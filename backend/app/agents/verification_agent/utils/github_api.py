"""
GitHub REST API helpers for project verification.

Uses the official API (reliable, structured) instead of scraping GitHub's
JavaScript-rendered HTML. A ``GITHUB_TOKEN`` is optional: without one GitHub
allows 60 requests/hour per IP (~10 verifications); with one, 5,000/hour.
Raw file downloads go through raw.githubusercontent.com and do not count
against the API quota.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import unquote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"


class GitHubError(Exception):
    """Raised with a user-facing message when the repository can't be read."""

    def __init__(self, message: str, kind: str = "error"):
        super().__init__(message)
        self.kind = kind  # "not_found" | "rate_limited" | "error"


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "CUDAS-Verification-Agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = (getattr(settings, "GITHUB_TOKEN", "") or "").strip()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=_headers())


def _raise_for(r: httpx.Response, what: str) -> None:
    if r.status_code == 404:
        raise GitHubError(f"{what} not found — it may be private, renamed or deleted", "not_found")
    if r.status_code in (403, 429) and (r.headers.get("x-ratelimit-remaining") == "0" or r.status_code == 429):
        reset = r.headers.get("x-ratelimit-reset")
        wait = ""
        if reset and reset.isdigit():
            import time
            mins = max(1, int((int(reset) - time.time()) // 60) + 1)
            wait = f" Try again in about {mins} minute{'s' if mins != 1 else ''}."
        raise GitHubError(
            "GitHub is temporarily refusing requests from this server (API rate limit)." + wait
            + " Set GITHUB_TOKEN on the server to raise the limit from 60 to 5,000 requests/hour.",
            "rate_limited",
        )
    if r.status_code >= 400:
        raise GitHubError(f"GitHub returned HTTP {r.status_code} for {what}")


# ── URL parsing ──────────────────────────────────────────────────────────────

_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]+?)(?:\.git)?"
    r"(?:/(?P<kind>tree|blob)/(?P<rest>[^?#]+))?/?(?:[?#].*)?$",
    re.I,
)


def parse_github_url(link: str) -> dict[str, Any] | None:
    """
    Parse repository links, including folder and file links.

    Returns ``{owner, repo, ref_and_path, kind}`` or None when it isn't a repo URL.
    ``ref_and_path`` is resolved later because branch names may contain '/'.
    """
    if not link:
        return None
    m = _URL_RE.match(link.strip())
    if not m:
        return None
    rest = unquote(m.group("rest") or "").strip("/")
    return {
        "owner": m.group("owner"),
        "repo": m.group("repo"),
        "kind": (m.group("kind") or "").lower() or None,
        "ref_and_path": rest or None,
    }


# ── API calls ────────────────────────────────────────────────────────────────


async def get_repo(c: httpx.AsyncClient, owner: str, repo: str) -> dict[str, Any]:
    r = await c.get(f"{API}/repos/{owner}/{repo}")
    _raise_for(r, f"Repository {owner}/{repo}")
    return r.json()


async def get_languages(c: httpx.AsyncClient, owner: str, repo: str) -> dict[str, int]:
    try:
        r = await c.get(f"{API}/repos/{owner}/{repo}/languages")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


async def resolve_ref_and_path(
    c: httpx.AsyncClient, owner: str, repo: str, ref_and_path: str | None, default_branch: str,
) -> tuple[str, str | None]:
    """
    Split 'feature/login/src/app' into (branch, sub_path) by checking which
    prefix is a real branch/tag. Falls back to the default branch.
    """
    if not ref_and_path:
        return default_branch, None
    parts = ref_and_path.split("/")
    if parts[0] == default_branch:
        return default_branch, "/".join(parts[1:]) or None
    for i in range(min(len(parts), 4), 0, -1):
        candidate = "/".join(parts[:i])
        try:
            r = await c.get(f"{API}/repos/{owner}/{repo}/commits/{candidate}", headers={"Accept": "application/vnd.github.sha"})
            if r.status_code == 200:
                return candidate, "/".join(parts[i:]) or None
        except Exception:
            break
    # Unknown ref — assume first segment is the branch name
    return parts[0], "/".join(parts[1:]) or None


async def get_tree(c: httpx.AsyncClient, owner: str, repo: str, ref: str) -> tuple[list[dict[str, Any]], bool]:
    r = await c.get(f"{API}/repos/{owner}/{repo}/git/trees/{ref}", params={"recursive": "1"})
    if r.status_code == 409:  # empty repository
        return [], False
    _raise_for(r, f"Branch '{ref}'")
    data = r.json()
    return data.get("tree", []), bool(data.get("truncated"))


async def get_readme(c: httpx.AsyncClient, owner: str, repo: str, ref: str, sub_path: str | None) -> str:
    """README of the folder (if a sub-path is given) or of the repository root."""
    urls = []
    if sub_path:
        urls.append(f"{API}/repos/{owner}/{repo}/readme/{sub_path}")
    urls.append(f"{API}/repos/{owner}/{repo}/readme")
    for url in urls:
        try:
            r = await c.get(url, params={"ref": ref}, headers={"Accept": "application/vnd.github.raw"})
            if r.status_code == 200:
                return r.text[:6000]
        except Exception:
            pass
    return ""


async def fetch_raw_files(
    c: httpx.AsyncClient, owner: str, repo: str, ref: str, paths: list[str], max_chars: int = 20000,
) -> dict[str, str]:
    """Download several files concurrently from raw.githubusercontent.com."""
    async def one(path: str) -> tuple[str, str | None]:
        try:
            r = await c.get(f"{RAW}/{owner}/{repo}/{ref}/{path}")
            return path, (r.text[:max_chars] if r.status_code == 200 else None)
        except Exception:
            return path, None

    results = await asyncio.gather(*(one(p) for p in paths))
    return {p: t for p, t in results if t}
