"""
GitHub Project Validator — Enhanced.
Uses web scraping to verify GitHub projects with deep contributor analysis,
commit-level analysis, multi-level directory traversal, and AI-powered assessment.
"""

from __future__ import annotations

import re
from typing import Any


async def verify_github_project(
    *,
    link: str | None,
    project_description: str | None = None,
    tech_stack: str | None = None,
    github_username: str | None = None,
) -> dict[str, Any]:
    """
    Verify a GitHub project by scraping the repo page, analyzing contributors,
    commits, and directory structure.

    Returns format_score, metadata_score, source_score, contribution_data,
    issues, verified_fields, recommendations, and scraped_data.
    """
    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    print(f"\n[Verification Agent] ═══ PROJECT VALIDATION ═══")
    print(f"[Verification Agent] Link: {link}")
    print(f"[Verification Agent] GitHub User: {github_username or 'N/A'}")

    if not link:
        print("[Verification Agent] ✗ No project link provided")
        return {
            "format_score": 0.0,
            "metadata_score": 0.0,
            "source_score": 0.0,
            "contribution_data": {},
            "issues": ["No project link provided"],
            "verified_fields": [],
            "recommendations": ["Provide a GitHub repository URL"],
            "scraped_data": {},
        }

    m = re.match(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)(?:/tree/[^/]+/(?P<sub_path>.*))?", link.strip(), flags=re.IGNORECASE)
    if not m:
        print("[Verification Agent] ✗ Invalid GitHub URL format")
        return {
            "format_score": 0.2,
            "metadata_score": 0.2,
            "source_score": 0.0,
            "contribution_data": {},
            "issues": ["Link does not look like a GitHub repository URL"],
            "verified_fields": [],
            "recommendations": ["Use format: https://github.com/<owner>/<repo> and optionally /tree/<branch>/<path>"],
            "scraped_data": {},
        }

    owner = m.group("owner")
    repo = m.group("repo")
    sub_path = m.group("sub_path")
    format_score = 1.0
    verified_fields.append("url_format")
    print(f"[Verification Agent] ✔ Valid URL format: {owner}/{repo}")

    # Auto-detect github_username from URL owner if not provided
    if not github_username:
        github_username = owner
        print(f"[Verification Agent] ℹ Using URL owner as username: {github_username}")

    # --- Web Scraping ---
    scraped_data: dict[str, Any] = {}
    source_score = 0.0
    metadata_score = 0.5
    contribution_data: dict[str, Any] = {}

    try:
        from app.agents.verification_agent.utils.github_scraper import (
            scrape_github_repo,
            scrape_contributors,
            scrape_user_commits,
            scrape_repo_tree,
        )

        # ── Step 1: Main repo page ────────────────────────────────────────
        scraped_data = await scrape_github_repo(owner, repo)

        if scraped_data.get("error"):
            error_msg = scraped_data["error"]
            if "404" in error_msg:
                issues.append("GitHub repo not found (404)")
                source_score = 0.0
                recommendations.append("Double-check repo URL or ensure it's public")
                print(f"[Verification Agent] ✗ Repo not found")
            elif "Rate limited" in error_msg:
                issues.append("GitHub rate limited — try again later")
                source_score = 0.3
                recommendations.append("Wait a few minutes and try again")
                print(f"[Verification Agent] ⚠ Rate limited")
            else:
                issues.append(f"Scraping error: {error_msg}")
                source_score = 0.2
                print(f"[Verification Agent] ⚠ Scraping error: {error_msg}")
        elif scraped_data.get("exists"):
            source_score = 1.0
            verified_fields.append("repo_exists")
            print(f"[Verification Agent] ✔ Repo exists")

            # --- Validate scraped data ---
            stars = scraped_data.get("stars", 0)
            forks = scraped_data.get("forks", 0)
            readme_len = len(scraped_data.get("readme_content", ""))
            languages = scraped_data.get("languages", [])
            file_count = len(scraped_data.get("file_names", []))
            description = scraped_data.get("description", "")

            # Metadata scoring
            metadata_score = 0.3  # Base for existing
            if description:
                metadata_score += 0.1
                verified_fields.append("description")
            if readme_len > 100:
                metadata_score += 0.2
                verified_fields.append("readme")
            elif readme_len > 0:
                metadata_score += 0.1
            if languages:
                metadata_score += 0.15
                verified_fields.append("languages")
            if stars > 0:
                metadata_score += 0.1
            if forks > 0:
                metadata_score += 0.05
            if file_count > 3:
                metadata_score += 0.1
                verified_fields.append("file_structure")

            metadata_score = min(1.0, metadata_score)

            # --- Quality checks ---
            print(f"\n[Verification Agent] ── Quality Checks ──")

            if readme_len < 50:
                issues.append("Weak or missing README documentation")
                recommendations.append("Add a comprehensive README with project description, setup instructions, and usage")
                print(f"[Verification Agent] ⚠ Weak README ({readme_len} chars)")
            else:
                print(f"[Verification Agent] ✔ README present ({readme_len} chars)")

            if file_count < 3:
                issues.append("Very few files in repository — may be incomplete")
                recommendations.append("Add more project files to demonstrate substance")
                print(f"[Verification Agent] ⚠ Low file count ({file_count})")
            else:
                print(f"[Verification Agent] ✔ File count: {file_count}")

            if not languages:
                issues.append("No programming languages detected")
                print(f"[Verification Agent] ⚠ No languages detected")
            else:
                print(f"[Verification Agent] ✔ Languages: {', '.join(languages)}")

            print(f"[Verification Agent] ✔ Stars: {stars} | Forks: {forks}")

            # ── Step 2: Contributors Analysis ─────────────────────────────
            print(f"\n[Verification Agent] ── Deep Analysis: Contributors ──")
            try:
                contributors = await scrape_contributors(owner, repo)
                scraped_data["contributors"] = contributors

                if contributors:
                    verified_fields.append("contributors_analyzed")
                    scraped_data["contributor_count"] = len(contributors)

                    # Find the user in contributors
                    user_found = False
                    for c in contributors:
                        if (c.get("username") or "").lower() == github_username.lower():
                            user_found = True
                            scraped_data["user_commits_count"] = c.get("commits", 0)
                            scraped_data["user_additions"] = c.get("additions", 0)
                            scraped_data["user_deletions"] = c.get("deletions", 0)
                            print(f"[Verification Agent] ✔ User '{github_username}' found: "
                                  f"{c.get('commits', 0)} commits")
                            break

                    if not user_found:
                        issues.append(f"User '{github_username}' not found in contributors list")
                        print(f"[Verification Agent] ⚠ User '{github_username}' NOT in contributors")
                else:
                    print(f"[Verification Agent] ⚠ Could not fetch contributor data")

            except Exception as contrib_err:
                print(f"[Verification Agent] ⚠ Contributor analysis failed: {contrib_err}")

            # ── Step 3: User Commits Analysis ─────────────────────────────
            print(f"\n[Verification Agent] ── Deep Analysis: User Commits ──")
            user_commits = []
            try:
                user_commits = await scrape_user_commits(owner, repo, github_username)
                scraped_data["user_commits_detail"] = user_commits

                if user_commits:
                    verified_fields.append("commits_analyzed")
                    print(f"[Verification Agent] ✔ Analyzed {len(user_commits)} commits by '{github_username}'")

                    # Check for bulk commit patterns
                    if len(user_commits) > 0:
                        dates = [c.get("date", "")[:10] for c in user_commits if c.get("date")]
                        unique_dates = set(dates)
                        if len(unique_dates) <= 1 and len(user_commits) > 5:
                            issues.append("All commits made on the same day — possible bulk upload")
                            print(f"[Verification Agent] ⚠ Suspicious: all commits on same day")
                else:
                    print(f"[Verification Agent] ⚠ No commits found for '{github_username}'")

            except Exception as commit_err:
                print(f"[Verification Agent] ⚠ Commit analysis failed: {commit_err}")

            # ── Step 4: Repository Tree Analysis ──────────────────────────
            print(f"\n[Verification Agent] ── Deep Analysis: Repo Structure ──")
            repo_tree = {}
            try:
                if sub_path:
                    print(f"[Verification Agent] Focusing analysis on folder: {sub_path}")
                repo_tree = await scrape_repo_tree(owner, repo, max_depth=3, sub_path=sub_path)
                scraped_data["repo_tree"] = repo_tree

                if repo_tree.get("total_files", 0) > 0:
                    verified_fields.append("repo_structure_analyzed")
                    print(f"[Verification Agent] ✔ Tree: {repo_tree['total_files']} files, "
                          f"{len(repo_tree.get('directories', []))} dirs")

            except Exception as tree_err:
                print(f"[Verification Agent] ⚠ Tree analysis failed: {tree_err}")

            # ── Step 5: Contribution Authenticity ─────────────────────────
            print(f"\n[Verification Agent] ── Contribution Authenticity ──")
            try:
                from app.agents.verification_agent.utils.contribution_analyzer import analyze_contribution

                contribution_data = analyze_contribution(
                    contributors=scraped_data.get("contributors", []),
                    user_commits=user_commits,
                    repo_tree=repo_tree,
                    github_username=github_username,
                    total_repo_commits=scraped_data.get("commits", 0),
                )

                scraped_data["contribution_analysis"] = contribution_data
                print(f"[Verification Agent] ✔ Authenticity Score: "
                      f"{contribution_data.get('contribution_authenticity_score', 0):.2f}")
                print(f"[Verification Agent]   Ownership: "
                      f"{contribution_data.get('code_ownership_score', 0):.2f}")
                print(f"[Verification Agent]   Commit Quality: "
                      f"{contribution_data.get('commit_quality_score', 0):.2f}")

            except Exception as contrib_err:
                print(f"[Verification Agent] ⚠ Contribution analysis failed: {contrib_err}")

    except Exception as e:
        issues.append(f"Verification error: {str(e)}")
        source_score = 0.2
        print(f"[Verification Agent] ✗ Exception during verification: {e}")
        recommendations.append("Try again later or contact support")

    # --- AI Analysis (if scraped data available) ---
    ai_feedback = await _run_ai_analysis(
        scraped_data=scraped_data,
        project_description=project_description,
        tech_stack=tech_stack,
        contribution_data=contribution_data,
    )

    if ai_feedback:
        if ai_feedback.get("internal_feedback"):
            scraped_data["internal_feedback"] = ai_feedback["internal_feedback"]
        if ai_feedback.get("student_feedback"):
            scraped_data["student_feedback"] = ai_feedback["student_feedback"]
        if ai_feedback.get("complexity_level"):
            scraped_data["complexity_level"] = ai_feedback["complexity_level"]
        if ai_feedback.get("description_match_score") is not None:
            desc_match = ai_feedback["description_match_score"]
            if desc_match < 0.3:
                issues.append("Project description does not match repository content")
            scraped_data["description_match_score"] = desc_match
        if ai_feedback.get("tech_stack_match_score") is not None:
            tech_match = ai_feedback["tech_stack_match_score"]
            if tech_match < 0.3:
                issues.append("Tech stack mismatch between submission and repository")
            scraped_data["tech_stack_match_score"] = tech_match

    print(f"\n[Verification Agent] ── Scores ──")
    print(f"[Verification Agent] Format:   {round(format_score, 2)}")
    print(f"[Verification Agent] Metadata: {round(metadata_score, 2)}")
    print(f"[Verification Agent] Source:   {round(source_score, 2)}")
    print(f"[Verification Agent] Issues:   {len(issues)}")
    print(f"[Verification Agent] ════════════════════════════\n")

    return {
        "format_score": round(format_score, 4),
        "metadata_score": round(metadata_score, 4),
        "source_score": round(source_score, 4),
        "contribution_data": contribution_data,
        "issues": issues,
        "verified_fields": verified_fields,
        "recommendations": recommendations,
        "scraped_data": scraped_data,
    }


async def _run_ai_analysis(
    *,
    scraped_data: dict[str, Any],
    project_description: str | None,
    tech_stack: str | None,
    contribution_data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Use LLM to analyze the project quality, description match, tech stack match, and contribution patterns."""
    if not scraped_data.get("exists"):
        return None

    try:
        import asyncio
        import json
        from app.core.llm import get_llm
        from langchain_core.messages import HumanMessage, SystemMessage

        print("[Verification Agent] Running AI analysis...")

        system_prompt = (
            "You are a strict project verification AI. Analyze the provided GitHub project data "
            "and return ONLY a compact JSON object with these keys:\n"
            "- description_match_score: float 0.0-1.0 (how well user description matches actual repo structure and features)\n"
            "- tech_stack_match_score: float 0.0-1.0 (how well user tech stack matches repo languages)\n"
            "- authenticity_score: float 0.0-1.0 (is this a real, substantial project?)\n"
            "- complexity_level: string (beginner/intermediate/advanced)\n"
            "- internal_feedback: string (detailed technical analysis for admin, frank assessment including contribution analysis)\n"
            "- student_feedback: string (friendly feedback for the student with appreciation + tips)\n"
            "Do NOT include markdown. Return ONLY valid JSON."
        )

        context = {
            "repo": scraped_data.get("repo_name"),
            "repo_description": scraped_data.get("description", ""),
            "readme_snippet": (scraped_data.get("readme_content", "") or "")[:2000],
            "languages": scraped_data.get("languages", []),
            "topics": scraped_data.get("topics", []),
            "stars": scraped_data.get("stars", 0),
            "forks": scraped_data.get("forks", 0),
            "file_count": len(scraped_data.get("file_names", [])),
            "file_names": scraped_data.get("file_names", [])[:15],
            "user_description": project_description or "Not provided",
            "user_tech_stack": tech_stack or "Not provided",
            "contributor_count": scraped_data.get("contributor_count", 0),
            "tree_directories": scraped_data.get("repo_tree", {}).get("directories", [])[:100],
        }

        # Include contribution analysis if available
        if contribution_data and contribution_data.get("details", {}).get("user_found"):
            context["contribution"] = {
                "percentage": contribution_data.get("contribution_percentage", 0),
                "commits": contribution_data.get("commit_count", 0),
                "lines_added": contribution_data.get("lines_added", 0),
                "lines_deleted": contribution_data.get("lines_deleted", 0),
                "authenticity_score": contribution_data.get("contribution_authenticity_score", 0),
                "commit_quality": contribution_data.get("commit_quality_score", 0),
                "code_ownership": contribution_data.get("code_ownership_score", 0),
            }

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Project verification data: {json.dumps(context)}"),
        ]

        llm = get_llm()
        resp = await asyncio.to_thread(llm.invoke, messages)
        text = resp.content if hasattr(resp, "content") else str(resp)

        # Extract JSON block if wrapped in markdown
        import re
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            text = match.group(0)
            
        parsed = json.loads(text)

        print(f"[Verification Agent] AI Analysis Complete:")
        print(f"  Complexity: {parsed.get('complexity_level', 'N/A')}")
        print(f"  Description Match: {parsed.get('description_match_score', 'N/A')}")
        print(f"  Tech Stack Match: {parsed.get('tech_stack_match_score', 'N/A')}")
        print(f"  Authenticity: {parsed.get('authenticity_score', 'N/A')}")

        return parsed

    except Exception as e:
        print(f"[Verification Agent] ⚠ AI analysis failed (non-fatal): {e}")
        return {
            "description_match_score": 0.5,
            "tech_stack_match_score": 0.5,
            "authenticity_score": 0.5,
            "complexity_level": "unknown",
            "internal_feedback": f"AI analysis unavailable: {str(e)}",
            "student_feedback": "Your project has been submitted for review. We'll analyze it shortly.",
        }
