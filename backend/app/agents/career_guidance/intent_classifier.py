"""
Intent Classifier for the Career Guidance Agent.

Classifies user queries into intent categories to determine
whether RAG retrieval is needed or a direct LLM call suffices.
"""

import enum
import logging

logger = logging.getLogger(__name__)


class IntentType(str, enum.Enum):
    GENERAL_QUERY = "GENERAL_QUERY"
    PERSONALIZED_GUIDANCE = "PERSONALIZED_GUIDANCE"
    SKILL_GAP_ANALYSIS = "SKILL_GAP_ANALYSIS"
    CAREER_SWITCH = "CAREER_SWITCH"
<<<<<<< HEAD
=======
    PROJECT_RECOMMENDATION = "PROJECT_RECOMMENDATION"
    JOB_ROLE_MATCHING = "JOB_ROLE_MATCHING"
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a


# ── Keyword-based intent patterns ────────────────────────────────────────────

_PERSONALIZED_KEYWORDS = [
    "my resume", "my skills", "my experience", "my profile",
    "for me", "based on my", "recommend me", "personalize",
    "my background", "my career", "suggest for me", "my goal",
    "my education", "my certification", "help me",
<<<<<<< HEAD
=======
    "my strength", "my weakness", "about me",
    "my certificate", "my academic", "my performance",
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
]

_SKILL_GAP_KEYWORDS = [
    "skill gap", "missing skills", "what skills", "skills i need",
    "upskill", "reskill", "skill assessment", "skill analysis",
    "what should i learn", "what to learn", "learn next",
    "improve my skills", "weak areas", "strength and weakness",
<<<<<<< HEAD
=======
    "skill roadmap", "skill improvement", "skills to develop",
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
]

_CAREER_SWITCH_KEYWORDS = [
    "career switch", "career change", "transition", "switch career",
    "change field", "move to", "pivot", "different career",
    "new career", "switch from", "change from", "transition from",
]

<<<<<<< HEAD
=======
_PROJECT_RECOMMENDATION_KEYWORDS = [
    "what project", "project idea", "build project", "recommend project",
    "suggest project", "project suggestion", "portfolio project",
    "side project", "project to build", "next project",
    "project for resume", "showcase project", "project recommendation",
    "what should i build", "hands-on project",
]

_JOB_ROLE_MATCHING_KEYWORDS = [
    "job match", "suited for", "fit for", "qualified for",
    "job role", "what job", "which role", "which position",
    "career match", "role match", "best job", "job suggestion",
    "job recommendation", "apply for", "target company",
    "job that fits", "right role", "what position",
    "career option", "job opportunities",
]

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

def classify_intent(query: str) -> IntentType:
    """
    Classify a user query into an IntentType.

    Uses keyword matching for speed and reliability.
    Falls back to GENERAL_QUERY if no specific intent is detected.

    Parameters
    ----------
    query : str
        The raw user query.

    Returns
    -------
    IntentType
    """
    q_lower = query.lower().strip()

    # Check most specific intents first
    for kw in _CAREER_SWITCH_KEYWORDS:
        if kw in q_lower:
            logger.info("Intent: CAREER_SWITCH (keyword: '%s')", kw)
            return IntentType.CAREER_SWITCH

    for kw in _SKILL_GAP_KEYWORDS:
        if kw in q_lower:
            logger.info("Intent: SKILL_GAP_ANALYSIS (keyword: '%s')", kw)
            return IntentType.SKILL_GAP_ANALYSIS

<<<<<<< HEAD
=======
    for kw in _PROJECT_RECOMMENDATION_KEYWORDS:
        if kw in q_lower:
            logger.info("Intent: PROJECT_RECOMMENDATION (keyword: '%s')", kw)
            return IntentType.PROJECT_RECOMMENDATION

    for kw in _JOB_ROLE_MATCHING_KEYWORDS:
        if kw in q_lower:
            logger.info("Intent: JOB_ROLE_MATCHING (keyword: '%s')", kw)
            return IntentType.JOB_ROLE_MATCHING

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
    for kw in _PERSONALIZED_KEYWORDS:
        if kw in q_lower:
            logger.info("Intent: PERSONALIZED_GUIDANCE (keyword: '%s')", kw)
            return IntentType.PERSONALIZED_GUIDANCE

    logger.info("Intent: GENERAL_QUERY (no specific keywords matched)")
    return IntentType.GENERAL_QUERY
