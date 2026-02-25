"""Prompt templates for academic study planner.

No FastAPI/DB imports.
"""

STUDY_PLAN_SYSTEM_PROMPT = (
    "You are an academic study planner. "
    "You must follow the provided subject hour allocations exactly. "
    "Do not change allocated hours. Do not add, remove, or rename subjects. "
    "Return JSON only with no markdown, no commentary, no extra keys. "
    "Every day MUST include tasks that contain EXACT subject-hour lines in this format: "
    "<SubjectName>: <HH.HH> (two decimals). "
    "Output schema must be exactly: "
    "{"
    "  \"student_id\": string,"
    "  \"daily_plan\": ["
    "    { \"day\": int, \"date\": \"YYYY-MM-DD\", \"tasks\": [string, ...] }"
    "  ],"
    "  \"motivation_note\": string (optional)"
    "}."
)

STUDY_PLAN_USER_PROMPT = (
    "Create a 7-day study plan using the following structured allocation data. "
    "Rules: (1) Do not change allocated_hours. (2) Do not add any subjects. "
    "(3) In each day tasks, include one line per subject in EXACT format '<SubjectName>: <HH.HH>' "
    "where <HH.HH> is allocated_hours with two decimals. "
    "(4) Return JSON only, no extra keys.\n\n"
    "PERFORMANCE_CONTEXT:\n"
    "- completion_ratio: {completion_ratio}\n"
    "- weak_subjects: {weak_subjects}\n"
    "- strong_subjects: {strong_subjects}\n"
    "- missed_subjects: {missed_subjects}\n\n"
    "TONE_RULES:\n"
    "- If completion_ratio < 0.6: Use supportive but corrective tone.\n"
    "- If 0.6 <= completion_ratio < 0.85: Use neutral constructive tone.\n"
    "- If completion_ratio >= 0.85: Use encouraging and challenge-based tone.\n"
    "- Emphasize weak_subjects and missed_subjects in explanations without changing allocated_hours.\n\n"
    "STRUCTURED_DATA_JSON=\n"
    "{structured_data}"
)


def build_llm_messages(structured_data: dict) -> list[dict]:
    import json
    perf = structured_data.get("performance_summary", {})
    completion_ratio = perf.get("completion_ratio", 1.0)
    weak_subjects = ", ".join(perf.get("weak_subjects", [])) or "None"
    strong_subjects = ", ".join(perf.get("strong_subjects", [])) or "None"
    missed_subjects = ", ".join(perf.get("missed_subjects", [])) or "None"

    # Detect revision mode subjects (days_left <= 3)
    allocations = structured_data.get("allocations", [])
    revision_subjects = [
        a["subject"] for a in allocations if a.get("days_left", 0) <= 3
    ]
    revision_note = ""
    if revision_subjects:
        revision_note = (
            "Revision Mode: Subjects with exams in ≤3 days should be prioritized for review. "
            "For these subjects, format tasks as: "
            "<Subject> – Revision + Previous Year Questions"
        )

    user_prompt = STUDY_PLAN_USER_PROMPT.format(
        completion_ratio=completion_ratio,
        weak_subjects=weak_subjects,
        strong_subjects=strong_subjects,
        missed_subjects=missed_subjects,
        structured_data=json.dumps(
            structured_data,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
    if revision_note:
        user_prompt = f"{revision_note}\n\n{user_prompt}"

    return [
        {"type": "system", "content": STUDY_PLAN_SYSTEM_PROMPT},
        {
            "type": "human",
            "content": user_prompt,
        },
    ]
