from __future__ import annotations

from enum import Enum


class InterviewMode(str, Enum):
    BASIC = "basic"
    FRONTEND = "frontend"
    BACKEND = "backend"
    MERN = "mern"
    JAVA = "java"
    PYTHON = "python"
    DATA_ANALYST = "data_analyst"
    DATA_SCIENCE = "data_science"
    ML_AI = "ml_ai"
    DEVOPS = "devops"
    CLOUD = "cloud"
    CYBERSECURITY = "cybersecurity"


def normalize_interview_mode(mode: str | None) -> str:
    m = (mode or "").strip().lower()
    if not m:
        raise ValueError("Mode is missing")

    allowed = {x.value for x in InterviewMode}
    if m not in allowed:
        raise ValueError(f"Invalid mode: {m}")

    return m


def get_role_for_mode(mode: str) -> str:
    m = (mode or "").strip().lower()
    mapping = {
        "basic": "General Placement Preparation",
        "frontend": "Frontend Developer",
        "backend": "Backend Developer",
        "mern": "MERN Stack Developer",
        "java": "Java Developer",
        "python": "Python Developer",
        "data_analyst": "Data Analyst",
        "data_science": "Data Science",
        "ml_ai": "ML / AI Engineer",
        "devops": "DevOps Engineer",
        "cloud": "Cloud Engineer",
        "cybersecurity": "Cybersecurity",
    }
    return mapping.get(m, "General Placement Preparation")


def get_interview_type_for_mode(mode: str) -> str:
    m = (mode or "").strip().lower()
    mapping = {
        "basic": "Basic Practice Interview",
        "frontend": "Frontend Interview",
        "backend": "Backend Interview",
        "mern": "MERN Stack Interview",
        "java": "Java Interview",
        "python": "Python Interview",
        "data_analyst": "Data Analyst Interview",
        "data_science": "Data Science Interview",
        "ml_ai": "ML/AI Interview",
        "devops": "DevOps Interview",
        "cloud": "Cloud Interview",
        "cybersecurity": "Cybersecurity Interview",
    }
    return mapping.get(m, "Role-Based Interview")

