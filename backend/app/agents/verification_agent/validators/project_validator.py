"""
GitHub Project Validator.
Uses web scraping to verify GitHub projects and AI to analyze project quality.
"""

from __future__ import annotations

import re
from typing import Any


async def verify_github_project(
    *,
    link: str | None,
    project_description: str | None = None,
    tech_stack: str | None = None,
) -> dict[str, Any]:
    """
    Verify a GitHub project by scraping the repo page and analyzing content.
    Returns format_score, metadata_score, source_score, issues, verified_fields,
    recommendations, and scraped_data for downstream AI analysis.
    """
    issues: list[str] = []
    verified_fields: list[str] = []
    recommendations: list[str] = []

    print(f"\n[Verification Agent] ═══ PROJECT VALIDATION ═══")
    print(f"[Verification Agent] Link: {link}")

    if not link:
        print("[Verification Agent] ✗ No project link provided")
        return {
            "format_score": 0.0,
            "metadata_score": 0.0,
            "source_score": 0.0,
            "issues": ["No project link provided"],
            "verified_fields": [],
            "recommendations": ["Provide a GitHub repository URL"],
            "scraped_data": {},
        }

    m = re.match(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)", link.strip(), flags=re.IGNORECASE)
    if not m:
        print("[Verification Agent] ✗ Invalid GitHub URL format")
        return {
            "format_score": 0.2,
            "metadata_score": 0.2,
            "source_score": 0.0,
            "issues": ["Link does not look like a GitHub repository URL"],
            "verified_fields": [],
            "recommendations": ["Use format: https://github.com/<owner>/<repo>"],
            "scraped_data": {},
        }

    owner = m.group("owner")
    repo = m.group("repo")
    format_score = 1.0
    verified_fields.append("url_format")
    print(f"[Verification Agent] ✔ Valid URL format: {owner}/{repo}")

    # --- Web Scraping ---
    scraped_data: dict[str, Any] = {}
    source_score = 0.0
    metadata_score = 0.5

    try:
        from app.agents.verification_agent.utils.github_scraper import scrape_github_repo

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

            # --- Quality checks with terminal logging ---
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
) -> dict[str, Any] | None:
    """Use LLM to analyze the project quality, description match, and tech stack match."""
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
            "- description_match_score: float 0.0-1.0 (how well user description matches repo)\n"
            "- tech_stack_match_score: float 0.0-1.0 (how well user tech stack matches repo languages)\n"
            "- authenticity_score: float 0.0-1.0 (is this a real, substantial project?)\n"
            "- complexity_level: string (beginner/intermediate/advanced)\n"
            "- internal_feedback: string (detailed technical analysis for admin, frank assessment)\n"
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
