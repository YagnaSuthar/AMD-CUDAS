"""
Dynamic Question Generator Agent (RAG-Enhanced).
Generates context-aware, resume-aware interview questions using:
- RAG context from pgvector (relevant CV chunks)
- Follow-up intelligence (related concepts from answer)
- Adaptive difficulty
- Behavior-reactive logic
"""

import logging
from typing import Any, Dict

from app.agents.Interview.prompts import (
    QUESTION_GENERATION_PROMPT,
    PHASE_DESCRIPTIONS,
    RESUME_PROJECT_QUESTION_PROMPT,
    RESUME_NO_PROJECT_QUESTION_PROMPT,
    RAG_QUESTION_GENERATION_PROMPT,
    RAG_FOLLOWUP_PROMPT,
    RESUME_PHASE_QUESTION_PROMPT,
)
from app.agents.Interview.utils import parse_json_response, InterviewTracer, estimate_tokens

logger = logging.getLogger(__name__)


def _mode_allowed_topics(mode: str, phase: str) -> set[str] | None:
    """Return a conservative allowlist of topics per mode for non-resume phases.

    We keep this minimal and only use it for validation/logging.
    Returning None means: do not enforce/validate.
    """
    m = (mode or "").strip().lower() or "basic"
    ph = (phase or "").strip().lower()
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
    }

    per_phase = allow.get(m, allow["basic"]).get(ph)
    return set(per_phase) if per_phase else None


async def generate_question(
    context: str = "",
    difficulty: str = "medium",
    llm: Any = None,
    *,
    last_question: str = "",
    last_answer: str = "",
    last_answer_summary: str = "",
    behavior: str = "neutral",
    skill_summary: str = "",
    resume_has_projects: bool = False,
    resume_project_summary: str = "",
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
) -> Dict[str, Any]:
    """
    Generate a single interview question.

    Priority for context:
    1. If followup_context available → RAG follow-up prompt (related concepts)
    2. If rag_context available → RAG-enhanced prompt (CV chunks)
    3. If first question → resume-aware prompt
    4. Fallback → standard context-aware prompt

    Parameters
    ----------
    rag_context : str
        Retrieved CV chunks from pgvector for context.
    followup_context : str
        Related concepts retrieved after candidate's answer.
    last_answer : str
        Raw last answer text (for follow-up intelligence).
    """
    logger.info(
        "QuestionGeneratorAgent: generating %s question (first=%s, rag=%s, followup=%s)",
        difficulty, is_first_question, bool(rag_context), bool(followup_context),
    )

    effective_skills = skill_summary or context
    
    # 4. Context Cleaning
    bad_phrases = ["skip", "no answer", "undefined"]
    clean_last_answer = last_answer if last_answer and not any(x in last_answer.lower() for x in bad_phrases) else ""
    clean_last_answer_summary = last_answer_summary if last_answer_summary and not any(x in last_answer_summary.lower() for x in bad_phrases) else ""
    
    last_eval_class = last_evaluation.get("answer_classification") if last_evaluation else None
    
    sources = []

    # ── Prepare Context ──────────────────────────────────────────────────
    rag_chunks = (rag_context or "").strip() or (followup_context or "").strip()

    if rag_context:
        sources.append("resume")
    if followup_context:
        sources.append("resume")
    
    # ── Format Prompt ──────────────────────────────────────────────────
    if phase == "resume":
        prompt = RESUME_PHASE_QUESTION_PROMPT.format(
            rag_chunks=rag_chunks,
            skill_summary=skill_summary or "Not listed",
            project_summary=resume_project_summary or "No summary available",
            topic=current_topic
        )
    else:
        prompt = QUESTION_GENERATION_PROMPT.format(
            rag_chunks=rag_chunks,
            phase=phase,
            topic=current_topic,
            type=current_intent
        )


    # ── Observability ──
    InterviewTracer.log_context_source(sources)
    InterviewTracer.log_token_usage(
        resume_tokens=estimate_tokens(resume_project_summary or ""),
        jd_tokens=estimate_tokens(job_description or ""),
        history_tokens=estimate_tokens(clean_last_answer or ""),
        total_tokens=estimate_tokens(prompt)
    )
    InterviewTracer.log_prompt(phase, current_topic, current_intent, prompt)
    InterviewTracer.log_pipeline_step(4, "rag", bool(rag_chunks))
    InterviewTracer.log_pipeline_step(5, "prompt", "Generated (see PROMPT DEBUG)")

    max_retries = 1
    current_attempt = 0
    
    while current_attempt <= max_retries:
        try:
            response = await llm.ainvoke(prompt)
            content: str = getattr(response, "content", str(response))
            result = parse_json_response(content)
            
            question = result.get("question", "").strip()
            InterviewTracer.log_pipeline_step(6, "LLM response", question)
            word_count = len(question.split())
            is_valid = True

            # ── Role-aware validation (logging/guardrail only) ───────────
            # Topic selection is primarily orchestrator-driven, but the LLM may
            # still return a mismatched topic. We warn and fall back to the
            # orchestrator-selected current_topic when it violates the allowlist.
            llm_topic = (result.get("topic") or current_topic or "").strip()
            allowed = _mode_allowed_topics(mode, phase)
            if allowed is not None and llm_topic not in allowed:
                logger.warning(
                    "QuestionGeneratorAgent: mode-topic mismatch mode=%s phase=%s llm_topic=%s allowed=%s; using current_topic=%s",
                    mode,
                    phase,
                    llm_topic,
                    sorted(list(allowed)),
                    current_topic,
                )
                result["topic"] = current_topic
            
            # ── System Rules Validation ───────────────────────────────────
            
            # 1. Length Validation (Max 15 words)
            if word_count > 15:
                logger.warning("Question too long (%d words): %s", word_count, question)
                is_valid = False
            
            # 2. Single Intent Validation (No 'and')
            if " and " in question.lower():
                logger.warning("Complexity check: Question contains 'and': %s", question)
                is_valid = False
                
            # 3. Validation: Invalid Context referencing
            if any(bad in question.lower() for bad in ["undefined", "null", "none context"]):
                logger.warning("Validation check: Question references invalid context: %s", question)
                is_valid = False
                
            if is_valid or current_attempt >= max_retries:
                if word_count > 15 and "." in question:
                    # Final fallback truncation
                    question = question.split(".")[0].strip()
                
                logger.info(
                    "QuestionGeneratorAgent: generated %s %s on topic '%s' (attempt %d)",
                    result.get("type", "primary"), result.get("intent", "concept"), result.get("topic"), current_attempt + 1
                )
                
                return {
                    "question": question,
                    "topic": result.get("topic", current_topic),
                    "phase": result.get("phase", phase),
                    "type": result.get("type", current_intent),
                }
            
            # Retry with stricter instruction
            current_attempt += 1
            logger.info("Retrying question generation (attempt %d)...", current_attempt + 1)
            prompt += "\n\nSTRICT RE-GENERATE: Keep it UNDER 18 words and ask only ONE thing. Absolutely no 'and'."
            
        except Exception as exc:
            logger.error("QuestionGeneratorAgent LLM error: %s", exc)
            if current_attempt >= max_retries:
                raise exc
            current_attempt += 1
