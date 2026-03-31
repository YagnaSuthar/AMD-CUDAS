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

Job Description: {job_description}
Student skills: {skill_summary}
Last question asked: {last_question}
Summary of last answer: {last_answer_summary}
Student behavior: {behavior}
Difficulty: {difficulty}
Resume context: {resume_context}

Rules:
1. Question must relate to the job description requirements
2. Question should test skills relevant to the position
3. Must NOT repeat the last question topic
4. If behavior is "arrogant", ask a harder probing question
5. If last answer was short or weak, ask a deeper follow-up on the same topic
6. If last answer was detailed, ask the next logical technical question
7. Use a human, professional, conversational tone — NOT robotic
8. Clear, specific, answerable in 2-3 minutes
9. CRITICAL: At least once in the interview, ask a question that explicitly references both the job description AND the student's resume/projects

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


# ── Resume-Aware First Question (with projects) ─────────────────────────

RESUME_PROJECT_QUESTION_PROMPT = """Generate the first interview question about the student's projects. Return JSON only.

Job Description: {job_description}
Student skills: {skill_summary}
Project summary: {project_summary}
Difficulty: {difficulty}

Rules:
1. Ask about a specific project from their resume that relates to the job description
2. Ask about technologies used, challenges faced, or a real-world problem they solved
3. Connect the project to job requirements when possible
4. Tone must be human, professional, and friendly — like a real interviewer
5. CRITICAL: Explicitly reference the job description and how their project experience aligns with it
6. Example tone: "I see in your resume you worked on [project]. The job description emphasizes [requirement]. Can you explain how your experience on that project prepared you for this?"

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


# ── Resume-Aware First Question (NO projects) ───────────────────────────

RESUME_NO_PROJECT_QUESTION_PROMPT = """Generate the first interview question for a student without projects. Return JSON only.

Job Description: {job_description}
Student skills: {skill_summary}
Difficulty: {difficulty}

The student's resume does NOT include any project details. Your first question should relate to the job description and test their fundamental understanding of required skills.

Rules:
1. Ask a fundamental question related to the job description
2. Test basic understanding of required skills
3. Be polite. Do NOT judge the student.
4. Human, professional, conversational tone — NOT robotic
5. CRITICAL: Explicitly reference the job description and how their skills align with what the role requires
6. Example tone: "I see from your resume that you have experience with [skill]. The job description emphasizes [requirement]. Can you explain how you would apply [skill] to solve a typical problem in this role?"

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

MEMORY_UPDATE_PROMPT = """You are an AI assistant that updates interview assessments. You must respond with valid JSON only.

Previous summary: {previous_summary}
Weak areas: {weak_areas}
Strong areas: {strong_areas}
Latest answer: {answer}
Current behavior: {behavior}

Rules:
1. Keep summary to 2-3 sentences max
2. Update weak/strong areas based on latest answer
3. Remove weak areas if candidate later showed strength

IMPORTANT: Respond with ONLY a JSON object. No explanations, no code blocks, no Python functions.

Example format:
{{"summary": "updated summary", "weak_areas": ["area1"], "strong_areas": ["area1"]}}

Your JSON response:"""


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


# ── Feedback Sentence Pools (No LLM call — selected by answer quality) ────

import random

FEEDBACK_POOLS = {
    # weighted_score >= 0.7
    "good": [
        "Great explanation! You clearly understand this concept well.",
        "I appreciate your confidence. That was a clear and structured answer.",
        "Well done! You explained it very effectively. Let's continue.",
        "Excellent answer! You've demonstrated a strong grasp of this topic.",
        "Nice work! That was precise and well-articulated.",
    ],
    # weighted_score 0.4 – 0.7
    "average": [
        "That's a fair attempt. You're on the right track.",
        "Good effort, but try to be more precise next time.",
        "You're heading in the right direction. Let's see how you handle the next one.",
        "Not bad! A bit more depth would have made it stronger.",
        "Decent answer. Let's keep going and see how you do.",
    ],
    # weighted_score < 0.4
    "poor": [
        "It seems you're not very familiar with this concept. No worries, let's try something else.",
        "That's okay, we'll move to a different area. Don't worry about it.",
        "Let's try a simpler question on this topic to build your confidence.",
        "No problem. Not every question is easy. Let's move forward.",
        "I understand, this can be tricky. Let's try another angle.",
    ],
    # no answer provided
    "no_answer": [
        "Are you able to hear me? Would you like me to repeat the question?",
        "Take your time. Whenever you're ready, you can share your answer.",
    ],
    # skipped / refusal
    "skipped": [
        "I understand you'd like to skip this question. Let's continue with the next one.",
        "No worries, we'll move on. Let's try a different topic.",
        "That's okay! Let me ask you something else.",
        "Understood. Let's proceed to the next question.",
    ],
}

# Legacy mapping kept for backward compatibility
BEHAVIOR_RESPONSES = {
    "arrogant_correct": FEEDBACK_POOLS["good"][0],
    "arrogant_incorrect": FEEDBACK_POOLS["poor"][0],
    "polite_correct": FEEDBACK_POOLS["good"][0],
    "polite_incorrect": FEEDBACK_POOLS["average"][0],
    "neutral_correct": FEEDBACK_POOLS["good"][0],
    "neutral_incorrect": FEEDBACK_POOLS["average"][0],
    "no_answer": FEEDBACK_POOLS["no_answer"][0],
    "timeout_reminder": FEEDBACK_POOLS["no_answer"][1],
}


def get_feedback_for_answer(
    weighted_score: float,
    has_answer: bool,
    answer_type: str = "VALID",
    used_sentences: set | None = None,
    last_feedback: str = "",
) -> str:
    """Select a feedback sentence based on the candidate's answer quality.

    - SKIPPED/REFUSAL/IRRELEVANT → skipped pool
    - weighted_score >= 0.7 → good pool
    - weighted_score 0.4–0.7 → average pool
    - weighted_score < 0.4 → poor pool
    - no answer → no_answer pool

    Avoids repeating the *last* feedback sentence.  Tracks used sentences
    in ``used_sentences`` so the same sentence is not picked again across
    the session.  When a pool is exhausted the tracking resets (but the
    last sentence is still avoided).
    """
    if used_sentences is None:
        used_sentences = set()

    # Pick the right pool
    if answer_type in ("SKIPPED", "REFUSAL", "IRRELEVANT"):
        pool_key = "skipped"
    elif not has_answer:
        pool_key = "no_answer"
    elif weighted_score >= 0.7:
        pool_key = "good"
    elif weighted_score >= 0.4:
        pool_key = "average"
    else:
        pool_key = "poor"

    pool = FEEDBACK_POOLS[pool_key]

    # Filter out used sentences AND the last feedback
    available = [s for s in pool if s not in used_sentences and s != last_feedback]

    # If all used up, reset but still exclude last_feedback
    if not available:
        used_sentences.difference_update(set(pool))
        available = [s for s in pool if s != last_feedback]
        if not available:
            available = list(pool)  # absolute fallback

    chosen = random.choice(available)
    used_sentences.add(chosen)
    return chosen


# ── RAG-Enhanced Question Generation ─────────────────────────────────────

RAG_QUESTION_GENERATION_PROMPT = """Generate one interview question using the candidate's CV data. Return JSON only.

Job Description: {job_description}
Student skills: {skill_summary}
Last question asked: {last_question}
Summary of last answer: {last_answer_summary}
Student behavior: {behavior}
Difficulty: {difficulty}

RELEVANT CV CONTEXT (from candidate's actual resume/documents):
{rag_context}

Rules:
1. Use the CV context to ask SPECIFIC questions about the candidate's actual experience
2. Reference their real projects, skills, or experience from the CV context
3. Must NOT repeat the last question topic
4. If candidate mentioned a technology in their answer, ask a deeper follow-up about it
5. If behavior is "arrogant", ask a harder probing question
6. If last answer was weak, ask a deeper follow-up on the same topic
7. If last answer was detailed, move to the next logical topic from their CV
8. Use a human, professional, conversational tone — NOT robotic
9. Clear, specific, answerable in 2-3 minutes

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


RAG_FOLLOWUP_PROMPT = """Generate a follow-up question based on the candidate's answer and related CV data. Return JSON only.

Previous question: {last_question}
Candidate's answer: {last_answer}
Difficulty: {difficulty}

RELATED CONCEPTS FROM CANDIDATE'S CV:
{followup_context}

Rules:
1. Ask a follow-up that connects the candidate's answer to related concepts from their CV
2. Make the interview feel natural — like a real interviewer who read their resume
3. Example: If they mentioned "React hooks", ask about useEffect or state management from their projects
4. Tone: professional, conversational, human-like

Return JSON:
{{"question": "question text", "topic": "specific topic", "difficulty": "easy|medium|hard"}}"""


# ── Weighted Scoring Evaluation ───────────────────────────────────────────

WEIGHTED_EVALUATION_PROMPT = """Evaluate this interview answer on three dimensions. Return JSON only.

QUESTION: {question}
ANSWER: {answer}
DIFFICULTY LEVEL: {difficulty}

IMPORTANT: Be extremely critical and strict with your evaluation.
Do NOT treat skipped, refusal, irrelevant, generic, or bad answers as confident or correct.
If the candidate says things like "skip", "I don't know", "pass", "next question",
or provides an incorrect, generic, or meaningless answer, you MUST score technical_score as 0.0-0.2
and communication/behavior scores as 0.1-0.3 at most.

Score each dimension from 0.0 to 1.0:

1. technical_score: How technically accurate and complete is the answer?
   - 0.0-0.2: Skipped, refused, incorrect, generic, or no relevant content
   - 0.2-0.4: Barely relevant or mostly incorrect
   - 0.4-0.6: Partially correct, missing key concepts
   - 0.6-0.8: Mostly correct with good understanding
   - 0.8-1.0: Excellent, thorough, and precise

2. communication_score: How clearly and professionally did they communicate?
   - 0.0-0.2: Skipped, extremely brief, or one-word answer
   - 0.2-0.4: Incoherent or very poorly structured
   - 0.4-0.6: Understandable but poorly structured
   - 0.6-0.8: Clear and well-organized
   - 0.8-1.0: Exceptional clarity and articulation

3. behavior_score: How professional and appropriate is their demeanor?
   - 0.0-0.3: Rude, dismissive, or inappropriate
   - 0.3-0.6: Neutral, minimal engagement
   - 0.6-0.8: Professional and engaged
   - 0.8-1.0: Excellent attitude, enthusiastic, thoughtful

Also classify behavior tone:
- "polite": respectful, professional
- "arrogant": dismissive, condescending
- "neutral": neither polite nor arrogant

Determine next difficulty:
- If weighted_score < 0.4: "easy"
- If weighted_score 0.4-0.7: "medium"
- If weighted_score > 0.7: "hard"

Return JSON:
{{"technical_score": 0.7, "communication_score": 0.8, "behavior_score": 0.9, "behavior_flag": "neutral", "next_difficulty": "medium"}}"""


# ── Student Report ────────────────────────────────────────────────────────

STUDENT_REPORT_PROMPT = """Generate a friendly, developmental interview report for the student. Return JSON only.

Session summary: {session_summary}
Technical score: {avg_technical:.2f}/1.0
Communication score: {avg_communication:.2f}/1.0
Behavior score: {avg_behavior:.2f}/1.0
Final weighted score: {final_score:.2f}/1.0
Weak areas: {weak_areas}
Strong areas: {strong_areas}
Questions asked: {total_questions}

Generate a supportive report with:
1. weak_areas: COMPLETE list of ALL specific technical gaps and missing skills identified during the session. Include every gap.
2. missing_skills: Core skills the student should learn or improve.
3. improvements: Concrete, actionable suggestions.
4. learning_path: Recommended topics/resources to study (ordered by priority).
5. encouragement: A friendly, encouraging message.

Tone: Friendly, supportive, constructive. Like a mentor giving advice.
IF the session was terminated early due to a proctoring violation (e.g. TAB_SWITCH, PHONE_DETECTED), clearly state it as a critical failure point.

Return JSON:
{{"weak_areas": ["area1"], "missing_skills": ["skill1"], "improvements": ["suggestion1"], "learning_path": ["topic1: description"], "encouragement": "message"}}"""


# ── Recruiter Report ──────────────────────────────────────────────────────

RECRUITER_REPORT_PROMPT = """Generate a professional recruiter assessment report. Return JSON only.

Session summary: {session_summary}
Technical score: {avg_technical:.2f}/1.0
Communication score: {avg_communication:.2f}/1.0
Behavior score: {avg_behavior:.2f}/1.0
Final weighted score: {final_score:.2f}/1.0
Weak areas: {weak_areas}
Strong areas: {strong_areas}
Behavior history: {behavior_summary}
Total questions: {total_questions}
Interview ended: {ended_reason}

Based on the final weighted score, provide a recommendation:
- final_score >= 0.8: "STRONGLY_HIRE" — Exceptional candidate
- final_score >= 0.6: "SHOULD_HIRE" — Good candidate, meets expectations
- final_score >= 0.4: "WEAK_HIRE" — Below expectations, consider with reservations
- final_score < 0.4: "REJECT" — Does not meet minimum requirements

Generate:
1. technical_assessment: Professional summary of technical ability.
2. communication_assessment: Assessment of communication skills.
3. behavior_analysis: Analysis of professional behavior. (MUST explicitly mention any proctoring violations if they occurred).
4. strengths: COMPLETE, EXHAUSTIVE list of ALL core strengths demonstrated.
5. weaknesses: COMPLETE, EXHAUSTIVE list of ALL technical gaps, flaws, and proctoring violations.
6. recommendation: One of STRONGLY_HIRE, SHOULD_HIRE, WEAK_HIRE, REJECT
7. justification: Brief justification for the recommendation.

CRITICAL: Do not truncate or omit any strengths or weaknesses passed in the context. List everything.

Return JSON:
{{"technical_assessment": "text", "communication_assessment": "text", "behavior_analysis": "text", "strengths": ["s1"], "weaknesses": ["w1"], "recommendation": "SHOULD_HIRE", "justification": "text"}}"""


# ── Early Exit Message ────────────────────────────────────────────────────

EARLY_EXIT_MESSAGE = (
    "Thank you for your time. Based on our conversation so far, "
    "we will conclude the interview here. "
    "You will receive a detailed report with feedback and suggestions for improvement."
)

