"""
Academic Agent LLM Provider.
Returns a callable ``invoke(messages) -> obj with .content`` backed by the
shared chat model in ``app.core.llm`` (NVIDIA or Groq).
"""

from app.core.llm import get_llm as _get_chat_model


def get_llm():
    model = _get_chat_model()

    def invoke(messages):
        return model.invoke(messages)

    return invoke
