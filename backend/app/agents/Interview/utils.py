"""
Shared utilities for Interview sub-agents.
"""

import json
import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def parse_json_response(content: str) -> Dict[str, Any]:
    """
    Parse a JSON response from the LLM, handling:
    - Markdown code fences (```json ... ```)
    - Thinking tokens mixed with JSON (gemini-2.5-flash)
    - Extra text before/after the JSON object
    """
    text = content.strip()
    logger.debug("Raw LLM response (%d chars): %.200s...", len(text), text)
    
    # 1. Remove markdown code fences: ```json ... ``` or ``` ... ```
    if "```" in text:
        # Extract content between first ``` and last ```
        match = re.search(r"```(?:\w*)\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    
    # 2. Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 3. Find the first { ... } block in the text (handles thinking tokens)
    brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # 4. Last resort: try to find any JSON-like content
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    
    # If nothing works, raise with the original content for debugging
    with open("debug_failed_json.txt", "w", encoding="utf-8") as f:
        f.write(content)
        
    raise json.JSONDecodeError(
        f"Could not extract JSON from LLM response. Saved to debug_failed_json.txt. Preview: {text[:200]}",
        text, 0
    )

