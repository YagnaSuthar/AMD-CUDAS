"""
Deterministic topic/concept selection for project-based interview questions.

The LLM does NOT choose what to ask — it only converts a pre-selected
(topic, concept) pair into a natural interview question.
"""

from __future__ import annotations

import re
from typing import Any

# ── Topic hierarchy ────────────────────────────────────────────────────────

TOPIC_HIERARCHY: dict[str, list[str]] = {
    "project_overview": [
        "project_overview",
        "architecture",
        "motivation",
        "challenges",
        "scalability",
        "future_improvements",
    ],
    "tech_stack": [
        "backend_choice",
        "database_choice",
        "frontend_choice",
        "deployment",
    ],
    "backend_design": [
        "api_design",
        "authentication",
        "session_management",
        "performance",
    ],
    "database": [
        "schema_design",
        "indexing",
        "relationships",
        "optimization",
    ],
    "ai_features": [
        "rag",
        "embeddings",
        "prompt_engineering",
        "evaluation",
    ],
}

# Fixed plan: question_number → (topic, concept)
QUESTION_NUMBER_PLAN: dict[int, tuple[str, str]] = {
    1: ("project_overview", "project_overview"),   # Project overview
    2: ("project_overview", "architecture"),       # Architecture
    3: ("tech_stack", "backend_choice"),           # Tech stack decision
    4: ("backend_design", "api_design"),             # Backend implementation
    5: ("database", "schema_design"),                # Database design
    6: ("project_overview", "challenges"),           # Challenges faced
    7: ("backend_design", "performance"),            # Optimization
    8: ("project_overview", "scalability"),          # Scalability
    9: ("ai_features", "rag"),                       # AI features
    10: ("project_overview", "future_improvements"), # Future improvements
}

CONCEPT_RAG_KEYWORDS: dict[str, list[str]] = {
    "project_overview": ["project", "overview", "built", "developed", "application"],
    "architecture": ["architecture", "components", "system design", "modules", "microservice"],
    "motivation": ["why", "motivation", "problem", "goal"],
    "challenges": ["challenge", "difficulty", "issue", "problem", "obstacle"],
    "scalability": ["scale", "scalability", "load", "users", "growth"],
    "future_improvements": ["future", "improve", "next", "roadmap", "enhancement"],
    "backend_choice": ["backend", "fastapi", "django", "flask", "node", "express", "api"],
    "database_choice": ["database", "postgres", "mysql", "mongodb", "redis", "sql"],
    "frontend_choice": ["frontend", "react", "vue", "angular", "ui"],
    "deployment": ["deploy", "docker", "kubernetes", "aws", "cloud", "ci/cd"],
    "api_design": ["api", "rest", "endpoint", "routes", "backend"],
    "authentication": ["auth", "jwt", "login", "oauth", "session"],
    "session_management": ["session", "token", "cookie", "auth"],
    "performance": ["performance", "optimize", "latency", "cache", "speed"],
    "schema_design": ["schema", "database", "table", "model", "entity"],
    "indexing": ["index", "query", "database"],
    "relationships": ["relationship", "foreign key", "join", "schema"],
    "optimization": ["optimize", "query", "index", "performance"],
    "rag": ["rag", "retrieval", "embedding", "vector", "llm", "ai"],
    "embeddings": ["embedding", "vector", "semantic"],
    "prompt_engineering": ["prompt", "llm", "generation"],
    "evaluation": ["evaluation", "metric", "accuracy", "testing"],
}

MAX_RAG_CHUNK_CHARS = 600


def normalize_concept(c: str) -> str:
    if not c:
        return ""
    c = c.lower()
    c = re.sub(r"[^\w\s]", "", c)
    return " ".join(c.split())


def concept_is_used(concept: str, used_concepts: list[str] | None) -> bool:
    """Return True if concept (or a near-duplicate) was already asked."""
    norm_c = normalize_concept(concept)
    if not norm_c:
        return False
    normalized_used = [normalize_concept(uc) for uc in (used_concepts or []) if uc]
    for uc in normalized_used:
        if not uc:
            continue
        if norm_c == uc:
            return True
        if len(norm_c) > 2 and len(uc) > 2 and (norm_c in uc or uc in norm_c):
            return True
        words_c = set(norm_c.split())
        words_uc = set(uc.split())
        if words_c and words_uc:
            jaccard = len(words_c & words_uc) / len(words_c | words_uc)
            if jaccard >= 0.5:
                return True
    return False


def _normalize_used(values: list[str] | None) -> set[str]:
    return {normalize_concept(v) for v in (values or []) if v}


def select_topic_and_concept(
    question_number: int,
    used_topics: list[str] | None = None,
    used_concepts: list[str] | None = None,
) -> tuple[str, str]:
    """
    Deterministically pick (topic, concept) for a question number.
    Retries with the next unused concept if the planned one was already used.
    """
    used_topics = used_topics or []
    used_concepts = used_concepts or []
    used_topic_norm = _normalize_used(used_topics)

    def _pick(topic: str, concept: str) -> tuple[str, str] | None:
        if concept_is_used(concept, used_concepts):
            return None
        return topic, concept

    # 1) Primary plan for this question number
    plan = QUESTION_NUMBER_PLAN.get(question_number)
    if plan:
        topic, concept = plan
        picked = _pick(topic, concept)
        if picked:
            return picked

        # 2) Retry: other unused concepts under the same topic
        for alt in TOPIC_HIERARCHY.get(topic, []):
            picked = _pick(topic, alt)
            if picked:
                return picked

    # 3) Retry: walk remaining question plan slots
    for qn in sorted(QUESTION_NUMBER_PLAN.keys()):
        if qn == question_number:
            continue
        t, c = QUESTION_NUMBER_PLAN[qn]
        picked = _pick(t, c)
        if picked:
            return picked
        for alt in TOPIC_HIERARCHY.get(t, []):
            picked = _pick(t, alt)
            if picked:
                return picked

    # 4) Fallback: first unused pair in hierarchy order
    for topic, concepts in TOPIC_HIERARCHY.items():
        if normalize_concept(topic) in used_topic_norm and all(
            concept_is_used(c, used_concepts) for c in concepts
        ):
            continue
        for concept in concepts:
            picked = _pick(topic, concept)
            if picked:
                return picked

    return "project_overview", "project_overview"


def get_rag_query_for_selection(
    topic: str,
    concept: str,
    project_summary: str = "",
) -> str:
    """Build a focused RAG query from the selected topic/concept."""
    keywords = CONCEPT_RAG_KEYWORDS.get(concept) or CONCEPT_RAG_KEYWORDS.get(topic) or [concept.replace("_", " ")]
    kw = " ".join(keywords[:4])
    summary_snippet = " ".join((project_summary or "").split()[:12])
    return f"{summary_snippet} {kw}".strip()


def select_rag_chunk(rag_context: str, topic: str, concept: str) -> str:
    """
    Return a single RAG chunk (<500 tokens target) most relevant to topic/concept.
    Falls back to the first chunk if no keyword match.
    """
    text = (rag_context or "").strip()
    if not text:
        return ""

    chunks = [c.strip() for c in re.split(r"\n\s*\n", text) if c.strip()]
    if not chunks:
        chunks = [text]

    keywords = CONCEPT_RAG_KEYWORDS.get(concept) or CONCEPT_RAG_KEYWORDS.get(topic) or [concept.replace("_", " ")]
    keywords_lower = [k.lower() for k in keywords]

    best_chunk = chunks[0]
    best_score = -1
    for chunk in chunks:
        low = chunk.lower()
        score = sum(1 for k in keywords_lower if k in low)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if len(best_chunk) > MAX_RAG_CHUNK_CHARS:
        best_chunk = best_chunk[:MAX_RAG_CHUNK_CHARS].rsplit(" ", 1)[0]

    return best_chunk


def format_concept_label(concept: str) -> str:
    """Human-readable concept label for the LLM prompt."""
    return concept.replace("_", " ")


def should_use_deterministic_pipeline(
    *,
    resume_has_projects: bool,
    question_number: int,
    mode: str = "basic",
) -> bool:
    """Use deterministic topic/concept selection for project-based early questions.
    
    Q1-Q6 are the resume phase — project overview, architecture, tech stack,
    API design, database design, and challenges. Beyond Q6 the interview
    transitions to core CS, advanced, and DSA phases.
    """
    if not resume_has_projects:
        return False
    if question_number < 1 or question_number > 6:
        return False
    return True


def selection_debug_info(
    question_number: int,
    topic: str,
    concept: str,
    used_topics: list[str] | None,
    used_concepts: list[str] | None,
) -> dict[str, Any]:
    return {
        "question_number": question_number,
        "selected_topic": topic,
        "selected_concept": concept,
        "used_topics": list(used_topics or []),
        "used_concepts": list(used_concepts or []),
    }
