"""
LLM provider factory.
Returns a LangChain chat model — NVIDIA NIM (OpenAI-compatible) or Groq —
based on application settings.
"""

try:
    from langchain_groq import ChatGroq
except ModuleNotFoundError:  # pragma: no cover
    ChatGroq = None

from app.core.config import settings


def _provider() -> str:
    provider = settings.LLM_PROVIDER.strip().lower()
    if provider:
        return provider
    return "nvidia" if settings.NVIDIA_API_KEY else "groq"


def get_llm():
    """
    Build and return the configured chat model.
    """
    if _provider() == "nvidia":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            model=settings.NVIDIA_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT_SECONDS,
            max_retries=3,
            # Reasoning output goes to a separate field; the app needs plain answers
            extra_body={"chat_template_kwargs": {"enable_thinking": settings.NVIDIA_ENABLE_THINKING}},
        )

    if ChatGroq is None:
        raise RuntimeError(
            "Missing optional dependency 'langchain-groq'. "
            "Install it (pip install langchain-groq) to enable Groq-backed AI interviews."
        )
    return ChatGroq(
        model=settings.GROQ_MODEL_NAME,
        api_key=settings.GROQ_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        max_retries=6,  # Exponential backoff: ~1s, 2s, 4s, 8s, 16s, 32s ≈ 63s total
    )
