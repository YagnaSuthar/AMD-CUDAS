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
