from __future__ import annotations

from typing import Optional


def build_evaluator_prompt(
    question: str,
    answer: str,
    phase: str,
    difficulty: str,
    keywords: Optional[str] = None,
    topic: str = "",
    concept: str = "",
    role: str = "",
) -> str:
    keywords_val = keywords if keywords else "None"
    
    return (
        "You are a senior technical interviewer.\n\n"
        "Evaluate the candidate’s answer realistically like a human interviewer. "
        "Be fair: reward logical thinking even if the phrasing is slightly off.\n\n"
        "IMPORTANT (VOICE / STT ROBUSTNESS): The answer may come from speech-to-text (STT). "
        "Do NOT penalize for missing symbols, imperfect grammar, or informal phrasing. "
        "Evaluate by MEANING, not exact wording.\n"
        "Treat common spoken variants as equivalent, for example:\n"
        "- 'big o of n square' / 'order n square' / 'n square' => O(n^2)\n"
        "- 'oop' => object-oriented programming\n"
        "- 'makes searching faster' => improves lookup time\n\n"
        "Return STRICT JSON only. No explanation outside JSON.\n\n"
        "---\n\n"
        "# INPUT\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER:\n{answer}\n\n"
        f"PHASE:\n{phase}\n\n"
        f"TOPIC:\n{topic if topic else 'None'}\n\n"
        f"CONCEPT:\n{concept if concept else 'None'}\n\n"
        f"ROLE:\n{role if role else 'None'}\n\n"
        f"DIFFICULTY:\n{difficulty}\n\n"
        f"EXPECTED KEYWORDS:\n{keywords_val}\n\n"
        "---\n\n"
        "# EVALUATION DIMENSIONS (0–10)\n\n"
        "1. correctness → accuracy of the technical facts\n"
        "2. completeness → how fully the answer addresses the question\n"
        "3. concept_depth → depth of understanding (the 'why')\n"
        "4. communication → clarity and logical structure\n"
        "5. confidence → decisiveness and avoidance of filler\n\n"
        "---\n\n"
        "# EXPLICIT SCORING RUBRIC (Enforce these bands for Correctness, Completeness, and Depth)\n\n"
        "0–1: No answer, refusal, completely incorrect.\n"
        "2–3: Very weak answer, keyword recognition only, no explanation, no reasoning.\n"
        "4–5: Basic understanding, partially correct, incomplete explanation, limited depth.\n"
        "6–7: Good understanding, mostly correct, reasonable explanation, minor missing details.\n"
        "8–9: Strong interview answer, good depth, good terminology, good reasoning.\n"
        "10: Excellent industry-level answer, technically complete, clear, structured, professional.\n\n"
        "---\n\n"
        "# SCORING CALIBRATION (HUMAN MODE)\n\n"
        "* PARTIAL CREDIT: If the answer shows the correct direction but lacks depth, correctness MUST be 4–6.\n"
        "* MINIMUM SCORE: If the answer is partially correct, do NOT score correctness below 4.\n"
        "* UNDERSTANDABILITY: If the answer is intelligible, communication MUST be ≥ 3.\n"
        "* FAIRNESS: Minor terminology slips should NOT heavily reduce the score. Focus on practical understanding.\n"
        "* DIRECT FACT EXCEPTION: If the question asks for a direct fact (e.g. 'What does X stand for?'), short answers are expected and MUST NOT be penalized. They should score 9-10 if correct. If the question asks for an explanation (e.g. 'Explain X'), keyword-only answers MUST score 0-2 for completeness and depth.\n\n"
        "---\n\n"
        "# CONSISTENCY CONSTRAINTS\n\n"
        "* If correctness ≤ 3: concept_depth MUST be capped at 3, completeness MUST be capped at 3.\n"
        "* If answer is incomplete: correctness MUST be capped at 5.\n"
        "* If NO ANSWER / Refusal: correctness = 0, completeness = 0, concept_depth = 0, confidence = 1.\n\n"
        "---\n\n"
        "# FEEDBACK STRUCTURE (MANDATORY)\n\n"
        "Your final_feedback must include:\n"
        "1. 1–2 Strengths: Explicitly mention what they got right.\n"
        "2. 1–2 Mistakes: Identify the specific error or gap.\n"
        "3. 1 Suggestion: Clear actionable step for improvement.\n\n"
        "---\n\n"
        "# OUTPUT EXTRACTION\n\n"
        "good_points → List of actual technical successes in the answer\n"
        "mistakes → List of technical errors or omissions\n"
        "missing_points → List of crucial concepts not mentioned\n"
        "misconceptions → Fundamental conceptual errors found\n\n"
        "---\n\n"
        "# STRICT DATA RULE\n\n"
        "Do NOT assume candidate knows things not explicitly stated. Evaluate ONLY what is present.\n\n"
        "---\n\n"
        "# OUTPUT FORMAT\n\n"
        "{\n"
        '  "correctness": int,\n'
        '  "completeness": int,\n'
        '  "concept_depth": int,\n'
        '  "communication": int,\n'
        '  "confidence": int,\n'
        '  "good_points": [string],\n'
        '  "mistakes": [string],\n'
        '  "missing_points": [string],\n'
        '  "misconceptions": [string],\n'
        '  "severity": "low/medium/high",\n'
        '  "final_feedback": "string"\n'
        "}\n"
    )
