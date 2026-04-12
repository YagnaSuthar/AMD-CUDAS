"""
GitHub Web Scraper — Enhanced.
Scrapes public GitHub repository pages to extract project metadata,
contributor data, user commits, and multi-level directory structure
without requiring an API key.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


async def scrape_github_repo(owner: str, repo: str) -> dict[str, Any]:
    """
    Scrape a public GitHub repository page and extract metadata.

    Returns a dict with keys:
        repo_name, description, readme_content, languages, topics,
        stars, forks, exists, error
    """
    result: dict[str, Any] = {
        "repo_name": f"{owner}/{repo}",
        "description": "",
        "readme_content": "",
        "languages": [],
        "topics": [],
        "stars": 0,
        "forks": 0,
        "commits": 0,
        "file_names": [],
        "exists": False,
        "error": None,
    }

    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError as e:
        result["error"] = f"Missing dependency: {e}"
        print(f"[GitHub Scraper] ERROR: Missing dependency - {e}")
        return result

    repo_url = f"https://github.com/{owner}/{repo}"
    print(f"\n{'='*60}")
    print(f"[GitHub Scraper] Scraping: {repo_url}")
    print(f"{'='*60}")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            # --- Scrape main repo page ---
            print("[GitHub Scraper] Fetching main page...")
            r = await client.get(repo_url)

            if r.status_code == 404:
                result["error"] = "Repository not found (404)"
                print("[GitHub Scraper] ✗ Repository not found (404)")
                return result
            elif r.status_code == 429:
                result["error"] = "Rate limited by GitHub"
                print("[GitHub Scraper] ✗ Rate limited (429)")
                return result
            elif r.status_code != 200:
                result["error"] = f"HTTP {r.status_code}"
                print(f"[GitHub Scraper] ✗ HTTP error: {r.status_code}")
                return result

            result["exists"] = True
            print("[GitHub Scraper] ✔ Repository exists")

            soup = BeautifulSoup(r.text, "html.parser")

            # --- Description ---
            desc_el = soup.select_one("p.f4.my-3")
            if not desc_el:
                desc_el = soup.select_one("[itemprop='about'] p")
            if not desc_el:
                desc_el = soup.select_one(".BorderGrid-row .f4")
            if desc_el:
                result["description"] = desc_el.get_text(strip=True)
                print(f"[GitHub Scraper] ✔ Description: {result['description'][:80]}...")

            # --- Topics ---
            topic_elements = soup.select("a.topic-tag")
            result["topics"] = [t.get_text(strip=True) for t in topic_elements][:20]
            if result["topics"]:
                print(f"[GitHub Scraper] ✔ Topics: {', '.join(result['topics'][:5])}")

            # --- Stars ---
            star_el = soup.select_one("#repo-stars-counter-star")
            if not star_el:
                star_el = soup.select_one("a[href$='/stargazers'] .Counter")
            if not star_el:
                star_el = soup.select_one("[id='repo-stars-counter-star']")
            if star_el:
                stars_text = star_el.get_text(strip=True).replace(",", "").replace("k", "000")
                try:
                    result["stars"] = int(float(stars_text))
                except (ValueError, TypeError):
                    pass
            print(f"[GitHub Scraper] ✔ Stars: {result['stars']}")

            # --- Forks ---
            fork_el = soup.select_one("#repo-network-counter")
            if not fork_el:
                fork_el = soup.select_one("a[href$='/forks'] .Counter")
            if fork_el:
                forks_text = fork_el.get_text(strip=True).replace(",", "").replace("k", "000")
                try:
                    result["forks"] = int(float(forks_text))
                except (ValueError, TypeError):
                    pass
            print(f"[GitHub Scraper] ✔ Forks: {result['forks']}")

            # --- Languages ---
            lang_elements = soup.select("a.d-inline-flex[data-ga-click*='language']")
            if not lang_elements:
                lang_elements = soup.select(".repository-lang-stats-graph span.language-color + span")
            if not lang_elements:
                # Try the language bar
                lang_items = soup.select("li.d-inline a span.text-bold")
                for li in lang_items:
                    lang_name = li.get_text(strip=True)
                    if lang_name and lang_name not in result["languages"]:
                        result["languages"].append(lang_name)
            else:
                for el in lang_elements:
                    lang_name = el.get_text(strip=True)
                    if lang_name and lang_name not in result["languages"]:
                        result["languages"].append(lang_name)

            # Fallback: extract from language color spans
            if not result["languages"]:
                for span in soup.select("span[itemprop='programmingLanguage']"):
                    lang = span.get_text(strip=True)
                    if lang and lang not in result["languages"]:
                        result["languages"].append(lang)

            if result["languages"]:
                print(f"[GitHub Scraper] ✔ Languages: {', '.join(result['languages'])}")

            # --- File names & Folders ---
            file_rows = soup.select("td.react-directory-row-name-cell-large-screen a, a.js-navigation-open.Link--primary, div.react-directory-filename-column a")
            files = []
            for a in file_rows:
                title = a.get("title", a.get_text(strip=True))
                if title and title not in files and "View all" not in title and title != "Go to file":
                    files.append(title)
            result["file_names"] = files[:50]
            if result["file_names"]:
                print(f"[GitHub Scraper] ✔ Files & Folders found: {len(result['file_names'])}")

            # --- Commits ---
            commits_el = soup.select_one("a[href$='/commits/main'] .Text-sc-17v1xeu-0, a[href$='/commits/master'] .Text-sc-17v1xeu-0, span.d-sm-inline strong")
            if commits_el:
                commits_text = commits_el.get_text(strip=True).replace(",", "")
                try:
                    result["commits"] = int(commits_text)
                except ValueError:
                    pass
            print(f"[GitHub Scraper] ✔ Commits: {result.get('commits', 0)}")

            # --- README ---
            print("[GitHub Scraper] Fetching README...")
            try:
                readme_r = await client.get(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
                )
                if readme_r.status_code == 404:
                    readme_r = await client.get(
                        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
                    )
                if readme_r.status_code == 200:
                    result["readme_content"] = readme_r.text[:5000]  # Cap at 5KB
                    print(f"[GitHub Scraper] ✔ README: {len(result['readme_content'])} chars")
                else:
                    print("[GitHub Scraper] ⚠ No README found")
            except Exception as readme_err:
                print(f"[GitHub Scraper] ⚠ README fetch failed: {readme_err}")

    except Exception as e:
        result["error"] = str(e)
        print(f"[GitHub Scraper] ✗ Scraping failed: {e}")
        logger.error("GitHub scraping failed for %s/%s: %s", owner, repo, e)

    print(f"\n[GitHub Scraper] Summary for {owner}/{repo}:")
    print(f"  Exists: {result['exists']}")
    print(f"  Description: {bool(result['description'])}")
    print(f"  README: {len(result.get('readme_content', ''))} chars")
    print(f"  Languages: {result['languages']}")
    print(f"  Stars: {result['stars']} | Forks: {result['forks']}")
    print(f"  Files: {len(result['file_names'])}")
    print(f"{'='*60}\n")

    return result


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
    owner: str, repo: str, username: str, max_pages: int = 3
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/commits?author={username}&per_page=30"
            r = await client.get(url)
            
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


# ── NEW: Repository Tree Scraper ──────────────────────────────────────────────


async def scrape_repo_tree(
    owner: str, repo: str, max_depth: int = 5, sub_path: str | None = None
) -> dict[str, Any]:
    """
    Traverse the repository directory structure via GitHub API.

    Returns a dict with:
        directories, total_files, max_depth, key_markers, key_file_contents, full_tree
    """
    tree: dict[str, Any] = {
        "directories": [],
        "total_files": 0,
        "max_depth": 0,
        "key_markers": {},
        "key_file_contents": {},
        "full_tree": {},
    }

    try:
        import httpx
    except ImportError as e:
        logger.error("Missing dependency for tree scraping: %s", e)
        return tree

    print(f"\n[GitHub Scraper] Traversing repo tree via API: {owner}/{repo}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            # Get default branch tree natively via API
            default_branch = "main"
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
            r = await client.get(url)
            if r.status_code == 404:
                url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                r = await client.get(url)
                default_branch = "master"

            if r.status_code == 200:
                data = r.json()
                tree_items = data.get("tree", [])
                
                # Nested tree builder
                nested_tree = {}
                
                # Key files to read content of
                key_file_names = {
                    "package.json", "requirements.txt", "Pipfile", "Cargo.toml",
                    "go.mod", "pom.xml", "build.gradle", "Dockerfile",
                    "docker-compose.yml", "docker-compose.yaml",
                    ".env.example", "setup.py", "pyproject.toml",
                }

                for item in tree_items:
                    path = item.get("path", "")
                    item_type = item.get("type", "")
                    
                    if not path:
                        continue
                        
                    # Target specific subpath if provided
                    if sub_path and not path.startswith(sub_path):
                        continue

                    parts = path.split("/")
                    depth = len(parts)
                    tree["max_depth"] = max(tree["max_depth"], depth)
                    
                    # Build nested tree
                    current_level = nested_tree
                    for i, part in enumerate(parts):
                        if i == len(parts) - 1:
                            if item_type == "tree":
                                current_level[part] = {}
                            else:
                                current_level[part] = "file"
                        else:
                            if part not in current_level:
                                current_level[part] = {}
                            current_level = current_level[part]
                    
                    if item_type == "tree":
                        tree["directories"].append(path)
                        name_lower = parts[-1].lower()
                        if name_lower in ("src", "source"):
                            tree["key_markers"]["has_src_dir"] = True
                        elif name_lower == "frontend":
                            tree["key_markers"]["has_frontend_dir"] = True
                        elif name_lower == "backend":
                            tree["key_markers"]["has_backend_dir"] = True
                        elif name_lower in ("test", "tests", "__tests__"):
                            tree["key_markers"]["has_tests"] = True
                    else:
                        tree["total_files"] += 1
                        filename = parts[-1].lower()

                        if filename == "readme.md" or filename == "readme":
                            tree["key_markers"]["has_readme"] = True
                        elif filename == "package.json":
                            tree["key_markers"]["has_package_json"] = True
                        elif filename in ("requirements.txt", "pipfile", "pyproject.toml"):
                            tree["key_markers"]["has_requirements"] = True
                        elif filename in ("dockerfile", "docker-compose.yml", "docker-compose.yaml"):
                            tree["key_markers"]["has_docker"] = True
                            tree["key_markers"]["has_config_files"] = True
                        elif filename in (".env.example", ".env"):
                            tree["key_markers"]["has_config_files"] = True
                        elif filename.startswith("test") or "test" in path.lower():
                            tree["key_markers"]["has_tests"] = True

                        # Try reading key files
                        if depth <= 3 and parts[-1] in key_file_names:
                            try:
                                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
                                file_r = await client.get(raw_url)
                                if file_r.status_code == 200:
                                    tree["key_file_contents"][path] = file_r.text[:2000]
                            except Exception:
                                pass

                tree["full_tree"] = nested_tree

            else:
                print(f"[GitHub Scraper] ⚠ API returned {r.status_code}. Rate limit or empty repo.")

    except Exception as e:
        print(f"[GitHub Scraper] ⚠ Tree API traversal error: {e}")
        logger.error("Tree API traversal failed for %s/%s: %s", owner, repo, e)

    print(f"[GitHub Scraper] ✔ Repo tree: {tree['total_files']} files, "
          f"{len(tree['directories'])} dirs, depth={tree['max_depth']}")
    return tree
