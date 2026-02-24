"""
Centralized LLM prompt templates for the interview system.
All prompts are stored as constants — no hard-coded strings in agents.
"""

# ── Profile Intelligence ──────────────────────────────────────────────────

PROFILE_ANALYSIS_PROMPT = """You are a senior technical recruiter analyzing a candidate profile.

Given the following candidate information, produce a JSON object with these fields:
- "skills": a list of the candidate's key technical and soft skills
- "experience_level": one of "junior", "mid", "senior", or "lead"
- "domains": a list of professional domains the candidate is suited for

CANDIDATE INFORMATION:
Resume: {resume_text}
Portfolio: {portfolio_text}
Experience: {experience_years} years
Known Skills: {skills}

Respond ONLY with the JSON object.

    CRITICAL INSTRUCTION: Output exactly one raw JSON object. Do NOT wrap it in ```json code fences. Do NOT add any conversational text before or after.
    """


# ── Question Generator ────────────────────────────────────────────────────

QUESTION_GENERATION_PROMPT = """You are a technical interviewer generating a single interview question.

Context about the candidate and session:
{context}

Difficulty level requested: {difficulty}

Generate a question that:
1. Matches the requested difficulty level
2. Is relevant to the candidate's domain and skills
3. Tests real understanding, not just recall
4. Is clear, specific, and answerable in 2-3 minutes

    Respond ONLY with a JSON object containing:
    - "question": the interview question text
    - "topic": the specific topic being tested (e.g. "Python async programming")
    - "difficulty": the actual difficulty ("easy", "medium", or "hard")

    CRITICAL INSTRUCTION: Output exactly one raw JSON object. Do NOT wrap it in ```json code fences. Do NOT add any conversational text before or after.
    """


# ── Answer Evaluation ─────────────────────────────────────────────────────

ANSWER_EVALUATION_PROMPT = """You are a senior technical interviewer evaluating a candidate's answer.

QUESTION: {question}

CANDIDATE'S ANSWER: {answer}

Evaluate the answer on each criterion from 1 to 10:
1. **clarity**: How clear and well-structured is the answer?
2. **depth**: How deeply does it demonstrate understanding?
3. **confidence**: How confident and decisive is the response?

Also decide what difficulty the NEXT question should be:
- If the answer is weak (avg < 4): "easy"
- If the answer is moderate (avg 4-7): "medium"
- If the answer is strong (avg > 7): "hard"

Respond ONLY with a JSON object containing:
- "clarity": int (1-10)
- "depth": int (1-10)
- "confidence": int (1-10)
- "next_difficulty": "easy" | "medium" | "hard"
"""


# ── Memory / Context Agent ────────────────────────────────────────────────

MEMORY_UPDATE_PROMPT = """You are maintaining a running assessment of a candidate during an interview.

PREVIOUS SUMMARY: {previous_summary}
PREVIOUS WEAK AREAS: {weak_areas}
PREVIOUS STRONG AREAS: {strong_areas}

LATEST ANSWER: {answer}

Update the assessment:
1. Incorporate the latest answer into the running summary.
2. Identify any NEW weak areas revealed.
3. Identify any NEW strong areas revealed.
4. Remove areas from weak_areas if the candidate later demonstrated strength in them.

Respond ONLY with a JSON object containing:
- "summary": updated running summary (2-4 sentences)
- "weak_areas": updated list of weak area strings
- "strong_areas": updated list of strong area strings
"""


# ── Feedback & Report ─────────────────────────────────────────────────────

FEEDBACK_REPORT_PROMPT = """You are producing a final interview assessment report.

SESSION SUMMARY: {session_summary}
OVERALL SCORES: {score_summary}
WEAK AREAS: {weak_areas}
STRONG AREAS: {strong_areas}

Produce a comprehensive but concise interview report.

Respond ONLY with a JSON object containing:
- "final_score": a float 0.0-10.0 representing overall performance
- "strengths": list of the candidate's demonstrated strengths
- "weaknesses": list of areas needing improvement
- "recommendation": one of "strong_hire", "hire", "maybe", "no_hire" with a 1-2 sentence justification
"""
