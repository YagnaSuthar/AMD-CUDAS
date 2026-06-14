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
from app.services.embedding_service import EmbeddingService
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

# Similarity guardrail: ultra-conservative. ANY paraphrase or similar meaning => reject.
# Aggressive thresholds to ensure ZERO semantic repetition across all modes.
SEMANTIC_JACCARD_THRESHOLD = 0.45
SEMANTIC_BIGRAM_JACCARD_THRESHOLD = 0.32
SEMANTIC_SEQUENCE_RATIO_THRESHOLD = 0.80

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


def normalize_question(q: str) -> str:
    if not q:
        return ""
    q = q.lower()
    q = re.sub(r'[^\w\s]', '', q)  # Remove punctuation
    q = " ".join(q.split())        # Remove extra spaces/newlines
    return q


def normalize_concept(c: str) -> str:
    if not c:
        return ""
    c = c.lower()
    c = re.sub(r'[^\w\s]', '', c)
    c = " ".join(c.split())
    # Stemming plurals/variations to collapse duplicate concepts
    words = c.split()
    stemmed = []
    for w in words:
        if w.endswith("ies"):
            w = w[:-3] + "y"
        elif w.endswith("es") and w not in ("postgres", "express", "redis"):
            w = w[:-2]
        elif w.endswith("s") and not w.endswith("ss") and w not in ("postgres", "redis", "dbms", "os", "css"):
            w = w[:-1]
        if w in ("join", "joins"):
            w = "join"
        elif w in ("indexing", "indexes", "index"):
            w = "index"
        elif w in ("caching", "cache", "caches"):
            w = "cache"
        elif w in ("balancing", "balancer", "balancers"):
            w = "balancer"
        elif w in ("transaction", "transactions", "transactional"):
            w = "transaction"
        stemmed.append(w)
    return " ".join(stemmed)


def check_exact_duplicate(question: str, question_history: list[str]) -> bool:
    norm_candidate = normalize_question(question)
    for q in question_history:
        if isinstance(q, str) and normalize_question(q) == norm_candidate:
            return True
    return False


def check_concept_duplicate(concept: str, secondary_concept: str, used_concepts: list[str]) -> bool:
    norm_c = normalize_concept(concept)
    norm_sc = normalize_concept(secondary_concept)
    
    normalized_used = [normalize_concept(uc) for uc in used_concepts if uc]
    
    # Check primary concept
    if norm_c:
        for uc in normalized_used:
            if not uc:
                continue
            if norm_c == uc:
                return True
            if len(norm_c) > 2 and len(uc) > 2:
                if norm_c in uc or uc in norm_c:
                    return True
            words_c = set(norm_c.split())
            words_uc = set(uc.split())
            if words_c and words_uc:
                jaccard = len(words_c & words_uc) / len(words_c | words_uc)
                if jaccard >= 0.5:
                    return True
                    
    # Check secondary concept
    if norm_sc:
        for uc in normalized_used:
            if not uc:
                continue
            if norm_sc == uc:
                return True
            if len(norm_sc) > 2 and len(uc) > 2:
                if norm_sc in uc or uc in norm_sc:
                    return True
            words_sc = set(norm_sc.split())
            words_uc = set(uc.split())
            if words_sc and words_uc:
                jaccard = len(words_sc & words_uc) / len(words_sc | words_uc)
                if jaccard >= 0.5:
                    return True
                    
    return False


def _normalize_for_sequence(text: str) -> str:
    """Strip punctuation and collapse whitespace for SequenceMatcher comparison."""
    t = re.sub(r"[^a-z0-9\s]", " ", (text or "").lower())
    return " ".join(t.split())


def check_semantic_similarity(candidate: str, question_history: list[str], threshold: float = 0.78) -> tuple[bool, float, str]:
    history_clean = [q for q in question_history if isinstance(q, str) and q.strip()]
    if not history_clean:
        return False, 0.0, ""
    try:
        emb_service = EmbeddingService()
        candidate_emb = emb_service.embed_text(candidate)
        history_embs = emb_service.embed_batch(history_clean)
        
        max_sim = -1.0
        matched_q = ""
        for q, q_emb in zip(history_clean, history_embs):
            sim = sum(x * y for x, y in zip(candidate_emb, q_emb))
            if sim > max_sim:
                max_sim = sim
                matched_q = q
        
        if max_sim >= threshold:
            return True, max_sim, matched_q
        return False, max_sim, ""
    except Exception as e:
        logger.warning("Error in embedding semantic similarity check: %s. Falling back to heuristic check.", e)
        # Fallback to Jaccard / SequenceMatcher semantic check
        from difflib import SequenceMatcher
        for h in history_clean:
            w_cand = set(re.sub(r"[^a-z0-9\s]", " ", candidate.lower()).split())
            w_h = set(re.sub(r"[^a-z0-9\s]", " ", h.lower()).split())
            w_cand = {w for w in w_cand if w not in _STOPWORDS and len(w) > 2}
            w_h = {w for w in w_h if w not in _STOPWORDS and len(w) > 2}
            jacc = len(w_cand & w_h) / len(w_cand | w_h) if (w_cand | w_h) else 0.0
            
            ratio = SequenceMatcher(None, _normalize_for_sequence(candidate), _normalize_for_sequence(h)).ratio()
            if jacc >= 0.45 or ratio >= 0.80 or (jacc >= 0.35 and ratio >= 0.70):
                return True, max(jacc, ratio), h
        return False, 0.0, ""


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
    secondary_concept: str = "",
    used_concepts: list[str] | None = None,
) -> tuple[bool, str]:
    """Return (is_valid, reason)."""
    # ── LAYER 1: EXACT DUPLICATE CHECK ───────────────────
    if check_exact_duplicate(question, history):
        logger.debug("REJECTED: reason=EXACT_DUPLICATE, question='%s', concept='%s'", question, concept)
        return False, "EXACT_DUPLICATE"

    # ── LAYER 2: CONCEPT DUPLICATE CHECK ───────────────────
    if used_concepts is not None:
        if check_concept_duplicate(concept, secondary_concept, used_concepts):
            logger.debug("REJECTED: reason=CONCEPT_DUPLICATE, question='%s', concept='%s'", question, concept)
            return False, "CONCEPT_DUPLICATE"

    # ── LAYER 3: SEMANTIC SIMILARITY CHECK ───────────────────
    is_sem_dup, max_sim, matched_q = check_semantic_similarity(question, history, threshold=0.78)
    if is_sem_dup:
        logger.debug("REJECTED: reason=SEMANTIC_DUPLICATE, question='%s', concept='%s' (similar to '%s', score=%.3f)", 
                     question, concept, matched_q, max_sim)
        return False, "SEMANTIC_DUPLICATE"

    if mode != "basic" and question_number > 15:
        return False, "exceeds_15_questions"
    if mode != "basic" and _is_behavioral(question):
        return False, "behavioral_question"
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

    return True, "ok"

FALLBACK_QUESTIONS = {
    "basic": [
        {"question": "What is database normalization, and why is it used in relational databases?", "concept": "database normalization", "topic": "DBMS"},
        {"question": "Explain the difference between an abstract class and an interface in OOP.", "concept": "OOP interface abstract class", "topic": "OOP"},
        {"question": "What is virtual memory, and how does it help a computer run large applications?", "concept": "virtual memory", "topic": "OS"},
        {"question": "How do TCP and UDP differ in terms of reliability and speed?", "concept": "TCP vs UDP", "topic": "Computer_Networks"},
        {"question": "What is the purpose of the software development lifecycle, and what are its key stages?", "concept": "SDLC stages", "topic": "Software_Engineering"},
        {"question": "Explain the difference between a stack and a queue data structure.", "concept": "stack vs queue", "topic": "Linked_Lists_and_Stacks"},
        {"question": "What is the Big O time complexity of searching in a balanced binary search tree?", "concept": "BST search complexity", "topic": "Trees_and_Graphs"},
        {"question": "What is rate limiting, and why is it important for APIs?", "concept": "rate limiting", "topic": "DBMS"},
        {"question": "Explain the concept of inheritance in object-oriented programming.", "concept": "OOP inheritance", "topic": "OOP"},
        {"question": "What is the difference between a process and a thread in an operating system?", "concept": "process vs thread", "topic": "OS"}
    ],
    "frontend": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "How does the virtual DOM work in React to update the UI?", "concept": "virtual DOM", "topic": "React"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "JavaScript"},
        {"question": "What is the difference between local storage and session storage in browsers?", "concept": "browser storage", "topic": "Browser_Rendering_DOM"},
        {"question": "Explain the concept of CSS box model and its components.", "concept": "CSS box model", "topic": "CSS"},
        {"question": "What is semantic HTML, and why is it important for SEO and accessibility?", "concept": "semantic HTML", "topic": "HTML"},
        {"question": "How does hoisting work in JavaScript for variables and functions?", "concept": "JavaScript hoisting", "topic": "JavaScript"},
        {"question": "What are React hooks, and what rules must you follow when using them?", "concept": "React hooks", "topic": "React"},
        {"question": "Explain the difference between event bubbling and event capturing in JS.", "concept": "JS event propagation", "topic": "JavaScript"},
        {"question": "What is the purpose of useEffect hook in React?", "concept": "React useEffect", "topic": "React"}
    ],
    "backend": [
        {"question": "What is the difference between an inner join and a left join in SQL?", "concept": "SQL joins", "topic": "DBMS"},
        {"question": "What is database normalization, and why is it used?", "concept": "database normalization", "topic": "DBMS"},
        {"question": "What is the purpose of caching, and when should you invalidate a cache?", "concept": "caching concepts", "topic": "Caching"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Authentication"},
        {"question": "What is the difference between horizontal and vertical scaling?", "concept": "system design scaling", "topic": "System_Design_Basics"},
        {"question": "What is a transaction in DBMS, and what are the ACID properties?", "concept": "database transactions", "topic": "DBMS"},
        {"question": "What is the purpose of database indexes, and how do they improve query speed?", "concept": "database indexing", "topic": "DBMS"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "DBMS"},
        {"question": "How do REST APIs differ from GraphQL APIs?", "concept": "REST vs GraphQL", "topic": "APIs"},
        {"question": "What is rate limiting, and why is it important for APIs?", "concept": "API rate limiting", "topic": "APIs"}
    ],
    "mern": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "Explain how middleware functions work in Express.js.", "concept": "Express middleware", "topic": "Node_APIs"},
        {"question": "What is the purpose of MongoDB indexes, and how do they affect query performance?", "concept": "MongoDB indexing", "topic": "MongoDB"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Auth_Fullstack"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "MongoDB"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "Node_APIs"},
        {"question": "How do you handle cross-origin resource sharing CORS issues in Express?", "concept": "CORS handling", "topic": "Node_APIs"},
        {"question": "What is the difference between controlled and uncontrolled components in React?", "concept": "React controlled components", "topic": "React"},
        {"question": "How does database indexing work to speed up queries?", "concept": "database indexing", "topic": "MongoDB"},
        {"question": "Explain the difference between authentication and authorization.", "concept": "authentication vs authorization", "topic": "Auth_Fullstack"}
    ],
    "fullstack": [
        {"question": "What is the difference between state and props in React?", "concept": "React state props", "topic": "React"},
        {"question": "Explain how middleware functions work in Express.js.", "concept": "Express middleware", "topic": "Node_APIs"},
        {"question": "What is the purpose of MongoDB indexes, and how do they affect query performance?", "concept": "MongoDB indexing", "topic": "MongoDB"},
        {"question": "How does JWT authentication work to secure an API?", "concept": "JWT auth", "topic": "Auth_Fullstack"},
        {"question": "What is the difference between SQL and NoSQL databases?", "concept": "SQL vs NoSQL", "topic": "MongoDB"},
        {"question": "What is the event loop in JavaScript, and how does it handle asynchronous tasks?", "concept": "JavaScript event loop", "topic": "Node_APIs"},
        {"question": "How do you handle cross-origin resource sharing CORS issues in Express?", "concept": "CORS handling", "topic": "Node_APIs"},
        {"question": "What is the difference between controlled and uncontrolled components in React?", "concept": "React controlled components", "topic": "React"},
        {"question": "How does database indexing work to speed up queries?", "concept": "database indexing", "topic": "MongoDB"},
        {"question": "Explain the difference between authentication and authorization.", "concept": "authentication vs authorization", "topic": "Auth_Fullstack"}
    ],
    "java": [
        {"question": "What is the difference between an interface and an abstract class in Java?", "concept": "OOP interface abstract class", "topic": "OOP"},
        {"question": "Explain how the Java Virtual Machine JVM manages memory using garbage collection.", "concept": "JVM memory management", "topic": "memory_runtime"},
        {"question": "What is the difference between method overloading and method overriding in Java?", "concept": "OOP overloading overriding", "topic": "OOP"},
        {"question": "What are Java collections, and what is the difference between List and Set?", "concept": "Java collections List Set", "topic": "java_language_concepts"},
        {"question": "What is the difference between a process and a thread in Java concurrency?", "concept": "process vs thread", "topic": "memory_runtime"},
        {"question": "Explain the concept of polymorphism in Java with an example.", "concept": "OOP polymorphism", "topic": "OOP"},
        {"question": "What is the purpose of the final keyword in Java for classes and methods?", "concept": "Java final keyword", "topic": "java_language_concepts"},
        {"question": "What is the difference between Checked and Unchecked exceptions in Java?", "concept": "Java exceptions check uncheck", "topic": "java_language_concepts"},
        {"question": "How does Spring Boot framework simplify Java web application development?", "concept": "Spring Boot framework", "topic": "java_language_concepts"},
        {"question": "Explain how threads are synchronized in Java to avoid data races.", "concept": "Java thread synchronization", "topic": "memory_runtime"}
    ],
    "python": [
        {"question": "What is the difference between a list and a tuple in Python?", "concept": "Python list tuple", "topic": "python_language_concepts"},
        {"question": "Explain how decorators work in Python with a brief example.", "concept": "Python decorators", "topic": "python_language_concepts"},
        {"question": "What is a generator in Python, and how does it differ from a regular function?", "concept": "Python generators", "topic": "python_language_concepts"},
        {"question": "What is the difference between deep copy and shallow copy in Python?", "concept": "Python shallow deep copy", "topic": "memory_runtime"},
        {"question": "How does memory management work in Python using reference counting and garbage collection?", "concept": "Python memory management", "topic": "memory_runtime"},
        {"question": "Explain the purpose of the global interpreter lock GIL in Python.", "concept": "Python GIL lock", "topic": "memory_runtime"},
        {"question": "What is the difference between instance, class, and static methods in Python?", "concept": "Python method types", "topic": "OOP"},
        {"question": "What is list comprehension in Python, and when should you use it?", "concept": "Python list comprehension", "topic": "python_language_concepts"},
        {"question": "How do you handle exceptions in Python using try, except, and finally blocks?", "concept": "Python exception handling", "topic": "python_language_concepts"},
        {"question": "What is the difference between a module and a package in Python?", "concept": "Python module package", "topic": "python_language_concepts"}
    ],
    "cybersecurity": [
        {"question": "What is the difference between authentication and authorization?", "concept": "authentication vs authorization", "topic": "auth_sessions"},
        {"question": "Explain the concept of SQL injection and how to prevent it.", "concept": "SQL injection prevention", "topic": "web_security"},
        {"question": "What is the difference between symmetric and asymmetric encryption?", "concept": "symmetric asymmetric encryption", "topic": "encryption_basics"},
        {"question": "What is a cross-site scripting XSS attack, and how do you mitigate it?", "concept": "XSS attack mitigation", "topic": "web_security"},
        {"question": "What is the purpose of a multi-factor authentication system?", "concept": "multi-factor authentication", "topic": "auth_sessions"},
        {"question": "Explain how a man-in-the-middle attack works on a public WiFi network.", "concept": "man-in-the-middle attack", "topic": "network_security"},
        {"question": "What is the difference between a firewall and an intrusion detection system?", "concept": "firewall vs IDS", "topic": "network_security"},
        {"question": "What is the purpose of the HTTPS protocol, and how does TLS secure it?", "concept": "HTTPS TLS security", "topic": "network_security"},
        {"question": "Explain how cross-site request forgery CSRF works and how to prevent it.", "concept": "CSRF attack prevention", "topic": "web_security"},
        {"question": "What is threat modeling, and why is it useful during software design?", "concept": "threat modeling concepts", "topic": "threat_modeling_scenarios"}
    ],
    "data_analyst": [
        {"question": "What is the difference between mean and median, and when is median a better summary?", "concept": "mean vs median", "topic": "statistics"},
        {"question": "What is exploratory data analysis EDA, and what are its main objectives?", "concept": "exploratory data analysis", "topic": "eda"},
        {"question": "What is the difference between an inner join and a left join in SQL?", "concept": "SQL joins", "topic": "sql"},
        {"question": "What is data cleaning, and name two common techniques to handle missing values.", "concept": "data cleaning imputation", "topic": "data_cleaning"},
        {"question": "What is the difference between correlation and causation in data analysis?", "concept": "correlation vs causation", "topic": "statistics"},
        {"question": "How do you use the group by statement in SQL, and what is its purpose?", "concept": "SQL group by", "topic": "sql"},
        {"question": "What is a database index, and how does it speed up SQL queries?", "concept": "database indexing", "topic": "sql"},
        {"question": "Explain the difference between structured and unstructured data.", "concept": "structured vs unstructured", "topic": "eda"},
        {"question": "What is a pivot table, and how does it help in summarizing data?", "concept": "pivot tables Excel", "topic": "pandas_excel"},
        {"question": "What is the difference between outlier detection and noise in data cleaning?", "concept": "outlier vs noise data", "topic": "data_cleaning"}
    ],
    "data_science": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "datascience": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "ml_ai": [
        {"question": "What is data leakage, and how can it happen during model training?", "concept": "data leakage prevention", "topic": "data_leakage"},
        {"question": "What is overfitting, and name two ways to reduce it?", "concept": "overfitting reduction", "topic": "bias_variance"},
        {"question": "Explain the difference between supervised and unsupervised learning.", "concept": "supervised unsupervised learning", "topic": "model_selection"},
        {"question": "What is the bias-variance trade-off in machine learning?", "concept": "bias variance trade-off", "topic": "bias_variance"},
        {"question": "What is the difference between L1 and L2 regularization?", "concept": "L1 L2 regularization", "topic": "model_evaluation"},
        {"question": "How does a random forest classifier differ from a single decision tree?", "concept": "random forest decision tree", "topic": "model_selection"},
        {"question": "What is the purpose of cross-validation in machine learning model evaluation?", "concept": "cross-validation evaluation", "topic": "model_evaluation"},
        {"question": "What are precision and recall, and how do they differ?", "concept": "precision vs recall", "topic": "model_evaluation"},
        {"question": "Explain the difference between classification and regression tasks.", "concept": "classification vs regression", "topic": "model_selection"},
        {"question": "What is the purpose of feature engineering in data preprocessing?", "concept": "feature engineering concepts", "topic": "feature_engineering"}
    ],
    "devops": [
        {"question": "What is the difference between CI and CD?", "concept": "CI vs CD", "topic": "ci_cd"},
        {"question": "What is the difference between horizontal scaling and vertical scaling?", "concept": "horizontal vertical scaling", "topic": "scaling_reliability"},
        {"question": "Explain the concept of infrastructure as code IaC.", "concept": "infrastructure as code", "topic": "infra_as_code"},
        {"question": "What is docker, and how does it differ from a virtual machine?", "concept": "docker containerization", "topic": "docker"},
        {"question": "What is kubernetes, and what is the role of a pod?", "concept": "kubernetes pods", "topic": "kubernetes"},
        {"question": "Explain the difference between rolling deployment and blue-green deployment strategies.", "concept": "deployment strategies", "topic": "deployment_strategies"},
        {"question": "What is the purpose of load balancing in cloud architecture?", "concept": "load balancer systems", "topic": "scaling_reliability"},
        {"question": "What is the difference between cloud public, private, and hybrid deployment models?", "concept": "cloud deployment models", "topic": "cloud_basics"},
        {"question": "What is the purpose of monitoring and logging in devops pipelines?", "concept": "monitoring logging DevOps", "topic": "monitoring_logging"},
        {"question": "Explain how IAM policies are used to secure cloud resources.", "concept": "cloud IAM security", "topic": "cloud_basics"}
    ],
    "cloud": [
        {"question": "What is the difference between CI and CD?", "concept": "CI vs CD", "topic": "ci_cd"},
        {"question": "What is the difference between horizontal scaling and vertical scaling?", "concept": "horizontal vertical scaling", "topic": "scaling_reliability"},
        {"question": "Explain the concept of infrastructure as code IaC.", "concept": "infrastructure as code", "topic": "infra_as_code"},
        {"question": "What is docker, and how does it differ from a virtual machine?", "concept": "docker containerization", "topic": "docker"},
        {"question": "What is kubernetes, and what is the role of a pod?", "concept": "kubernetes pods", "topic": "kubernetes"},
        {"question": "Explain the difference between rolling deployment and blue-green deployment strategies.", "concept": "deployment strategies", "topic": "deployment_strategies"},
        {"question": "What is the purpose of load balancing in cloud architecture?", "concept": "load balancer systems", "topic": "scaling_reliability"},
        {"question": "What is the difference between cloud public, private, and hybrid deployment models?", "concept": "cloud deployment models", "topic": "cloud_basics"},
        {"question": "What is the purpose of monitoring and logging in devops pipelines?", "concept": "monitoring logging DevOps", "topic": "monitoring_logging"},
        {"question": "Explain how IAM policies are used to secure cloud resources.", "concept": "cloud IAM security", "topic": "cloud_basics"}
    ]
}


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

    max_attempts = 10
    attempt = 0
    target_topic = current_topic
    
    # Track which topics we have attempted during this generation call to avoid loops
    attempted_topics = {target_topic}
    last_error = ""

    while True:
        try:
            # Format target topic in prompt dynamically
            if phase == "resume":
                current_prompt = RESUME_PHASE_QUESTION_PROMPT.format(
                    rag_chunks=rag_chunks,
                    skill_summary=skill_summary or "Not listed",
                    project_summary=resume_project_summary or "No summary available",
                    topic=target_topic
                )
            elif mode == "basic":
                current_prompt = BASIC_PRACTICE_QUESTION_GENERATION_PROMPT.format(
                    mode=mode,
                    question_number=question_number,
                    last_answer=answer_quality or "None",
                    used_concepts=json.dumps(used_concepts[-20:]) if used_concepts else "[]",
                )
            else:
                current_prompt = STRICT_QUESTION_GENERATION_PROMPT.format(
                    mode=mode,
                    question_number=question_number,
                    used_concepts=json.dumps(used_concepts[-20:]) if used_concepts else "[]",
                    used_topics=json.dumps([str(x) for x in topic_history[-10:]]) if topic_history else "[]",
                    last_answer=answer_quality or "None"
                )
                
                # Append role filters and subtopics
                project_name = _extract_first_project_name(resume_project_summary) if question_number == 1 else ""
                if resume_has_projects and question_number == 1 and project_name:
                    current_prompt += "\n\nSTRICT RULES (JOB-SPECIFIC):"
                    current_prompt += "\n- Q1 MUST be project-based and role-relevant."
                    current_prompt += f"\n- Use the project name '{project_name}' in the question."
                    current_prompt += "\n- Ask about a specific implementation decision, challenge, or trade-off from that project."
                    current_prompt += "\n- Do NOT ask generic 'overview' questions unless you reference a concrete technical detail."
                else:
                    current_prompt += "\n\nSTRICT RULES (JOB-SPECIFIC):"
                    if resume_has_projects and question_number == 1 and not project_name:
                        current_prompt += "\n- Resume projects exist, but no valid project title is available to reference."
                        current_prompt += "\n- DO NOT mention resume projects or ask project-based questions."
                        current_prompt += "\n- Ask a skill-based question strictly aligned to the selected role."
                    elif not resume_has_projects:
                        current_prompt += "\n- No relevant resume projects exist for this mode."
                        current_prompt += "\n- DO NOT mention resume projects or ask project-based questions."
                        current_prompt += "\n- Ask a skill-based question strictly aligned to the selected role."

                if mode == "data_analyst":
                    current_prompt += "\n\nROLE FILTER: Data Analyst"
                    current_prompt += "\n- ONLY ask about data cleaning, SQL, EDA, visualization, statistics, pandas/Excel, or business insights."
                    current_prompt += "\n- DO NOT ask about APIs, caching, system design, or backend architecture."
                elif mode == "ml_ai":
                    current_prompt += "\n\nROLE FILTER: ML/AI"
                    current_prompt += "\n- ONLY ask about preprocessing, models, evaluation, overfitting, and tuning."
                    current_prompt += "\n- DO NOT ask about DBMS, OS, APIs, or backend systems."
                elif mode == "cloud":
                    current_prompt += "\n\nROLE FILTER: Cloud"
                    current_prompt += "\n- ONLY ask about deployment, IAM, networking, monitoring, reliability, and cost optimization."
                    current_prompt += "\n- DO NOT ask frontend or ML theory questions."
                elif mode == "mern":
                    current_prompt += "\n\nROLE FILTER: MERN"
                    current_prompt += "\n- Focus on React, Node APIs, MongoDB, authentication, and fullstack data flow."
                    current_prompt += "\n- Avoid OS theory and unrelated domains."

            if unused_subtopics is not None:
                # Find an unused subtopic that isn't the exhausted target_topic
                valid_unused = [t for t in unused_subtopics if t == target_topic or t not in attempted_topics]
                current_prompt += f"\n- You MUST pick subtopic ONLY from this unused list: {', '.join(valid_unused) if valid_unused else 'NONE'}"

            current_prompt += "\n\nOUTPUT JSON MUST INCLUDE: question, concept, secondary_concept, difficulty. Use natural language; avoid robotic phrases like 'idea' or 'concept' in the question itself."

            response = await llm.ainvoke(current_prompt)
            content: str = getattr(response, "content", str(response))
            result = parse_json_response(content)

            question = (result.get("question", "")).strip()
            InterviewTracer.log_pipeline_step(6, "LLM response", question)

            subtopic_raw = result.get("subtopic") or result.get("topic")
            concept_raw = result.get("concept")
            secondary_concept_raw = result.get("secondary_concept") or ""
            
            subtopic = str(subtopic_raw or "").strip()
            concept = str(concept_raw or "").strip()
            secondary_concept = str(secondary_concept_raw or "").strip()

            if not subtopic and unused_subtopics:
                subtopic = target_topic
            if not concept:
                concept = f"{target_topic}_q{question_number}"

            # Validate generated question
            is_valid, reason = _validate_question(
                question,
                mode,
                question_number,
                question_history,
                subtopic=subtopic,
                unused_subtopics=unused_subtopics,
                concept=concept,
                secondary_concept=secondary_concept,
                used_concepts=used_concepts,
            )

            if is_valid:
                # Apply language sanitization
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

                # Word count truncation safety
                if len(question.split()) > MAX_QUESTION_WORDS and "." in question:
                    question = question.split(".")[0].strip()

                # Final pass sanitization
                question = _sanitize_question_text(
                    question,
                    mode=mode,
                    resume_has_projects=bool(resume_has_projects),
                    resume_project_summary=resume_project_summary,
                )

                # Log final accepted question
                logger.info("ACCEPTED: question='%s', concept='%s', status=accepted", question, concept)
                
                return {
                    "question": question,
                    "topic": result.get("topic") or target_topic,
                    "subtopic": subtopic,
                    "concept": concept,
                    "secondary_concept": secondary_concept,
                    "phase": result.get("phase", phase_bucket),
                    "type": result.get("type", strict_intent),
                    "difficulty": strict_difficulty,
                    "intent": strict_intent,
                }
            else:
                logger.warning(
                    "QuestionGeneratorAgent: validation failed (attempt %d/10 topic=%s reason=%s): %s",
                    attempt + 1, target_topic, reason, question,
                )
                attempt += 1
                if attempt >= max_attempts:
                    # Switch target topic/concept from unused pool
                    if unused_subtopics:
                        alt_topics = [t for t in unused_subtopics if t not in attempted_topics]
                        if alt_topics:
                            target_topic = alt_topics[0]
                            attempted_topics.add(target_topic)
                            attempt = 0
                            logger.info("Switched to alternative subtopic: '%s'", target_topic)
                            continue
                    
                    # If we exhausted all options, break to fallback pool
                    break

        except Exception as exc:
            logger.error("QuestionGeneratorAgent LLM error: %s", exc)
            last_error = str(exc)
            attempt += 1
            if attempt >= max_attempts:
                if unused_subtopics:
                    alt_topics = [t for t in unused_subtopics if t not in attempted_topics]
                    if alt_topics:
                        target_topic = alt_topics[0]
                        attempted_topics.add(target_topic)
                        attempt = 0
                        logger.info("Switched to alternative subtopic on error: '%s'", target_topic)
                        continue
                break

    # ── FALLBACK POOL MECHANISM ──────────────────────────────────────────
    logger.warning("All LLM generation attempts failed or returned duplicates. Selecting from FALLBACK_POOL.")
    
    # Retrieve fallbacks for this mode
    fallback_list = FALLBACK_QUESTIONS.get(mode, FALLBACK_QUESTIONS["basic"])
    for f_item in fallback_list:
        fq = f_item["question"]
        fc = f_item["concept"]
        ft = f_item["topic"]
        
        # Check exact duplicate
        if check_exact_duplicate(fq, question_history):
            logger.debug("FALLBACK REJECTED: reason=EXACT_DUPLICATE, question='%s', concept='%s'", fq, fc)
            continue
            
        # Check concept duplicate
        if used_concepts is not None and check_concept_duplicate(fc, "", used_concepts):
            logger.debug("FALLBACK REJECTED: reason=CONCEPT_DUPLICATE, question='%s', concept='%s'", fq, fc)
            continue
            
        # Check semantic duplicate
        is_sem_dup, max_sim, matched_q = check_semantic_similarity(fq, question_history, threshold=0.78)
        if is_sem_dup:
            logger.debug("FALLBACK REJECTED: reason=SEMANTIC_DUPLICATE, question='%s', concept='%s' (similar to '%s', score=%.3f)", 
                         fq, fc, matched_q, max_sim)
            continue
            
        # Found a valid fallback question!
        logger.info("ACCEPTED (FALLBACK): question='%s', concept='%s', status=accepted", fq, fc)
        return {
            "question": fq,
            "topic": ft,
            "subtopic": ft,
            "concept": fc,
            "secondary_concept": "",
            "phase": phase_bucket,
            "type": strict_intent,
            "difficulty": strict_difficulty,
            "intent": strict_intent,
        }
        
    # Absolute last-resort fallback if even all fallback pool items are somehow duplicated
    default_q = "Explain a challenging technical decision you had to make and its outcome."
    default_c = "challenging decision"
    logger.info("ACCEPTED (LAST RESORT): question='%s', concept='%s', status=accepted", default_q, default_c)
    return {
        "question": default_q,
        "topic": "general",
        "subtopic": "general",
        "concept": default_c,
        "secondary_concept": "",
        "phase": phase_bucket,
        "type": strict_intent,
        "difficulty": strict_difficulty,
        "intent": strict_intent,
    }
