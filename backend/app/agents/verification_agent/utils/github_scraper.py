"""
GitHub data collection for project verification.

- Repository metadata and folder tree: GitHub REST API (see ``github_api``)
  analysed by ``tree_analyzer``.
- Contributor statistics: GitHub's contributors graph data (with HTML fallback).
- A user's commits: GitHub REST API, optionally scoped to the submitted folder.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


async def fetch_repository_snapshot(
    owner: str,
    repo: str,
    *,
    ref_and_path: str | None = None,
    link_kind: str | None = None,
    tech_stack: str | None = None,
) -> dict[str, Any]:
    """
    Read a repository through the GitHub API and analyze its folder tree.

    Resolves the real default branch (not just main/master), honours
    ``/tree/<branch>/<folder>`` and ``/blob/<branch>/<file>`` links, and runs the
    deterministic tree analysis (see ``tree_analyzer``).

    Raises ``GitHubError`` with a user-facing message when the repo can't be read.
    """
    import asyncio

    from app.agents.verification_agent.utils import github_api as gh
    from app.agents.verification_agent.utils.tree_analyzer import (
        MANIFEST_NAMES, VENDORED_DIRS, analyze_tree,
    )

    print(f"[GitHub] Reading {owner}/{repo} via API (link path: {ref_and_path or '-'})")
    async with gh.client() as c:
        info = await gh.get_repo(c, owner, repo)
        default_branch = info.get("default_branch") or "main"
        ref, sub_path = await gh.resolve_ref_and_path(c, owner, repo, ref_and_path, default_branch)
        if link_kind == "blob" and sub_path:
            # A file link — analyze the folder that contains it
            sub_path = sub_path.rsplit("/", 1)[0] if "/" in sub_path else None

        items, truncated = await gh.get_tree(c, owner, repo, ref)

        scope = (sub_path or "").strip("/")
        manifest_paths = [
            it["path"] for it in items
            if it.get("type") == "blob"
            and it["path"].rsplit("/", 1)[-1].lower() in MANIFEST_NAMES
            and (not scope or it["path"].startswith(scope + "/") or "/" not in it["path"])
            and not any(p.lower() in VENDORED_DIRS for p in it["path"].split("/")[:-1])
        ]
        manifest_paths.sort(key=lambda p: p.count("/"))

        languages, readme, manifests = await asyncio.gather(
            gh.get_languages(c, owner, repo),
            gh.get_readme(c, owner, repo, ref, sub_path),
            gh.fetch_raw_files(c, owner, repo, ref, manifest_paths[:15]),
        )

    analysis = analyze_tree(
        items,
        sub_path=sub_path,
        manifests=manifests,
        claimed_tech_stack=tech_stack,
        truncated=truncated,
        branch=ref,
    )

    parent = info.get("parent") or {}
    snapshot = {
        "exists": True,
        "error": None,
        "repo_name": info.get("full_name") or f"{owner}/{repo}",
        "description": info.get("description") or "",
        "topics": info.get("topics") or [],
        "stars": info.get("stargazers_count", 0),
        "forks": info.get("forks_count", 0),
        "is_fork": bool(info.get("fork")),
        "fork_parent": parent.get("full_name"),
        "is_archived": bool(info.get("archived")),
        "created_at": info.get("created_at"),
        "pushed_at": info.get("pushed_at"),
        "default_branch": default_branch,
        "branch": ref,
        "sub_path": sub_path,
        "languages": [k for k, _ in sorted(languages.items(), key=lambda kv: -kv[1])],
        "languages_bytes": languages,
        "readme_content": readme,
        "file_names": [e["name"] for e in analysis.get("top_level", [])],
        "commits": 0,
        "repo_tree": analysis,
    }
    print(f"[GitHub] ✔ {snapshot['repo_name']}@{ref}{'/' + sub_path if sub_path else ''}: "
          f"{analysis.get('total_files', 0)} files, {analysis.get('code_files', 0)} code files, "
          f"types={analysis.get('project_types')}, structure={analysis.get('structure_score')}")
    return snapshot


# ── NEW: Contributors Scraper ─────────────────────────────────────────────────


async def scrape_contributors(owner: str, repo: str) -> list[dict[str, Any]]:
    """
    Scrape the contributors page to extract contribution data.

    Returns a list of dicts with keys:
        username, commits, additions, deletions, avatar_url
    """
    contributors: list[dict[str, Any]] = []

    try:
        import httpx
        from bs4 import BeautifulSoup
        import asyncio
    except ImportError as e:
        logger.error("Missing dependency for contributor scraping: %s", e)
        return contributors

    url = f"https://github.com/{owner}/{repo}/graphs/contributors-data"
    print(f"\n[GitHub Scraper] Fetching contributors: {url}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": f"https://github.com/{owner}/{repo}/graphs/contributors",
            "X-Requested-With": "XMLHttpRequest",
        }

        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            max_retries = 5
            for attempt in range(max_retries):
                r = await client.get(url)

                if r.status_code == 200:
                    try:
                        data = r.json()
                        for item in data:
                            author = item.get("author", {})
                            username = author.get("login", "")
                            commits = item.get("total", 0)
                            
                            additions = 0
                            deletions = 0
                            for week in item.get("weeks", []):
                                additions += week.get("a", 0)
                                deletions += week.get("d", 0)
                                
                            if username:
                                contributors.append({
                                    "username": username,
                                    "commits": commits,
                                    "additions": additions,
                                    "deletions": deletions,
                                })
                        break  # Success
                    except Exception as e:
                        print(f"[GitHub Scraper] ⚠ JSON parse failed for contributors: {e}")
                        break
                elif r.status_code == 202:
                    print(f"[GitHub Scraper] ⏳ Contributors data is processing (202). Retrying in 2s (Attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(2)
                else:
                    print(f"[GitHub Scraper] ⚠ Contributors page returned {r.status_code}")
                    break

    except Exception as e:
        print(f"[GitHub Scraper] ⚠ Contributors scraping failed: {e}")
        logger.error("Contributors scraping failed for %s/%s: %s", owner, repo, e)

    # Fallback if we got nothing
    if not contributors:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                contributors = await _scrape_contributors_fallback(client, owner, repo)
        except Exception:
            pass

    if contributors:
        print(f"[GitHub Scraper] ✔ Found {len(contributors)} contributors")
        for c in contributors[:5]:
            print(f"  - {c['username']}: {c['commits']} commits")
    else:
        print("[GitHub Scraper] ⚠ No contributor data found")

    return contributors


async def _scrape_contributors_fallback(
    client: Any, owner: str, repo: str
) -> list[dict[str, Any]]:
    """Fallback: scrape contributor info from the main repo page or API."""
    contributors: list[dict[str, Any]] = []

    try:
        from bs4 import BeautifulSoup

        # Try the contributors list page
        url = f"https://github.com/{owner}/{repo}/contributors"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        r = await client.get(url, headers=headers)

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")

            # Parse contributor list items
            contrib_items = soup.select(
                "li.contrib-person, "
                "ol.contrib-data li, "
                "a[data-hovercard-type='user']"
            )

            seen_usernames = set()
            for item in contrib_items:
                # Extract username from link
                link = item if item.name == "a" else item.select_one("a")
                if not link:
                    continue

                href = link.get("href", "")
                username = href.strip("/").split("/")[-1] if href else link.get_text(strip=True)

                if not username or username in seen_usernames:
                    continue
                seen_usernames.add(username)

                # Try to find commit count
                commits = 0
                text_content = item.get_text(" ", strip=True)
                nums = re.findall(r"(\d[\d,]*)\s*commit", text_content, re.IGNORECASE)
                if nums:
                    commits = int(nums[0].replace(",", ""))

                contributors.append({
                    "username": username,
                    "commits": commits,
                    "additions": 0,
                    "deletions": 0,
                })

    except Exception as e:
        logger.warning("Contributors fallback failed: %s", e)

    return contributors


# ── NEW: User Commits Scraper ─────────────────────────────────────────────────


async def scrape_user_commits(
    owner: str, repo: str, username: str, max_pages: int = 3,
    sub_path: str | None = None, ref: str | None = None,
) -> list[dict[str, Any]]:
    """
    Scrape commits by a specific user from the repository.

    Returns a list of dicts with keys: message, date, sha, url
    """
    commits: list[dict[str, Any]] = []

    try:
        import httpx
    except ImportError as e:
        logger.error("Missing dependency for commit scraping: %s", e)
        return commits

    print(f"\n[GitHub Scraper] Fetching commits by '{username}' in {owner}/{repo} via API")

    try:
        from app.agents.verification_agent.utils.github_api import client as gh_client

        async with gh_client() as client:
            params = {"author": username, "per_page": 30}
            if sub_path:
                params["path"] = sub_path  # only commits that touched the submitted folder
            if ref:
                params["sha"] = ref
            r = await client.get(f"https://api.github.com/repos/{owner}/{repo}/commits", params=params)
            
            if r.status_code == 200:
                data = r.json()
                for item in data:
                    commit_data = item.get("commit", {})
                    author = commit_data.get("author", {})
                    
                    commits.append({
                        "message": commit_data.get("message", "N/A"),
                        "date": author.get("date", "N/A"),
                        "sha": item.get("sha", "")[:7]
                    })
            else:
                print(f"[GitHub Scraper] ⚠ Commits API returned {r.status_code}")

    except Exception as e:
        print(f"[GitHub Scraper] ⚠ Commit API scraping failed: {e}")
        logger.error("Commit API scraping failed for %s in %s/%s: %s", username, owner, repo, e)

    print(f"[GitHub Scraper] ✔ Found {len(commits)} commits by '{username}'")
    for c in commits[:3]:
        print(f"  - [{c.get('date', 'N/A')[:10]}] {c.get('message', 'N/A')[:60]}")

    return commits
