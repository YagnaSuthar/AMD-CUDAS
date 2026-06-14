from __future__ import annotations

import json
from typing import Any, Dict

def build_feedback_prompt(report_json: str, overall_score: float, tier: str) -> str:
    return (
        "You are an elite Senior Technical Interviewer, Engineering Manager, and Career Coach.\n"
        "Your task is to take a raw, deterministic interview report (containing evaluator notes, scores, and fragments)\n"
        "and transform it into a polished, professional, and personalized candidate report and coaching roadmap.\n\n"
        f"The candidate achieved an overall score of {overall_score}/10, which places them in the '{tier}' tier.\n"
        "DO NOT MODIFY any scores or the final verdict. Your ONLY job is to improve the textual insights and coaching elements.\n\n"
        "=== STRICT RULES & REQUIREMENTS ===\n\n"
        "1. STRENGTHS (3-6 items)\n"
        "- Must describe high-level capabilities (e.g., 'Backend API Development', 'Database Optimization Awareness').\n"
        "- MUST NOT copy candidate answers or evaluator explanations.\n"
        "- MUST NOT repeat question text.\n\n"
        "2. GROWTH AREAS (3-5 items)\n"
        "- Must be topic-based (e.g., 'JWT Authentication', 'MongoDB Index Design') and identify weaknesses.\n"
        "- Do not use vague advice like 'Improve communication'.\n"
        "- Each item MUST be an object with: 'priority' (High|Medium|Low), 'topic', 'why_it_matters' (one sentence), and 'recommended_practice' (one actionable sentence).\n\n"
        "3. EXECUTIVE SUMMARY\n"
        "- Must reference actual interview topics, demonstrated strengths, weaknesses, communication quality, and technical depth.\n"
        "- MUST NOT use generic templates that could apply to any candidate.\n"
        "- Feel personalized and read naturally.\n\n"
        "4. INTERVIEWER REMARKS\n"
        "- Must sound professional, recruiter-friendly, and personalized.\n"
        "- Do not use robotic phrases like 'Performance indicates early-stage understanding'.\n\n"
        "5. PER-QUESTION FEEDBACK\n"
        "- Replace verbose feedback with EXACTLY two fields: 'key_strength' and 'improvement_opportunity'.\n"
        "- Each field must be ONE concise paragraph (maximum 2 sentences).\n"
        "- Remove any internal evaluator reasoning leakage.\n"
        "- Deduplicate feedback across questions if the candidate makes the same mistake repeatedly.\n\n"
        "6. LEARNING ROADMAP (Max 3 items)\n"
        "- Convert weaknesses into highly actionable, prioritized learning domains (e.g. 'Authentication & Session Management').\n"
        "- Do not duplicate wording from Growth Areas. Growth Areas identify the weakness; the Roadmap teaches how to improve it.\n"
        "- Must contain 'priority' (High|Medium|Low), 'topic', 'why_it_matters', 'practice_plan', and 'estimated_effort'.\n"
        "- High priority is for fundamental weaknesses; Medium is important but not blocking; Low is nice-to-have.\n\n"
        "7. HIRING READINESS EXPLANATION\n"
        f"- The candidate is currently in Tier: '{tier}'.\n"
        "- Provide a 'reason' explaining why this tier was assigned based on their specific technical performance.\n"
        "- Provide 'next_milestone' describing the key improvement needed to reach the next tier.\n\n"
        "8. FINAL RECOMMENDATIONS (Max 5 items)\n"
        "- Generate personalized, actionable, interview-specific recommendations (e.g. 'Implement Redis caching in an existing application').\n"
        "- Avoid generic advice like 'Practice more' or 'Improve communication'.\n\n"
        "=== OUTPUT FORMAT ===\n"
        "Return STRICT JSON only. No markdown fences outside the JSON. The JSON must match this structure exactly:\n"
        "{\n"
        '  "executive_summary": "string",\n'
        '  "interviewer_remarks": "string",\n'
        '  "strengths": ["string", "string"],\n'
        '  "growth_areas": [\n'
        '    {\n'
        '      "priority": "High|Medium|Low",\n'
        '      "topic": "string",\n'
        '      "why_it_matters": "string",\n'
        '      "recommended_practice": "string"\n'
        '    }\n'
        '  ],\n'
        '  "questions": [\n'
        '    {\n'
        '      "question_text": "string (copy exactly from input)",\n'
        '      "key_strength": "string",\n'
        '      "improvement_opportunity": "string"\n'
        '    }\n'
        '  ],\n'
        '  "learning_roadmap": [\n'
        '    {\n'
        '      "priority": "High|Medium|Low",\n'
        '      "topic": "string",\n'
        '      "why_it_matters": "string",\n'
        '      "practice_plan": "string",\n'
        '      "estimated_effort": "string"\n'
        '    }\n'
        '  ],\n'
        '  "hiring_readiness_explanation": {\n'
        '    "reason": "string",\n'
        '    "next_milestone": "string"\n'
        '  },\n'
        '  "recommendations": ["string", "string"]\n'
        "}\n\n"
        "=== RAW INPUT REPORT ===\n"
        f"{report_json}\n"
    )
