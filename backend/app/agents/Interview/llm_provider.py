"""
LLM provider factory for the interview agent.
Delegates to the shared provider in ``app.core.llm`` (NVIDIA or Groq).
"""

from app.core.llm import get_llm  # noqa: F401
