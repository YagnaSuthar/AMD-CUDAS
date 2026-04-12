from __future__ import annotations

import re
from typing import Any


async def verify_github_project(*, link: str | None) -> dict[str, Any]:
    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    if not link:
        return {
            "format_score": 0.0,
            "metadata_score": 0.0,
            "source_score": 0.0,
            "issues": ["No project link provided"],
            "verified_fields": [],
            "recommendations": ["Provide a GitHub repository URL"],
        }

    m = re.match(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)", link.strip(), flags=re.IGNORECASE)
    if not m:
        return {
            "format_score": 0.2,
            "metadata_score": 0.2,
            "source_score": 0.0,
            "issues": ["Link does not look like a GitHub repository URL"],
            "verified_fields": [],
            "recommendations": ["Use format: https://github.com/<owner>/<repo>"],
        }

    owner = m.group("owner")
    repo = m.group("repo")

    format_score = 1.0

    source_score = 0.0
    metadata_score = 0.5

    try:
        import httpx

        async with httpx.AsyncClient(timeout=20.0, headers={"Accept": "application/vnd.github+json"}) as client:
            r = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if r.status_code == 200:
                data = r.json()
                source_score = 1.0
                verified_fields.append("repo_exists")

                stars = int(data.get("stargazers_count") or 0)
                forks = int(data.get("forks_count") or 0)
                open_issues = int(data.get("open_issues_count") or 0)
                metadata_score = min(1.0, 0.4 + (0.3 if stars > 0 else 0.0) + (0.2 if forks > 0 else 0.0) + (0.1 if open_issues < 200 else 0.0))
            elif r.status_code == 404:
                issues.append("GitHub repo not found (404)")
                recommendations.append("Double-check owner/repo name or repo visibility")
            else:
                issues.append(f"GitHub API error: {r.status_code}")
                recommendations.append("Try again later or provide alternative proof (screenshots, commits)")
    except Exception:
        issues.append("GitHub verification unavailable (http client missing or network blocked)")
        recommendations.append("Install httpx and allow outbound requests, or provide repo metadata manually")

    return {
        "format_score": round(format_score, 4),
        "metadata_score": round(metadata_score, 4),
        "source_score": round(source_score, 4),
        "issues": issues,
        "verified_fields": verified_fields,
        "recommendations": recommendations,
    }
