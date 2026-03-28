"""Debug: exact raw response from gemini-2.5-flash for a complex prompt."""
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

from app.agents.Interview.llm_provider import get_llm
from app.agents.Interview.prompts import PROFILE_ANALYSIS_PROMPT

async def test():
    llm = get_llm()
    
    prompt = PROFILE_ANALYSIS_PROMPT.format(
        resume_text="Python developer with 3 years experience in FastAPI and React.",
        portfolio_text="github.com/test - 10 repos",
        experience_years=3,
        skills="Python (advanced), FastAPI (advanced), React (intermediate)",
    )
    
    print("=== Calling LLM... ===")
    response = await llm.ainvoke(prompt)
    
    print(f"\n=== Response type: {type(response)} ===")
    print(f"=== dir(response): {[a for a in dir(response) if not a.startswith('_')]} ===")
    
    content = getattr(response, "content", None)
    print(f"\n=== .content ({type(content).__name__}, {len(str(content))} chars) ===")
    print(repr(content))
    
    # Check for additional_kwargs which may contain thinking
    additional = getattr(response, "additional_kwargs", {})
    print(f"\n=== .additional_kwargs ===")
    for k, v in additional.items():
        val_str = str(v)[:200]
        print(f"  {k}: {val_str}")
    
    # Check response_metadata
    meta = getattr(response, "response_metadata", {})
    print(f"\n=== .response_metadata keys: {list(meta.keys())} ===")

asyncio.run(test())
