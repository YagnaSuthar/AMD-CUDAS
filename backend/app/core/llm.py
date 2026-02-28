"""
LLM provider factory.
Creates a LangChain ChatGroq instance from application settings.
"""

from langchain_groq import ChatGroq

from app.core.config import settings


def get_llm() -> ChatGroq:
    """
    Build and return a Groq LLM instance configured from env vars.
    """
    return ChatGroq(
        model=settings.GROQ_MODEL_NAME,
        api_key=settings.GROQ_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        max_retries=6,  # Exponential backoff: ~1s, 2s, 4s, 8s, 16s, 32s ≈ 63s total
    )
