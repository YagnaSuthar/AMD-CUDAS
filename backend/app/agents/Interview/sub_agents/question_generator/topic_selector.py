"""
Deterministic topic/concept selection for project-based interview questions.

The LLM does NOT choose what to ask — it only converts a pre-selected
(topic, concept) pair into a natural interview question.
"""

from __future__ import annotations

import re
import random
from typing import Any

# ── Concept Pools ────────────────────────────────────────────────────────

RESUME_CONCEPTS = [
    "Architecture",
    "Authentication",
    "APIs",
    "Database",
    "Deployment",
    "Security",
    "Scalability",
    "Performance",
    "AI Workflow",
    "Agent Communication",
    "LangGraph",
    "Prompt Engineering",
    "Challenges",
    "Trade-offs",
    "Future Improvements"
]

CORE_CONCEPTS = {
    "DBMS": ["ACID Properties", "Normalization", "Indexing", "Joins", "Transactions", "NoSQL vs SQL"],
    "OS": ["Process vs Thread", "Deadlocks", "Virtual Memory", "Scheduling", "Concurrency"],
    "Computer_Networks": ["OSI Model", "TCP vs UDP", "DNS", "HTTP/HTTPS", "Load Balancing"],
    "OOP": ["Inheritance", "Polymorphism", "Encapsulation", "Abstraction", "Design Patterns"],
    "Software_Engineering": ["Agile", "CI/CD", "Testing", "Version Control", "Microservices"],
    "System_Design_Basics": ["Client-Server", "API Design", "Caching", "Message Queues", "CAP Theorem"],
    "Behavioral": ["Conflict Resolution", "Time Management", "Leadership", "Handling Failure", "Teamwork"],
    "Scenario": ["System Outage", "Tight Deadline", "Disagreement with Manager", "Scaling a feature"]
}

ROLE_CONCEPTS = {
    "frontend": {
        "easy": ["DOM Manipulation", "CSS Flexbox/Grid", "HTML Semantics", "State Management Basics"],
        "medium": ["Virtual DOM", "React Hooks", "Component Lifecycle", "Performance Optimization", "Responsive Design"],
        "hard": ["Server-Side Rendering", "WebSockets", "Micro-frontends", "Advanced State Management", "Web Workers"]
    },
    "backend": {
        "easy": ["REST APIs", "CRUD Operations", "Basic SQL", "Authentication Basics"],
        "medium": ["Caching Strategies", "Connection Pooling", "Message Brokers", "JWT", "Middleware"],
        "hard": ["Distributed Systems", "Database Sharding", "Event-Driven Architecture", "gRPC", "Consensus Algorithms"]
    },
    "fullstack": {
        "easy": ["Client-Server Architecture", "REST APIs", "DOM Basics", "Basic SQL"],
        "medium": ["State Management", "Authentication Flow", "API Integration", "Database Design"],
        "hard": ["Microservices", "System Design", "Advanced Security", "Performance Profiling"]
    },
    "java": {
        "easy": ["JVM Basics", "OOP in Java", "Collections Framework Basics", "Exceptions"],
        "medium": ["Multithreading", "Stream API", "Spring Boot Basics", "Generics"],
        "hard": ["Garbage Collection Tuning", "Concurrency Utilities", "Spring Security", "Microservices with Spring"]
    },
    "python": {
        "easy": ["Data Types", "Functions", "List Comprehensions", "Basic OOP"],
        "medium": ["Decorators", "Generators", "Context Managers", "Flask/Django Basics"],
        "hard": ["GIL", "Asyncio", "Metaclasses", "Advanced Performance Optimization"]
    },
    "cybersecurity": {
        "easy": ["CIA Triad", "Phishing", "Basic Encryption", "Firewalls"],
        "medium": ["OWASP Top 10", "Symmetric vs Asymmetric Encryption", "VPNs", "Intrusion Detection"],
        "hard": ["Zero Trust Architecture", "Penetration Testing Strategies", "Advanced Cryptography", "Malware Analysis"]
    }
}

ROLE_BEHAVIORAL_CONCEPTS = {
    "frontend": ["Conflict while shipping UI", "Cross-browser issues", "Designer vs Developer conflict", "Accessibility challenges"],
    "backend": ["Production outage", "Database migration failure", "API contract breaking", "Scaling bottlenecks"],
    "mern": ["Production outage", "Database migration failure", "API contract breaking", "Scaling bottlenecks"],
    "fullstack": ["Production outage", "Database migration failure", "API contract breaking", "Scaling bottlenecks"],
    "java": ["Production outage", "Database migration failure", "API contract breaking", "Scaling bottlenecks"],
    "python": ["Production outage", "Database migration failure", "API contract breaking", "Scaling bottlenecks"],
    "data_analyst": ["Handling dirty data sources", "Explaining statistics to business stakeholders", "Conflicting report definitions", "Query performance bottlenecks"],
    "data_science": ["Overfitting in production", "Handling model bias", "Data privacy conflict", "Concept drift in deployed model"],
    "ml_ai": ["LLM hallucination in production", "GPU memory optimization conflict", "Model training latency", "RAG performance tuning"],
    "ai": ["LLM hallucination in production", "GPU memory optimization conflict", "Model training latency", "RAG performance tuning"],
    "cloud": ["Deployment failure", "Cost overrun", "Downtime during peak", "Cloud provider outage"],
    "devops": ["CI/CD pipeline broken", "Secret leak", "Reverting a bad deploy", "Infrastructure as code failure"],
    "cybersecurity": ["Security breach response", "Zero-day vulnerability", "Pushback on security policies", "Incident post-mortem"]
}

GENERAL_BEHAVIORAL_CONCEPTS = [
    "Leadership", "Ownership", "Teamwork", "Conflict", "Communication",
    "Deadlines", "Failure", "Learning", "Mentoring", "Decision Making",
    "Time Management", "Stakeholder Management", "Prioritization", "Product Thinking"
]

CONCEPT_RAG_KEYWORDS: dict[str, list[str]] = {
    "Project Overview": ["project", "overview", "built", "developed", "application"],
    "Architecture": ["architecture", "components", "system design", "modules", "microservice"],
    "Tech Decisions": ["why", "motivation", "choice", "decision", "tech stack"],
    "Scalability": ["scale", "scalability", "load", "users", "growth"],
    "Future Improvements": ["future", "improve", "next", "roadmap", "enhancement"],
    "Deployment": ["deploy", "docker", "kubernetes", "aws", "cloud", "ci/cd"],
    "Authentication": ["auth", "jwt", "login", "oauth", "session"],
    "Performance": ["performance", "optimize", "latency", "cache", "speed"],
    "Database": ["database", "postgres", "mysql", "mongodb", "redis", "sql", "schema"],
    "Security": ["security", "vulnerability", "encryption", "protection"]
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


def select_concept(
    phase: str,
    topic: str,
    role: str,
    difficulty: str,
    used_concepts: list[str] | None = None
) -> str:
    """
    Dynamically pick an unused concept based on metadata.
    """
    used_concepts = used_concepts or []
    role_norm = (role or "").strip().lower()
    
    # For role-based interviews (where role != "basic"), we bypass the generic
    # core concepts and role concepts lookup for Q2-Q14, and instead return the
    # deterministic topic directly as the concept.
    # This aligns with the deterministic roadmap where the planner controls topic & concept.
    if role_norm != "basic":
        if phase == "resume":
            available = [c for c in RESUME_CONCEPTS if not concept_is_used(c, used_concepts)]
            if available:
                return random.choice(available)
            return random.choice(RESUME_CONCEPTS)
            
        if phase == "behavioral" or topic.lower() == "behavioral":
            pool = ROLE_BEHAVIORAL_CONCEPTS.get(role_norm, GENERAL_BEHAVIORAL_CONCEPTS)
            available = [c for c in pool if not concept_is_used(c, used_concepts)]
            if not available and pool is not GENERAL_BEHAVIORAL_CONCEPTS:
                available = [c for c in GENERAL_BEHAVIORAL_CONCEPTS if not concept_is_used(c, used_concepts)]
            if available:
                return random.choice(available)
            return random.choice(GENERAL_BEHAVIORAL_CONCEPTS)
            
        if topic == "Scenario":
            scenarios = {
                "mern": "Debugging a slow MERN application after deployment",
                "frontend": "Resolving performance bottlenecks in a complex React/JavaScript application",
                "backend": "Handling database connection spikes and API latency issues under high load",
                "python": "Debugging a memory leak or CPU spike in a production FastAPI or Django application",
                "java": "Analyzing and resolving thread deadlocks or JVM OutOfMemoryError in production",
                "data_analyst": "Handling contradictory data sources or massive clean-up challenges before reporting",
                "data_science": "Dealing with concept drift or high variance in a deployed model in production",
                "ml_ai": "Optimizing latency for LLM inference or handling vector database scaling issues",
                "devops": "Recovering from a failing CI/CD deployment or secret leak in production",
                "cloud": "Diagnosing cloud service outage or unexpected monthly cost overrun",
                "cybersecurity": "Responding to a suspected security breach or zero-day vulnerability in the system"
            }
            return scenarios.get(role_norm, "Technical Scenario Analysis")
            
        # Check if topic is in the roadmap for this role
        from app.agents.Interview.planner.interview_planner import ROADMAPS
        role_roadmap = ROADMAPS.get(role_norm, [])
        if topic in role_roadmap:
            return topic

    # 1. Resume Phase (Basic Practice)
    if phase == "resume":
        available = [c for c in RESUME_CONCEPTS if not concept_is_used(c, used_concepts)]
        if available:
            return random.choice(available)
        return random.choice(RESUME_CONCEPTS) # Fallback if all used

    # 1b. Behavioral Phase (Basic Practice)
    if phase == "behavioral" or topic.lower() == "behavioral":
        pool = ROLE_BEHAVIORAL_CONCEPTS.get(role_norm, GENERAL_BEHAVIORAL_CONCEPTS)
        available = [c for c in pool if not concept_is_used(c, used_concepts)]
        if not available and pool is not GENERAL_BEHAVIORAL_CONCEPTS:
            available = [c for c in GENERAL_BEHAVIORAL_CONCEPTS if not concept_is_used(c, used_concepts)]
        if available:
            return random.choice(available)
        return random.choice(GENERAL_BEHAVIORAL_CONCEPTS)

    # 2. Core/Topic based (if topic exists in CORE_CONCEPTS - Basic Practice)
    if topic in CORE_CONCEPTS:
        available = [c for c in CORE_CONCEPTS[topic] if not concept_is_used(c, used_concepts)]
        if available:
            return random.choice(available)
    
    # 3. Role based (if topic maps to role concepts or just general role phase - Basic Practice)
    if role_norm in ROLE_CONCEPTS:
        diff_norm = difficulty.lower()
        if diff_norm not in ["easy", "medium", "hard"]:
            diff_norm = "medium"
        
        pool = ROLE_CONCEPTS[role_norm].get(diff_norm, [])
        available = [c for c in pool if not concept_is_used(c, used_concepts)]
        if available:
            return random.choice(available)
            
        # Fallback to any difficulty for this role
        all_role_concepts = []
        for d in ["easy", "medium", "hard"]:
            all_role_concepts.extend(ROLE_CONCEPTS[role_norm].get(d, []))
        available = [c for c in all_role_concepts if not concept_is_used(c, used_concepts)]
        if available:
            return random.choice(available)
            
    # 4. Fallback for any unknown topic (Basic Practice)
    if topic and topic.strip() and topic.lower() != "general":
        # Just use the topic itself as the concept if nothing else matches
        return topic.replace("_", " ").title()

    return "General Technical Concepts"

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

