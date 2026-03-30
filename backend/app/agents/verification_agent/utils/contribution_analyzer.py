"""
GitHub Contribution Analyzer.

Analyzes contributor data, commit patterns, and code ownership
to compute a Contribution Authenticity Score for verification.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def analyze_contribution(
    *,
    contributors: list[dict[str, Any]],
    user_commits: list[dict[str, Any]],
    repo_tree: dict[str, Any],
    github_username: str | None = None,
    total_repo_commits: int = 0,
) -> dict[str, Any]:
    """
    Compute a Contribution Authenticity Score from contributor and commit data.

    Parameters
    ----------
    contributors : list[dict]
        List of contributor dicts with keys: username, commits, additions, deletions
    user_commits : list[dict]
        List of the specific user's commit dicts with keys: message, date, sha
    repo_tree : dict
        Repository tree structure with key directories and file counts
    github_username : str, optional
        The GitHub username to match in contributors
    total_repo_commits : int
        Total commits in the repository

    Returns
    -------
    dict with authenticity metrics
    """
    result: dict[str, Any] = {
        "contribution_percentage": 0.0,
        "commit_count": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "commit_frequency_score": 0.0,
        "commit_quality_score": 0.0,
        "code_ownership_score": 0.0,
        "project_completeness_score": 0.0,
        "contribution_authenticity_score": 0.0,
        "contribution_summary": "Unable to analyze contributions.",
        "details": {},
    }

    if not github_username:
        result["contribution_summary"] = "No GitHub username provided for contribution analysis."
        return result

    username_lower = github_username.lower()

    # ── 1) Find user in contributors ──────────────────────────────────────
    user_contrib = None
    total_additions = 0
    total_deletions = 0
    total_commits_all = 0

    for c in contributors:
        c_name = (c.get("username") or "").lower()
        c_commits = c.get("commits", 0)
        c_adds = c.get("additions", 0)
        c_dels = c.get("deletions", 0)
        total_additions += c_adds
        total_deletions += c_dels
        total_commits_all += c_commits

        if c_name == username_lower:
            user_contrib = c

    if user_contrib:
        user_commits_count = user_contrib.get("commits", 0)
        user_additions = user_contrib.get("additions", 0)
        user_deletions = user_contrib.get("deletions", 0)

        result["commit_count"] = user_commits_count
        result["lines_added"] = user_additions
        result["lines_deleted"] = user_deletions

        # Contribution percentage (by commits)
        if total_commits_all > 0:
            result["contribution_percentage"] = round(
                user_commits_count / total_commits_all * 100, 1
            )

        # Code ownership (by lines changed)
        total_lines = total_additions + total_deletions
        user_lines = user_additions + user_deletions
        if total_lines > 0:
            result["code_ownership_score"] = min(1.0, round(user_lines / total_lines, 4))
        else:
            result["code_ownership_score"] = 0.5  # Solo project, assume ownership
    else:
        # User not found in contributors
        result["contribution_summary"] = (
            f"User '{github_username}' was not found in the repository's contributor list. "
            "This could mean they haven't made any commits, or the username doesn't match."
        )
        result["details"]["user_found"] = False
        return result

    result["details"]["user_found"] = True
    result["details"]["total_contributors"] = len(contributors)

    # ── 2) Analyze commit quality ─────────────────────────────────────────
    if user_commits:
        meaningful_count = 0
        trivial_patterns = [
            r"^(fix|update|test|wip|tmp|temp|minor|typo|oops|revert)$",
            r"^(initial commit|first commit|init|create|add files)$",
            r"^\.+$",  # just dots
            r"^[a-f0-9]{6,}$",  # just a hash
        ]

        for commit in user_commits:
            msg = (commit.get("message") or "").strip().lower()
            is_trivial = False
            for pattern in trivial_patterns:
                if re.match(pattern, msg, re.IGNORECASE):
                    is_trivial = True
                    break
            # Also check message length — very short messages are often trivial
            if len(msg) < 5:
                is_trivial = True

            if not is_trivial:
                meaningful_count += 1

        if len(user_commits) > 0:
            result["commit_quality_score"] = round(
                meaningful_count / len(user_commits), 4
            )

        # Commit frequency: check distribution over time
        dates = []
        for commit in user_commits:
            date_str = commit.get("date", "")
            if date_str:
                dates.append(date_str)

        if len(dates) >= 2:
            # Check if commits are spread out (not all in one day)
            unique_dates = set(d[:10] for d in dates)  # Extract YYYY-MM-DD
            date_spread = len(unique_dates)

            if date_spread >= 10:
                result["commit_frequency_score"] = 1.0
            elif date_spread >= 5:
                result["commit_frequency_score"] = 0.8
            elif date_spread >= 3:
                result["commit_frequency_score"] = 0.6
            elif date_spread >= 2:
                result["commit_frequency_score"] = 0.4
            else:
                # All commits in one day — suspicious bulk upload
                result["commit_frequency_score"] = 0.2
        elif len(dates) == 1:
            result["commit_frequency_score"] = 0.3
        else:
            result["commit_frequency_score"] = 0.5  # No date info

        result["details"]["total_user_commits_analyzed"] = len(user_commits)
        result["details"]["meaningful_commits"] = meaningful_count
        result["details"]["unique_commit_dates"] = len(set(d[:10] for d in dates)) if dates else 0

    else:
        # No individual commit data available — use contributor-level data
        result["commit_quality_score"] = 0.5
        result["commit_frequency_score"] = 0.5

    # ── 3) Analyze project completeness ───────────────────────────────────
    if repo_tree:
        completeness = 0.0
        key_markers = repo_tree.get("key_markers", {})

        # Check for important project indicators
        has_readme = key_markers.get("has_readme", False)
        has_package = key_markers.get("has_package_json", False) or key_markers.get("has_requirements", False)
        has_src = key_markers.get("has_src_dir", False) or key_markers.get("has_frontend_dir", False) or key_markers.get("has_backend_dir", False)
        has_config = key_markers.get("has_config_files", False)
        has_tests = key_markers.get("has_tests", False)
        dir_depth = repo_tree.get("max_depth", 0)
        total_files = repo_tree.get("total_files", 0)

        if has_readme:
            completeness += 0.15
        if has_package:
            completeness += 0.15
        if has_src:
            completeness += 0.2
        if has_config:
            completeness += 0.1
        if has_tests:
            completeness += 0.1
        if dir_depth >= 3:
            completeness += 0.15
        elif dir_depth >= 2:
            completeness += 0.1
        if total_files >= 20:
            completeness += 0.15
        elif total_files >= 10:
            completeness += 0.1
        elif total_files >= 5:
            completeness += 0.05

        result["project_completeness_score"] = min(1.0, round(completeness, 4))
        result["details"]["repo_structure"] = key_markers
    else:
        result["project_completeness_score"] = 0.5  # Unknown

    # ── 4) Compute final authenticity score ───────────────────────────────
    authenticity = (
        result["commit_frequency_score"] * 0.25
        + result["commit_quality_score"] * 0.25
        + result["code_ownership_score"] * 0.25
        + result["project_completeness_score"] * 0.25
    )
    result["contribution_authenticity_score"] = round(min(1.0, authenticity), 4)

    # ── 5) Generate human-readable summary ────────────────────────────────
    summary_parts = []
    summary_parts.append(
        f"User '{github_username}' contributed {result['contribution_percentage']}% "
        f"of commits ({result['commit_count']} commits) to this repository."
    )
    summary_parts.append(
        f"Lines changed: +{result['lines_added']} / -{result['lines_deleted']}."
    )

    if result["commit_frequency_score"] >= 0.7:
        summary_parts.append("Commits are well-distributed over time, indicating consistent work.")
    elif result["commit_frequency_score"] >= 0.4:
        summary_parts.append("Commit pattern shows moderate distribution over time.")
    else:
        summary_parts.append("⚠ Commits are clustered — possible bulk upload detected.")

    if result["commit_quality_score"] >= 0.7:
        summary_parts.append("Commit messages are mostly meaningful and descriptive.")
    elif result["commit_quality_score"] >= 0.4:
        summary_parts.append("Commit messages are of mixed quality.")
    else:
        summary_parts.append("⚠ Many commit messages are trivial or non-descriptive.")

    if result["code_ownership_score"] >= 0.5:
        summary_parts.append("User has significant code ownership in this project.")
    elif result["code_ownership_score"] >= 0.2:
        summary_parts.append("User has moderate code ownership.")
    else:
        summary_parts.append("⚠ User's code ownership is low compared to other contributors.")

    score_pct = int(result["contribution_authenticity_score"] * 100)
    summary_parts.append(f"Overall Contribution Authenticity Score: {score_pct}%.")

    result["contribution_summary"] = " ".join(summary_parts)

    logger.info(
        "Contribution analysis for %s: authenticity=%.2f, commits=%d, ownership=%.2f",
        github_username,
        result["contribution_authenticity_score"],
        result["commit_count"],
        result["code_ownership_score"],
    )

    return result
