"""
LLM provider factory.
Creates a LangChain ChatGoogleGenerativeAI instance from application settings.
"""

# from langchain_google_genai import ChatGoogleGenerativeAI
try:
    from langchain_groq import ChatGroq
except ModuleNotFoundError:  # pragma: no cover
    ChatGroq = None

from app.core.config import settings


# def get_llm() -> ChatGoogleGenerativeAI:
def get_llm():
    """
    Build and return a Gemini LLM instance configured from env vars.
    """
    if ChatGroq is None:
        raise RuntimeError(
            "Missing optional dependency 'langchain-groq'. "
            "Install it (pip install langchain-groq) to enable Groq-backed AI interviews."
        )
    # return ChatGoogleGenerativeAI(
    #     model=settings.GEMINI_MODEL_NAME,
    #     google_api_key=settings.GEMINI_API_KEY,
    #     temperature=settings.LLM_TEMPERATURE,
    #     max_output_tokens=settings.LLM_MAX_TOKENS,
    #     convert_system_message_to_human=True,
    #     max_retries=6, # Exponential backoff: ~1s, 2s, 4s, 8s, 16s, 32s ≈ 63s total
    # )
    return ChatGroq(
        model=settings.GROQ_MODEL_NAME,
        api_key=settings.GROQ_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        max_retries=6, # Exponential backoff
    )
