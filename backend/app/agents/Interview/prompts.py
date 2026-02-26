"""
Centralized LLM prompt templates for the interview system.
All prompts are stored as constants — no hard-coded strings in agents.
Optimized for Groq Llama-3.1-8b-instant: short system messages, structured JSON.
"""

# ── Profile Intelligence ──────────────────────────────────────────────────

PROFILE_ANALYSIS_PROMPT = """Analyze this candidate profile. Return JSON only.

Resume: {resume_text}
Portfolio: {portfolio_text}
Experience: {experience_years} years
Skills: {skills}

Return JSON:
{{"skills": ["skill1","skill2"], "experience_level": "junior|mid|senior|lead", "domains": ["domain1"], "has_projects": true, "project_summary": "brief summary of projects"}}"""


# ── Question Generator (Dynamic, Context-Aware, Resume-Aware) ─────────────

QUESTION_GENERATION_PROMPT = """Generate one interview question. Return JSON only.

Student skills: {skill_summary}
Last question asked: {last_question}
Summary of last answer: {last_answer_summary}
Student behavior: {behavior}
Difficulty: {difficulty}
Resume context: {resume_context}

Rules:
1. Question must relate to student's skills
2. Must NOT repeat the last question topic
3. If behavior is "arrogant", ask a harder probing question
4. If last answer was short or weak, ask a deeper follow-up on the same topic
5. If last answer was detailed, ask the next logical technical question
6. Use a human, professional, conversational tone — NOT robotic
7. Clear, specific, answerable in 2-3 minutes

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


# ── Resume-Aware First Question (with projects) ─────────────────────────

RESUME_PROJECT_QUESTION_PROMPT = """Generate the first interview question about the student's projects. Return JSON only.

Student skills: {skill_summary}
Project summary: {project_summary}
Difficulty: {difficulty}

Rules:
1. Ask about a specific project from their resume
2. Ask about technologies used, challenges faced, or a real-world problem they solved
3. Tone must be human, professional, and friendly — like a real interviewer
4. Example tone: "I noticed you have experience in web development. Can you explain one project where you solved a real-world problem?"

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


# ── Resume-Aware First Question (NO projects) ───────────────────────────

RESUME_NO_PROJECT_QUESTION_PROMPT = """Generate the first interview question for a student without projects. Return JSON only.

Student skills: {skill_summary}
Difficulty: {difficulty}

The student's resume does NOT include any project details. Your first question should politely ask why and whether they plan to start any.

Example tone: "I see that your resume does not include any project details. Can you tell me why you haven't worked on projects yet? Are you planning to start any soon?"

Rules:
1. Be polite. Do NOT judge the student.
2. Human, professional, conversational tone — NOT robotic
3. Ask both: why no projects + future plans

Return JSON:
{{"question": "question text", "topic": "projects", "difficulty": "easy"}}"""


# ── Answer Evaluation (with Behavior Classification) ─────────────────────

ANSWER_EVALUATION_PROMPT = """Evaluate this interview answer. Return JSON only.

QUESTION: {question}
ANSWER: {answer}

Score each 0-10:
- clarity: structure and communication
- depth: understanding demonstrated
- confidence: decisiveness
- technical_score: technical accuracy

Classify behavior tone:
- "polite": respectful, professional
- "arrogant": dismissive, condescending, overconfident
- "neutral": neither polite nor arrogant

Next difficulty: weak(<4)="easy", moderate(4-7)="medium", strong(>7)="hard"

Return JSON:
{{"clarity": 5, "depth": 5, "confidence": 5, "technical_score": 5, "behavior_flag": "neutral", "next_difficulty": "medium"}}"""


# ── Memory / Context Agent ────────────────────────────────────────────────

MEMORY_UPDATE_PROMPT = """Update interview assessment. Return JSON only.

Previous summary: {previous_summary}
Weak areas: {weak_areas}
Strong areas: {strong_areas}
Latest answer: {answer}
Current behavior: {behavior}

Rules:
1. Keep summary to 2-3 sentences max
2. Update weak/strong areas based on latest answer
3. Remove weak areas if candidate later showed strength

Return JSON:
{{"summary": "updated summary", "weak_areas": ["area1"], "strong_areas": ["area1"]}}"""


# ── Feedback & Report ─────────────────────────────────────────────────────

FEEDBACK_REPORT_PROMPT = """Generate final interview report. Return JSON only.

Session summary: {session_summary}
Scores: {score_summary}
Weak areas: {weak_areas}
Strong areas: {strong_areas}
Behavior history: {behavior_summary}

Return JSON:
{{"final_score": 7.5, "communication_score": 8.0, "strengths": ["s1"], "weaknesses": ["w1"], "behavior_summary": "summary", "recommendation": "strong_hire|hire|maybe|no_hire: justification"}}"""


# ── Greeting Templates (No LLM call — pure Python) ────────────────────────

GREETING_TEMPLATE = "Hello {student_name}, are you comfortable?"

GREETING_COMFORTABLE_YES = "Great. Can we start the interview?"

GREETING_COMFORTABLE_NO = (
    "Okay, no problem. We will conduct the interview later. Have a great day."
)

GREETING_START_NO = "Alright, we will schedule it later."


# ── Behavior-Reactive Response Templates (No LLM call) ───────────────────

BEHAVIOR_RESPONSES = {
    "arrogant_correct": (
        "Thank you for your answer. That's technically correct. "
        "Let me challenge you with something more nuanced."
    ),
    "arrogant_incorrect": (
        "I appreciate your confidence, but let me clarify — the correct approach "
        "involves a different perspective. Let's move to the next question."
    ),
    "polite_correct": (
        "Excellent answer! You've demonstrated a strong understanding of this topic. "
        "Well done. Let's continue."
    ),
    "polite_incorrect": (
        "Good attempt! The concept you're thinking of is close, but there's a "
        "subtle difference. Don't worry, let's move on to the next question."
    ),
    "neutral_correct": (
        "That's correct. Good job. Let's proceed to the next question."
    ),
    "neutral_incorrect": (
        "Not quite the answer I was looking for, but that's okay. "
        "Let's move on to the next one."
    ),
    "no_answer": (
        "Are you able to hear me? Would you like me to repeat the question?"
    ),
    "timeout_reminder": (
        "Take your time. Whenever you're ready, you can share your answer."
    ),
}
