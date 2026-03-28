"""
GitHub Web Scraper.
Scrapes public GitHub repository pages to extract project metadata
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
