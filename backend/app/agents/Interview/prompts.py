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
{{
  "skills": ["skill1", "skill2"],
  "experience_level": "junior|mid|senior|lead",
  "domains": ["domain1"],
  "has_projects": true,
  "project_summary": "brief summary of projects"
}}"""


# ── Question Generator (Dynamic, Context-Aware, Resume-Aware) ─────────────

PHASE_DESCRIPTIONS = {
    "resume": "Focus on projects and tech stack from {rag_chunks}. Ask about technical choices and decisions.",
    "core": "Focus on fundamentals: DBMS, OS, OOP. Ask conceptual questions.",
    "problem_solving": "Focus on DSA basics, reasoning, and real-world scenarios.",
    "behavioral": "Ask exactly one question about teamwork, conflict, or leadership.",
}

# ── Resume-Phase Prompt (dedicated — forces project-specific questions) ────
RESUME_PHASE_QUESTION_PROMPT = """You are a senior technical interviewer. You MUST ask a question about the candidate's ACTUAL project.

Projects:
{project_summary}

Context:
{rag_chunks}

CURRENT TOPIC: {topic}

STRICT RULES:
1. You MUST reference a SPECIFIC project, technology, or decision from the candidate's data above.
2. Do NOT ask generic theory questions like "What is REST API?" or "Explain MVC".
3. Ask about WHY they chose a technology, HOW they implemented something, or WHAT challenges they faced.
4. Max 15 words, single intent, conversational tone.
5. Examples of GOOD questions:
   - "Why did you choose MongoDB for your e-commerce project?"
   - "How did you handle authentication in your React app?"
   - "What challenges did you face deploying your Flask API?"
6. Examples of BAD questions (DO NOT generate these):
   - "What is React?" (generic theory)
   - "Explain how databases work" (not project-specific)
   - "Tell me about your experience" (too vague)

OUTPUT FORMAT (JSON only):
{{
  "question": "...",
  "phase": "resume",
  "topic": "{topic}",
  "type": "primary"
}}"""

# ── Standard Prompt (for core, problem_solving, behavioral phases) ─────────
QUESTION_GENERATION_PROMPT = """You are a senior technical interviewer conducting a structured interview.

FLOW:
Phases in order: resume, core, problem_solving, behavioral.

RULES:
1. RESUME PHASE: Use ONLY {rag_chunks}. Ask about project, tech stack, and decisions. Do NOT ask generic theory.
2. CORE PHASE: Ask fundamentals from DBMS, OS, OOP.
3. PROBLEM SOLVING: Ask DSA basics or scenarios.
4. BEHAVIORAL: Ask ONLY 1 question about experience.
5. ADAPTIVE: 
   - weak answer -> change topic
   - partial answer -> one follow-up
   - strong answer -> deeper question
6. QUALITY: Max 15 words, single intent, no repetition, no hallucination.
7. TRANSITIONS: Use phrases like "Let's move to fundamentals" or "Now a problem-solving question."

Current Phase: {phase}
Topic: {topic}
Intent: {type}

OUTPUT FORMAT (JSON only):
{{
  "question": "...",
  "phase": "{phase}",
  "topic": "{topic}",
  "type": "primary | follow-up"
}}"""

# ── Basic Practice Agent Prompt ──────────────────────────────────────────────
BASIC_PRACTICE_QUESTION_GENERATION_PROMPT = """You are a strictly controlled interview question generator.

You MUST generate the next question without causing system errors.

---
# 🎯 OBJECTIVE
Generate ONE valid question about: {target_topic}

---
# 🧠 INPUT
* mode: {mode}
* question_number: {question_number}
* last_answer: {last_answer}
* used_topics: {used_topics}

---
# 🚨 SAFETY RULE (CRITICAL)
DO NOT assume any variable exists unless explicitly provided.
DO NOT use parameters like:
* last_question
* external memory not in input

---
# 🎯 BASIC PRACTICE FLOW
Q1–Q6 → resume (project-specific questions)
Q7–Q11 → core
Q12–Q14 → DSA / advanced
Q15 → mixed

---
# 🚨 HARD FLOW CONTROL (MANDATORY)
## Q1–Q6 → RESUME QUESTIONS ONLY
Rules:
* MUST reference a real project (e.g., FarmXpert)
* MUST ask about implementation
* MUST NOT ask generic/system design questions

---
# 🚨 NO REPETITION
* Never repeat concept
* Never rephrase question

---
# 🚨 SKIP RULE
If last_answer = "skip":
* change topic completely
* DO NOT ask follow-up

---
# 🎯 OUTPUT
Return ONE clean question only in the following JSON format:
```json
{{
  "question": "...",
  "concept": "unique_concept",
  "secondary_concept": "secondary_concept_if_any",
  "topic": "{target_topic}",
  "difficulty": "medium"
}}
```

---
# 🧠 FINAL RULE
You are executing a FIXED interview flow, not generating random questions.
"""

# ── Deterministic concept → question conversion (LLM does NOT pick topic) ────

DETERMINISTIC_CONCEPT_QUESTION_PROMPT = """You are a senior technical interviewer reviewing a candidate's actual work.

INPUT:
Topic: {topic}
Concept: {concept}
Candidate's Project Context: {rag_context}
Previous Questions Asked: {question_history}
Technologies Discussed: {technologies_discussed}
Projects Discussed: {projects_discussed}
Previous Concepts: {previous_concepts}
Current Difficulty: {current_difficulty}
Interview Phase: {interview_phase}

Generate exactly ONE interview question about the provided concept.

Rules:
* You MUST ground the question in the candidate's actual projects and technologies from the Project Context above.
* Reference specific project names, technologies, or decisions from the context.
* Ask WHY they chose something, HOW they implemented it, or WHAT challenges they faced.
* Use diverse sentence structures. Avoid repetitive use of identical wording.
* Prefer conversational openings (e.g., "Suppose...", "Walk me through...", "Imagine...").
* Do NOT ask any question that is similar to the Previous Questions Asked.
* Maximum 25 words.
* Conversational tone ("How did you...", "Why did you choose...", "What was your approach to...").
* No greetings.
* No explanations.
* No follow-up text.
* Return question only."""


PHRASE_CONCEPT_QUESTION_PROMPT = """You are a senior technical interviewer conducting a technical interview.

INPUT:
Topic: {topic}
Concept: {concept}
Difficulty: {difficulty}
Previous Questions Asked: {question_history}
Technologies Discussed: {technologies_discussed}
Projects Discussed: {projects_discussed}
Previous Concepts: {previous_concepts}
Current Difficulty: {current_difficulty}
Interview Phase: {interview_phase}

Generate exactly ONE natural, conversational interview question about the provided concept.

Rules:
* The question must target the concept: {concept}.
* The difficulty level must be: {difficulty}.
* Keep the question concise and focused on a single intent (maximum 25 words).
* Do NOT ask the candidate to write code, implement a function, or program anything. Focus on verbal reasoning, explanation, or trade-offs.
* Use diverse sentence structures. Avoid repetitive use of identical wording.
* Prefer conversational openings (e.g., "Suppose...", "Imagine...", "Walk me through...").
* Do NOT ask any question that is similar to the Previous Questions Asked.
* Conversational, professional tone (e.g., "What are the trade-offs of...", "How would you approach...", "Why is...").
* No greetings.
* No explanations or extra text.
* Return the question text only."""



# ── Strict Agent Unified Prompt ──────────────────────────────────────────────
STRICT_QUESTION_GENERATION_PROMPT = """You are a STRICT role-based interview question generator.

Your job is to generate ONE question with correct topic flow.

---
# 🎯 OBJECTIVE
Generate ONE interview question about: {target_topic}

---
# 🧠 INPUT
* mode: {mode}
* question_number: {question_number}
* last_answer: {last_answer}
* used_topics: {used_topics}

---
# 🚨 CRITICAL RULES

## 1. TOPIC-BASED FLOW
Questions MUST follow the target topic.
* Target Topic: {target_topic}

---
## 2. SKIP RULE (VERY IMPORTANT)
If last_answer = "skip" OR "no idea":
→ Ask about a different concept or subtopic under {target_topic}.

---
## 3. DIFFICULTY FLOW
* Q1–Q4 → easy
* Q5–Q10 → medium
* Q11–Q15 → hard

---
## 4. ONE CONCEPT ONLY
Each question must test ONLY ONE idea.

---
## 5. NATURAL QUESTIONS
Ask like real interviewer.

---
# 🚫 FORBIDDEN
* Do NOT ask generic overview questions.
* Do NOT ask behavioral questions.

---
# 🎯 OUTPUT
Return ONLY:
```json
{{
  "question": "...",
  "concept": "...",
  "secondary_concept": "...",
  "topic": "{target_topic}"
}}
```
"""



# ── Resume-Aware First Question (with projects) ─────────────────────────

RESUME_PROJECT_QUESTION_PROMPT = """Generate a project-based interview question. Return JSON only.

Job Description: {job_description}
Student skills: {skill_summary}
Project summary: {project_summary}
Difficulty: {difficulty}

RULES:
1. LENGTH: Max 18 words.
2. SINGLE INTENT: Ask about one specific aspect of a project.
3. STYLE: Conversational ("How did you...", "Why did you choose...").
4. CONTENT: Explicitly reference a project from their resume: {project_summary}.

Return JSON:
{{
  "question": "question text",
  "type": "primary",
  "intent": "reasoning",
  "topic": "projects",
  "difficulty": "medium"
}}"""


# ── Resume-Aware First Question (NO projects) ───────────────────────────

RESUME_NO_PROJECT_QUESTION_PROMPT = """Generate a fundamental skill interview question. Return JSON only.

Job Description: {job_description}
Student skills: {skill_summary}
Difficulty: {difficulty}

RULES:
1. LENGTH: Max 18 words.
2. SINGLE INTENT: Ask only one conceptual thing.
3. STYLE: Conversational ("What does...", "How would you...").

Return JSON:
{{
  "question": "question text",
  "type": "primary",
  "intent": "concept",
  "topic": "fundamentals",
  "difficulty": "easy"
}}"""


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
Difficulty: {difficulty}

RELEVANT CV CONTEXT (from candidate's actual resume/documents):
{rag_context}

CRITICAL RULES:
1. LENGTH: Max 18 words.
2. SINGLE INTENT: Ask only one thing from the CV context.
3. STYLE: Conversational ("How did you...", "What was the...").
4. CONTENT: Reference their real projects or experience from the CV context.

Return JSON:
{{
  "question": "question text",
  "type": "primary",
  "intent": "concept|reasoning",
  "topic": "specific topic",
  "difficulty": "easy|medium|hard"
}}"""


RAG_FOLLOWUP_PROMPT = """Generate a human-like follow-up question. Return JSON only.

Previous question: {last_question}
Candidate's answer: {last_answer}
Difficulty: {difficulty}

RELATED CONCEPTS FROM CANDIDATE'S CV:
{followup_context}

CRITICAL RULES:
1. LENGTH: Max 18 words.
2. SINGLE INTENT: Ask just one deeper thing.
3. LOGIC: 
   - If answer was weak: Ask clarification.
   - If answer was strong: Ask trade-offs/why ("What are the trade-offs...", "Why did you...").

Return JSON:
{{
  "question": "question text",
  "type": "follow-up",
  "intent": "clarification|reasoning",
  "topic": "specific topic",
  "difficulty": "easy|medium|hard"
}}"""


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

