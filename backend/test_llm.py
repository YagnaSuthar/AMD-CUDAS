from app.agents.Interview.llm_provider import get_llm
from langchain_core.messages import HumanMessage

def test_llm():
    print("Testing LLM connection...")
    try:
        llm = get_llm()
        resp = llm.invoke([HumanMessage(content="Say 'Hello World'")])
        print(f"  [SUCCESS] Response: {resp.content}")
    except Exception as e:
        print(f"  [FAILED] {e}")

if __name__ == "__main__":
    test_llm()
