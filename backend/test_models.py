"""Test which Gemini models are available and have quota."""
import os
os.environ["GEMINI_API_KEY"] = ""  # Will be loaded from .env

from app.core.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

MODELS_TO_TRY = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
]

def test_model(model_name: str) -> bool:
    print(f"  Testing {model_name}...", end=" ", flush=True)
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            max_output_tokens=50,
            convert_system_message_to_human=True,
            max_retries=1,
        )
        resp = llm.invoke([HumanMessage(content="Say hello")])
        print(f"✓ OK — {resp.content[:40]}")
        return True
    except Exception as e:
        err = str(e)[:80]
        print(f"✗ FAIL — {err}")
        return False

if __name__ == "__main__":
    print(f"API Key: ...{settings.GEMINI_API_KEY[-8:]}")
    print()
    for m in MODELS_TO_TRY:
        if test_model(m):
            print(f"\n>>> Use this in .env: GEMINI_MODEL_NAME={m}")
            break
    else:
        print("\nAll models failed. Your project quota may be fully exhausted.")
        print("Try creating a NEW Google Cloud project at https://aistudio.google.com/")
