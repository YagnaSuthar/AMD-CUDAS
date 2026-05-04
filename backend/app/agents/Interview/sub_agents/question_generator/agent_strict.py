"""
Strict Question Generator Agent (Role-aware, 15-question, no behavioral, no repetition, difficulty progression).
"""

import logging
import difflib
import re
import json
from typing import Any, Dict

from app.agents.Interview.prompts import (
    QUESTION_GENERATION_PROMPT,
    PHASE_DESCRIPTIONS,
    RESUME_PROJECT_QUESTION_PROMPT,
    RESUME_NO_PROJECT_QUESTION_PROMPT,
    RAG_QUESTION_GENERATION_PROMPT,
    RAG_FOLLOWUP_PROMPT,
    RESUME_PHASE_QUESTION_PROMPT,
    STRICT_QUESTION_GENERATION_PROMPT,
    BASIC_PRACTICE_QUESTION_GENERATION_PROMPT,
)
from app.agents.Interview.utils import parse_json_response, InterviewTracer, estimate_tokens

logger = logging.getLogger(__name__)

# ── Strict Rules Constants ────────────────────────────────────────────────
MAX_QUESTION_WORDS = 18
FORBIDDEN_PHRASES = [" and ", "undefined", "null", "none context"]
FORBIDDEN_BEHAVIORAL_KEYWORDS = ["team", "conflict", "describe a time", "tell me about", "how did you handle"]
FORBIDDEN_CONCEPTS = ["behavioral", "teamwork", "communication", "leadership"]
ALLOWED_MODES = {
    "basic",
    "frontend",
    "backend",
    "mern",
    "fullstack",
    "java",
    "python",
    "cybersecurity",
    "data_analyst",
    "data_science",
    "datascience",
    "ml_ai",
    "cloud",
    "devops",
}

# Similarity guardrail: deliberately conservative. High overlap => reject.
# Tightened to catch paraphrases as well.
SEMANTIC_JACCARD_THRESHOLD = 0.55
SEMANTIC_BIGRAM_JACCARD_THRESHOLD = 0.40
SEMANTIC_SEQUENCE_RATIO_THRESHOLD = 0.86

# Minimal stopword list for semantic repetition checks (no external deps).
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "while", "what", "why",
    "how", "is", "are", "was", "were", "do", "does", "did", "can", "could", "should", "would",
    "explain", "describe", "define", "tell", "me", "about", "you", "your", "in", "of", "to", "for",
    "on", "with", "from", "as", "at", "by", "give", "one", "key", "concept", "idea",
}

# ── Question Counting Helpers ─────────────────────────────────────────────
def _question_number_by_phase(question_number: int) -> str:
    """Map 1–15 to phase buckets."""
    if 1 <= question_number <= 2:
        return "resume"
    if 3 <= question_number <= 7:
        return "core"
    if 8 <= question_number <= 12:
        return "advanced"
    if 13 <= question_number <= 15:
        return "dsa_scenario"
    return "core"

def _difficulty_by_number(question_number: int) -> str:
    """Map 1–15 to difficulty levels."""
    if 1 <= question_number <= 3:
        return "easy"
    if 4 <= question_number <= 8:
        return "medium"
    if 9 <= question_number <= 12:
        return "hard"
    if 13 <= question_number <= 15:
        return "advanced"
    return "medium"

def _intent_by_bucket(phase_bucket: str) -> str:
    """Convert phase bucket to intent."""
    if phase_bucket == "dsa_scenario":
        return "reasoning"
    return "concept"

# ── Validation Helpers ───────────────────────────────────────────────────
def _is_behavioral(question: str) -> bool:
    q = question.lower()
    # Reduce false positives: only flag if a behavioral keyword appears without a clear technical anchor
    has_behavioral = any(k in q for k in FORBIDDEN_BEHAVIORAL_KEYWORDS)
    has_concept = any(c in q for c in FORBIDDEN_CONCEPTS)
    # If there’s a technical anchor (common in our modes), allow the question even if it contains a behavioral keyword
    tech_anchors = {"api", "database", "react", "node", "python", "java", "system", "design", "security", "auth", "frontend", "backend", "fullstack", "cyber"}
    has_tech = any(t in q for t in tech_anchors)
    return (has_behavioral or has_concept) and not has_tech

def _is_multi_part(question: str) -> bool:
    return " and " in question.lower() or question.count("?") > 1

def _is_too_long(question: str) -> bool:
    return len(question.split()) > MAX_QUESTION_WORDS

def _contains_invalid_context(question: str) -> bool:
    q = question.lower()
    return any(bad in q for bad in ["undefined", "null", "none context"])

def _is_repeat(question: str, history: list) -> bool:
    q_norm = question.strip().lower()
    for h in history:
        if isinstance(h, str) and q_norm == h.strip().lower():
            return True
    return False


def _tokenize_for_similarity(text: str) -> set[str]:
    t = (text or "").lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    tokens = [x.strip() for x in t.split() if x.strip()]
    tokens = [x for x in tokens if x not in _STOPWORDS and len(x) > 2]
    return set(tokens)


def _bigrams(tokens: list[str]) -> set[str]:
    if not tokens:
        return set()
    if len(tokens) < 2:
        return set(tokens)
    return {f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)}


def _normalize_for_sequence(text: str) -> str:
    t = (text or "").strip().lower()
    if not t:
        return ""
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = " ".join([w for w in t.split() if w and w not in _STOPWORDS])
    return " ".join(t.split())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return float(inter / union) if union else 0.0


def _is_semantic_repeat(question: str, history: list[str]) -> bool:
    """Heuristic semantic repetition check.

    Reject if the new question shares too much content with any historical question.
    This is intentionally conservative to satisfy the "ZERO SEMANTIC REPETITION" rule.
    """
    q_tokens = _tokenize_for_similarity(question)
    q_norm = _normalize_for_sequence(question)
    if not q_tokens and not q_norm:
        return False

    q_words = [w for w in re.sub(r"[^a-z0-9\s]", " ", (question or "").lower()).split() if w]
    q_words = [w for w in q_words if w not in _STOPWORDS and len(w) > 2]
    q_bigrams = _bigrams(q_words)

    for h in history or []:
        if not isinstance(h, str) or not h.strip():
            continue
        h_tokens = _tokenize_for_similarity(h)

        # 1) Token-set overlap (good for meaning-level similarity)
        sim = _jaccard(q_tokens, h_tokens)
        if sim >= SEMANTIC_JACCARD_THRESHOLD:
            return True

        # 2) Bigram overlap (catches paraphrases with similar phrasing)
        h_words = [w for w in re.sub(r"[^a-z0-9\s]", " ", (h or "").lower()).split() if w]
        h_words = [w for w in h_words if w not in _STOPWORDS and len(w) > 2]
        h_bigrams = _bigrams(h_words)
        sim2 = _jaccard(q_bigrams, h_bigrams)
        if sim2 >= SEMANTIC_BIGRAM_JACCARD_THRESHOLD:
            return True

        # 3) Sequence similarity after normalization (catches near-paraphrases)
        h_norm = _normalize_for_sequence(h)
        if q_norm and h_norm:
            ratio = difflib.SequenceMatcher(a=q_norm, b=h_norm).ratio()
            if ratio >= SEMANTIC_SEQUENCE_RATIO_THRESHOLD:
                return True

        # 4) Extra strictness: if both token and sequence are moderately high, reject
        if q_norm and h_norm:
            ratio2 = difflib.SequenceMatcher(a=q_norm, b=h_norm).ratio()
            if sim >= 0.42 and ratio2 >= 0.78:
                return True
    return False


def _normalize_label(s: str) -> str:
    return (s or "").strip().lower()


def _compute_unused_subtopics(available_subtopics: list | None, used_subtopics: list | None) -> list[str]:
    av = [str(x).strip() for x in (available_subtopics or []) if str(x).strip()]
    used = {_normalize_label(x) for x in (used_subtopics or []) if str(x).strip()}
    return [x for x in av if _normalize_label(x) not in used]

def _validate_question(
    question: str,
    mode: str,
    question_number: int,
    history: list,
    *,
    subtopic: str = "",
    unused_subtopics: list[str] | None = None,
    concept: str = "",
    used_concepts: list[str] | None = None,
) -> tuple[bool, str]:
    """Return (is_valid, reason)."""
    if mode == "basic":
        # SIMPLIFIED VALIDATION FOR BASIC MODE (as requested by user)
        if _is_repeat(question, history):
            return False, "repeat"
        if _is_semantic_repeat(question, [h for h in (history or []) if isinstance(h, str)]):
            return False, "semantic_repeat"
        if used_concepts is not None:
            if not str(concept or "").strip():
                pass # ignore missing concept error to prevent loop
            elif _normalize_label(concept) in {_normalize_label(x) for x in used_concepts}:
                return False, "concept_reused"
        return True, "ok"

    if mode != "basic" and question_number > 15:
        return False, "exceeds_15_questions"
    if mode != "basic" and _is_behavioral(question):
        return False, "behavioral_question"
    if _is_repeat(question, history):
        return False, "repeat"
    if _is_semantic_repeat(question, [h for h in (history or []) if isinstance(h, str)]):
        return False, "semantic_repeat"
    if _is_multi_part(question):
        return False, "multi_part"
    if _is_too_long(question):
        return False, "too_long"
    if _contains_invalid_context(question):
        return False, "invalid_context"

    if unused_subtopics is not None:
        # Must pick ONLY from unused subtopics
        if not str(subtopic or "").strip():
            return False, "missing_subtopic"
        if _normalize_label(subtopic) not in {_normalize_label(x) for x in unused_subtopics}:
            return False, "subtopic_reused_or_invalid"

    if used_concepts is not None:
        # Must introduce a NEW concept
        if not str(concept or "").strip():
            return False, "missing_concept"
        if _normalize_label(concept) in {_normalize_label(x) for x in used_concepts}:
            return False, "concept_reused"

    return True, "ok"

def _mode_allowed_topics(mode: str, phase_bucket: str | None) -> set[str] | None:
    """Return allowed topics for strict modes; None means allow any."""
    m = (mode or "").strip().lower()
    if m == "basic":
        return None
    ph = (phase_bucket or "").strip().lower()
    if ph in {"resume", "behavioral"}:
        return None

    allow = {
        "basic": {
            "core": {"DBMS", "OS", "OOP"},
            "problem_solving": {"DSA_basics", "logic_reasoning", "real_world_scenario"},
        },
        "frontend": {
            "core": {"HTML", "CSS", "JavaScript", "React", "Browser_Rendering_DOM"},
            "problem_solving": {"arrays_strings", "async_event_loop", "ui_state_logic"},
        },
        "backend": {
            "core": {"DBMS", "APIs", "Caching", "Authentication", "System_Design_Basics"},
            "problem_solving": {"hashing_maps", "queues_streams", "data_flow_reasoning"},
        },
        "mern": {
            "core": {"React", "Node_APIs", "MongoDB", "Auth_Fullstack"},
            "problem_solving": {"api_data_flow", "logic_reasoning", "real_world_scenario"},
        },
        "fullstack": {
            "core": {"React", "Node_APIs", "MongoDB", "Auth_Fullstack"},
            "problem_solving": {"api_data_flow", "logic_reasoning", "real_world_scenario"},
        },
        "java": {
            "core": {"java_language_concepts", "OOP", "memory_runtime"},
            "problem_solving": {"language_specific_dsa", "logic_reasoning", "real_world_scenario"},
        },
        "python": {
            "core": {"python_language_concepts", "OOP", "memory_runtime"},
            "problem_solving": {"language_specific_dsa", "logic_reasoning", "real_world_scenario"},
        },
        "cybersecurity": {
            "core": {"network_security", "auth_sessions", "encryption_basics", "web_security"},
            "problem_solving": {"threat_modeling_scenarios", "logic_reasoning"},
        },
        "data_analyst": {
            "core": {"data_cleaning", "sql", "eda", "visualization", "statistics", "pandas_excel", "business_insights"},
            "problem_solving": {"sql_queries", "data_quality", "dashboard_metrics", "logic_reasoning"},
        },
        "data_science": {
            "core": {"data_cleaning", "eda", "feature_engineering", "model_selection", "model_evaluation", "statistics"},
            "problem_solving": {"ml_scenarios", "bias_variance", "data_leakage", "logic_reasoning"},
        },
        "datascience": {
            "core": {"data_cleaning", "eda", "feature_engineering", "model_selection", "model_evaluation", "statistics"},
            "problem_solving": {"ml_scenarios", "bias_variance", "data_leakage", "logic_reasoning"},
        },
        "ml_ai": {
            "core": {"data_preprocessing", "model_selection", "model_evaluation", "overfitting", "hyperparameter_tuning", "ml_metrics"},
            "problem_solving": {"ml_scenarios", "bias_variance", "data_leakage", "logic_reasoning"},
        },
        "devops": {
            "core": {"ci_cd", "docker", "kubernetes", "linux", "monitoring_logging", "infra_as_code", "cloud_basics"},
            "problem_solving": {"incident_response", "deployment_strategies", "scaling_reliability", "logic_reasoning"},
        },
        "cloud": {
            "core": {"cloud_basics", "iam", "networking", "compute_storage", "observability", "cost_optimization"},
            "problem_solving": {"incident_response", "deployment_strategies", "scaling_reliability", "logic_reasoning"},
        },
    }

    per_phase = allow.get(m, allow["basic"]).get(ph)
    return set(per_phase) if per_phase else None


def _extract_first_project_name(resume_project_summary: str) -> str:
    text = (resume_project_summary or "").strip()
    if not text:
        return ""

    def _looks_like_real_project_title(candidate: str) -> bool:
        c = (candidate or "").strip()
        if not c:
            return False
        low = c.lower()
        if low.startswith((
            "developed ",
            "built ",
            "created ",
            "implemented ",
            "designed ",
            "made ",
            "worked on ",
        )):
            return False
        if low in {"project", "projects", "capstone", "final year project"}:
            return False
        if len(c.split()) < 2 and len(c) < 6:
            return False
        return True

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if not line:
            continue

        # IMPORTANT: Do NOT split on a plain hyphen. Many resumes contain
        # hyphenated words (e.g., "multi-tenant") which would be truncated.
        for sep in (":", "—", "|"):
            if sep in line:
                candidate = line.split(sep, 1)[0].strip()
                if _looks_like_real_project_title(candidate):
                    return candidate

        if _looks_like_real_project_title(line):
            return line
    return ""


def _sanitize_question_text(
    question: str,
    *,
    mode: str,
    resume_has_projects: bool,
    resume_project_summary: str,
) -> str:
    q = (question or "").strip()
    if not q:
        return q

    def _fallback_skill_question(non_basic_mode: str) -> str:
        m = (non_basic_mode or "").strip().lower()
        return {
            "frontend": "What is the difference between controlled and uncontrolled components in React?",
            "backend": "What is the difference between an inner join and a left join in SQL?",
            "mern": "What is the purpose of MongoDB indexes, and how do they affect query performance?",
            "java": "What is the difference between an interface and an abstract class in Java?",
            "python": "What is the difference between a list and a tuple in Python, and when would you use each?",
            "data_analyst": "What is the difference between mean and median, and when is median a better summary?",
            "data_science": "What is data leakage, and how can it happen during model training?",
            "ml_ai": "What is overfitting, and name two ways to reduce it?",
            "devops": "What is the difference between CI and CD?",
            "cloud": "What is the difference between horizontal scaling and vertical scaling?",
            "cybersecurity": "What is the difference between authentication and authorization?",
        }.get(m, "What is overfitting, and name two ways to reduce it?")

    replacements = {
        "project_overview": "your project",
        "tech_stack": "tech stack",
        "java_language_concepts": "Java language concepts",
        "python_language_concepts": "Python language concepts",
        "network_security": "network security",
    }
    for k, v in replacements.items():
        if k in q:
            q = q.replace(k, v)

    if "_" in q:
        q = " ".join([tok.replace("_", " ") for tok in q.split()])
        q = " ".join(q.split())

    low = q.lower()
    if "idea in your work" in low or "idea in your project" in low:
        if resume_has_projects:
            project_name = _extract_first_project_name(resume_project_summary)
            if project_name:
                q = f"Can you briefly describe {project_name} and its main functionality?"
            else:
                q = _fallback_skill_question(mode) if mode != "basic" else "Can you briefly describe your project and its main functionality?"
        else:
            q = _fallback_skill_question(mode) if mode != "basic" else "Can you describe a practical approach you would take in this situation?"

    if mode != "basic" and resume_has_projects:
        project_name = _extract_first_project_name(resume_project_summary)
        if not project_name:
            low2 = q.lower()
            if "your project" in low2 or "in your project" in low2 or "from that project" in low2:
                q = _fallback_skill_question(mode)

    q = q.rstrip(" .")
    if not q.endswith("?"):
        q = q + "?"
    return q


async def generate_question_strict(
    *,
    llm: Any,
    difficulty: str = "basic",
    skill_summary: str = "",
    context: str = "",
    resume_project_summary: str = "",
    resume_has_projects: bool = True,
    is_first_question: bool = False,
    job_description: str = "",
    rag_context: str = "",
    followup_context: str = "",
    phase: str = "core",
    mode: str = "basic",
    previous_topics: list = None,
    topic_depth: int = 0,
    current_topic: str = "initial",
    current_intent: str = "concept",
    last_evaluation: dict = None,
    last_answer: str = "",
    last_answer_summary: str = "",
    question_number: int = 1,
    question_history: list = None,
    topic_history: list = None,
    answer_quality: str = "",
    available_subtopics: list | None = None,
    used_subtopics: list | None = None,
    used_concepts: list | None = None,
    elapsed_time: int = 0,
    **kwargs,
) -> Dict[str, Any]:
    """
    Generate a single interview question with strict role-aware rules.

    New parameters:
        question_number: 1–15 (used for difficulty/phase bucketing)
        question_history: list of past question strings (for repetition guard)
        topic_history: list of past topic strings (for repetition guard)
        answer_quality: "strong" | "partial" | "weak" | "skip" (adaptive logic)
    """
    logger.info(
        "QuestionGeneratorAgent: generating %s question (first=%s, rag=%s, followup=%s, mode=%s, qnum=%d)",
        difficulty, is_first_question, bool(rag_context), bool(followup_context), mode, question_number,
    )

    # Normalize inputs
    mode = (mode or "").strip().lower() or "basic"
    if mode not in ALLOWED_MODES:
        mode = "basic"
    previous_topics = previous_topics or []
    question_history = question_history or []
    topic_history = topic_history or []
    used_concepts = used_concepts or []
    effective_skills = skill_summary or context

    unused_subtopics = _compute_unused_subtopics(available_subtopics, used_subtopics) if available_subtopics is not None else None

    # Determine strict phase bucket and difficulty for non-basic modes
    if mode != "basic":
        phase_bucket = _question_number_by_phase(question_number)
        strict_difficulty = _difficulty_by_number(question_number)
        strict_intent = _intent_by_bucket(phase_bucket)
    else:
        phase_bucket = phase
        strict_difficulty = difficulty
        strict_intent = current_intent

    # Adaptive logic: if answer is weak/skip, force topic change (skip handling)
    if answer_quality in {"weak", "skip"} or last_answer.lower() in {"skip", "no idea"}:
        topic_depth = 0
        current_intent = "primary"
        # Orchestrator will change topic; we just respect the inputs

    # 4. Context Cleaning
    bad_phrases = ["skip", "no answer", "undefined"]
    clean_last_answer = last_answer if last_answer and not any(x in last_answer.lower() for x in bad_phrases) else ""
    clean_last_answer_summary = last_answer_summary if last_answer_summary and not any(x in last_answer_summary.lower() for x in bad_phrases) else ""

    last_eval_class = last_evaluation.get("answer_classification") if last_evaluation else None

    sources = []
    rag_chunks = (rag_context or "").strip() or (followup_context or "").strip()
    if rag_context:
        sources.append("resume")
    if followup_context:
        sources.append("resume")

    # ── Prompt Selection ──────────────────────────────────────────────────
    
    total_questions = 15 if mode != "basic" else "N/A"
    projects_content = rag_chunks if rag_chunks else (resume_project_summary or "None")

    if mode == "basic":
        prompt = BASIC_PRACTICE_QUESTION_GENERATION_PROMPT.format(
            mode=mode,
            question_number=question_number,
            last_answer=answer_quality or "None",
            used_concepts=json.dumps(used_concepts[-20:]) if used_concepts else "[]",
        )
    else:
        prompt = STRICT_QUESTION_GENERATION_PROMPT.format(
            mode=mode,
            question_number=question_number,
            used_concepts=json.dumps(used_concepts[-20:]) if used_concepts else "[]",
            used_topics=json.dumps([str(x) for x in topic_history[-10:]]) if topic_history else "[]",
            last_answer=answer_quality or "None"
        )

        # Job-specific relevance control (language-only; does not change flow/count/eval/schema)
        project_name = _extract_first_project_name(resume_project_summary) if question_number == 1 else ""
        if resume_has_projects and question_number == 1 and project_name:
            prompt += "\n\nSTRICT RULES (JOB-SPECIFIC):"
            prompt += "\n- Q1 MUST be project-based and role-relevant."
            prompt += f"\n- Use the project name '{project_name}' in the question."
            prompt += "\n- Ask about a specific implementation decision, challenge, or trade-off from that project."
            prompt += "\n- Do NOT ask generic 'overview' questions unless you reference a concrete technical detail."
        else:
            prompt += "\n\nSTRICT RULES (JOB-SPECIFIC):"
            if resume_has_projects and question_number == 1 and not project_name:
                prompt += "\n- Resume projects exist, but no valid project title is available to reference."
                prompt += "\n- DO NOT mention resume projects or ask project-based questions."
                prompt += "\n- Ask a skill-based question strictly aligned to the selected role."
            elif not resume_has_projects:
                prompt += "\n- No relevant resume projects exist for this mode."
                prompt += "\n- DO NOT mention resume projects or ask project-based questions."
                prompt += "\n- Ask a skill-based question strictly aligned to the selected role."

        if mode == "data_analyst":
            prompt += "\n\nROLE FILTER: Data Analyst"
            prompt += "\n- ONLY ask about data cleaning, SQL, EDA, visualization, statistics, pandas/Excel, or business insights."
            prompt += "\n- DO NOT ask about APIs, caching, system design, or backend architecture."

        if mode == "ml_ai":
            prompt += "\n\nROLE FILTER: ML/AI"
            prompt += "\n- ONLY ask about preprocessing, models, evaluation, overfitting, and tuning."
            prompt += "\n- DO NOT ask about DBMS, OS, APIs, or backend systems."

        if mode == "cloud":
            prompt += "\n\nROLE FILTER: Cloud"
            prompt += "\n- ONLY ask about deployment, IAM, networking, monitoring, reliability, and cost optimization."
            prompt += "\n- DO NOT ask frontend or ML theory questions."

        if mode == "mern":
            prompt += "\n\nROLE FILTER: MERN"
            prompt += "\n- Focus on React, Node APIs, MongoDB, authentication, and fullstack data flow."
            prompt += "\n- Avoid OS theory and unrelated domains."

    if unused_subtopics is not None:
        prompt += f"\n- You MUST pick subtopic ONLY from this unused list: {', '.join(unused_subtopics) if unused_subtopics else 'NONE'}"

    # Require structured output fields for uniqueness tracking.
    prompt += "\n\nOUTPUT JSON MUST INCLUDE: question, concept, difficulty. Use natural language; avoid robotic phrases like 'idea' or 'concept' in the question itself."

    # ── Observability ──
    InterviewTracer.log_context_source(sources)
    InterviewTracer.log_token_usage(
        resume_tokens=estimate_tokens(resume_project_summary or ""),
        jd_tokens=estimate_tokens(job_description or ""),
        history_tokens=estimate_tokens(clean_last_answer or ""),
        total_tokens=estimate_tokens(prompt)
    )
    InterviewTracer.log_prompt(phase_bucket, current_topic, strict_intent, prompt)
    InterviewTracer.log_pipeline_step(4, "rag", bool(rag_chunks))
    InterviewTracer.log_pipeline_step(5, "prompt", "Generated (see PROMPT DEBUG)")

    max_retries = 2
    current_attempt = 0
    last_error = ""

    while current_attempt <= max_retries:
        try:
            response = await llm.ainvoke(prompt)
            content: str = getattr(response, "content", str(response))
            result = parse_json_response(content)

            question = (result.get("question", "")).strip()
            InterviewTracer.log_pipeline_step(6, "LLM response", question)

            # ── Deterministic fallback for missing subtopic/concept ────────────────
            subtopic_raw = result.get("subtopic")
            concept_raw = result.get("concept")
            subtopic = str(subtopic_raw or "").strip()
            concept = str(concept_raw or "").strip()

            # If LLM omitted subtopic, fall back to current_topic (orchestrator guarantees it’s from unused list)
            if not subtopic and unused_subtopics:
                subtopic = current_topic
                logger.warning(
                    "QuestionGeneratorAgent: LLM omitted subtopic; falling back to current_topic=%s", current_topic
                )
            # If LLM omitted concept, synthesize from topic + question_number
            if not concept:
                concept = f"{current_topic}_q{question_number}"
                logger.warning(
                    "QuestionGeneratorAgent: LLM omitted concept; synthesizing=%s", concept
                )

            # ── Strict Validation for non-basic modes ───────────────────────
            is_valid, reason = _validate_question(
                question,
                mode,
                question_number,
                question_history,
                subtopic=subtopic,
                unused_subtopics=unused_subtopics,
                concept=concept,
                used_concepts=used_concepts,
            )
            if not is_valid:
                logger.warning(
                    "QuestionGeneratorAgent: validation failed (mode=%s qnum=%d reason=%s): %s",
                    mode, question_number, reason, question,
                )
                # Retry with stricter instruction
                current_attempt += 1
                if current_attempt <= max_retries:
                    prompt += f"\n\nSTRICT RE-GENERATE (attempt {current_attempt+1}): Fix violation: {reason}. Keep UNDER {MAX_QUESTION_WORDS} words, single intent, no behavioral, role-specific to {mode}. Also ensure subtopic is unused and concept is new."
                    continue
                # Fallback: truncate and sanitize
                if reason == "too_long" and "." in question:
                    question = question.split(".")[0].strip()
                elif reason in {"behavioral_question", "multi_part"}:
                    # Fallback generic question
                    question = f"What is a key {current_topic} concept you use?"
                else:
                    question = f"Explain one {current_topic} idea in your work."

            # Language sanitization (no behavior/flow changes): remove internal labels
            # and unnatural phrasing while keeping the same topic/intent.
            question = _sanitize_question_text(
                question,
                mode=mode,
                resume_has_projects=bool(resume_has_projects),
                resume_project_summary=resume_project_summary or "",
            )

            if mode != "basic" and bool(resume_has_projects):
                project_name_now = _extract_first_project_name(resume_project_summary or "")
                if not project_name_now:
                    qlow = (question or "").lower()
                    if "your project" in qlow or "in your project" in qlow or "that project" in qlow or "from that project" in qlow:
                        question = _sanitize_question_text(
                            question,
                            mode=mode,
                            resume_has_projects=True,
                            resume_project_summary="",
                        )

            # Role-aware topic guardrail (logging only)
            llm_topic = (result.get("topic") or current_topic or "").strip()
            allowed = _mode_allowed_topics(mode, phase_bucket)
            if allowed is not None and llm_topic not in allowed:
                logger.warning(
                    "QuestionGeneratorAgent: mode-topic mismatch mode=%s phase=%s llm_topic=%s allowed=%s; using current_topic=%s",
                    mode,
                    phase_bucket,
                    llm_topic,
                    sorted(list(allowed)),
                    current_topic,
                )
                result["topic"] = current_topic

            # Final word count truncation safety
            if len(question.split()) > MAX_QUESTION_WORDS and "." in question:
                question = question.split(".")[0].strip()

            # Final pass sanitization to avoid leaking internal labels.
            question = _sanitize_question_text(
                question,
                mode=mode,
                resume_has_projects=bool(resume_has_projects),
                resume_project_summary=resume_project_summary,
            )

            logger.info(
                "QuestionGeneratorAgent: generated %s %s on topic '%s' (attempt %d, qnum=%d)",
                result.get("type", "primary"), result.get("intent", "concept"), result.get("topic"), current_attempt + 1, question_number,
            )
            return {
                "question": question,
                "topic": result.get("topic", current_topic),
                "subtopic": subtopic,
                "concept": concept,
                "phase": result.get("phase", phase_bucket),
                "type": result.get("type", strict_intent),
                "difficulty": strict_difficulty,
                "intent": strict_intent,
            }

        except Exception as exc:
            logger.error("QuestionGeneratorAgent LLM error: %s", exc)
            last_error = str(exc)
            if current_attempt >= max_retries:
                raise exc
            current_attempt += 1
            prompt += f"\n\nSTRICT RE-GENERATE (attempt {current_attempt+1}): Keep it UNDER {MAX_QUESTION_WORDS} words and ask only ONE thing. Absolutely no 'and'."

    # If all retries failed, raise the last error
    raise RuntimeError(f"Question generation failed after retries: {last_error}")
