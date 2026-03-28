# """
# Academic Agent LLM Provider
# Independent from Interview agent.
# Uses official Google Generative AI SDK.
# """

# import google.generativeai as genai
# from app.core.config import settings


# def get_llm():
#     """
#     Returns a callable function compatible with orchestrator.
#     """

#     genai.configure(api_key=settings.GEMINI_API_KEY)

#     model = genai.GenerativeModel("gemini-1.5-flash")

#     def invoke(messages):
#         combined_prompt = ""

#         for msg in messages:
#             if isinstance(msg, dict):
#                 combined_prompt += msg.get("content", "") + "\n"
#             else:
#                 combined_prompt += getattr(msg, "content", "") + "\n"

#         response = model.generate_content(combined_prompt)

#         class Result:
#             content = response.text

#         return Result()

#     return invoke


"""
Academic Agent LLM Provider
Auto-detects supported Gemini model.
"""

import google.generativeai as genai
from app.core.config import settings


def get_llm():
    genai.configure(api_key=settings.GEMINI_API_KEY)

    # 🔍 Find first available generateContent-capable model
    models = genai.list_models()
    selected_model = None

    for m in models:
        if "generateContent" in m.supported_generation_methods:
            selected_model = m.name
            break

    if not selected_model:
        raise RuntimeError("No supported Gemini model found for this API key.")

    model = genai.GenerativeModel(selected_model)

    def invoke(messages):
        combined_prompt = ""

        for msg in messages:
            if isinstance(msg, dict):
                combined_prompt += msg.get("content", "") + "\n"
            else:
                combined_prompt += getattr(msg, "content", "") + "\n"

        response = model.generate_content(combined_prompt)

        class Result:
            content = response.text

        return Result()

    return invoke