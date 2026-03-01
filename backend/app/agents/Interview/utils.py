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
    - Python function definitions (common LLM error)
    """
    text = content.strip()
    logger.debug("Raw LLM response (%d chars): %.200s...", len(text), text)
    
    # 1. Remove Python function definitions if LLM returns code instead of JSON
    if text.startswith("def ") or "def update_interview_assessment" in text:
        logger.warning("LLM returned Python function instead of JSON. Attempting to extract JSON...")
        # Try to find JSON-like patterns in the function body
        json_patterns = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        for pattern in json_patterns:
            try:
                return json.loads(pattern)
            except json.JSONDecodeError:
                continue
    
    # 2. Remove markdown code fences: ```json ... ``` or ``` ... ```
    if "```" in text:
        # Extract content between first ``` and last ```
        match = re.search(r"```(?:\w*)\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
    
    # 3. Remove any leading/trailing text that's not JSON
    # Find the first { and last }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]
    
    # 4. Try direct parse first
    try:
        result = json.loads(text)
        logger.debug("Successfully parsed JSON: %s", result)
        return result
    except json.JSONDecodeError as e:
        logger.debug("Direct JSON parse failed: %s", e)
    
    # 5. Find the first { ... } block in the text (handles thinking tokens)
    brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            logger.debug("Successfully parsed JSON from brace match: %s", result)
            return result
        except json.JSONDecodeError:
            pass
    
    # 6. Last resort: try to find any JSON-like content line by line
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                result = json.loads(line)
                logger.debug("Successfully parsed JSON from line: %s", result)
                return result
            except json.JSONDecodeError:
                continue
    
    # 7. If nothing works, save for debugging and raise detailed error
    debug_file = "debug_failed_json.txt"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(f"Raw LLM Response:\n{content}\n\n")
        f.write(f"Processed Text:\n{text}\n\n")
        f.write(f"Response Length: {len(content)} characters\n")
        f.write(f"Contains 'def': {'def ' in text}\n")
        f.write(f"Contains 'json': {'json' in text.lower()}\n")
        
    raise json.JSONDecodeError(
        f"Could not extract JSON from LLM response. Saved to {debug_file} for debugging. "
        f"The LLM may have returned Python code instead of JSON. "
        f"Preview: {text[:200]}",
        text, 0
    )

