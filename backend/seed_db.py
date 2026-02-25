"""
seed_db.py - Populate the database with realistic test data for all Interview agents.

Agent data requirements:
  ┌─────────────────────────┬──────────────────────────────────────────────────┐
  │ Agent                   │ DB Data Needed                                  │
  ├─────────────────────────┼──────────────────────────────────────────────────┤
  │ profile_intelligence    │ StudentProfile (resume, portfolio, exp_years)   │
  │                         │ Skill (skill_name, skill_level) per student     │
  │ question_generator      │ — (pure LLM, uses profile context string)      │
  │ answer_evaluator        │ — (pure LLM, uses question + answer text)      │
  │ memory_agent            │ InterviewMemory (creates if absent)             │
  │ feedback_agent          │ InterviewMemory + Answer + AnswerScore          │
  └─────────────────────────┴──────────────────────────────────────────────────┘
"""

import asyncio
import uuid
import logging
from datetime import datetime

from sqlalchemy import select, delete
from app.core.database import async_session_factory, engine
from app.models.interview import (
    Base, User, StudentProfile, Skill, InterviewSession,
    Question, Answer, AnswerScore, InterviewMemory,
    UserRole, SessionStatus, Difficulty, QuestionType,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Fixed UUIDs so we can reference them ──────────────────────────────────
STUDENT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
SESSION_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")


async def clean_old_data(session):
    """Remove previous test data to start fresh."""
    # Delete in reverse dependency order
    for model in [InterviewMemory, AnswerScore, Answer, Question, InterviewSession, Skill, StudentProfile, User]:
        await session.execute(delete(model))
    await session.flush()
    logger.info("Cleaned all existing data.")


async def seed_user(session) -> uuid.UUID:
    """Create a realistic student user."""
    user = User(
        id=STUDENT_ID,
        name="Ali Ahmed Khan",
        email="ali.khan@university.edu",
        role=UserRole.STUDENT,
    )
    session.add(user)
    await session.flush()
    logger.info("Created User: %s (%s)", user.name, user.email)
    return user.id


async def seed_profile(session, student_id: uuid.UUID):
    """Create a detailed student profile with resume and portfolio text.
    
    The profile_intelligence agent reads:
      - resume_text  → analyzed by LLM for skills/experience
      - portfolio_text → analyzed by LLM for domains
      - experience_years → used to determine experience level
    """
    profile = StudentProfile(
        student_id=student_id,
        resume_text="""
ALI AHMED KHAN
Full-Stack Software Engineer | 3 Years Experience

EDUCATION:
- BS Computer Science, FAST-NUCES Islamabad (2021-2025)
- GPA: 3.6/4.0

EXPERIENCE:
Software Engineer Intern — TechVentures (Jun 2024 – Aug 2024)
  • Built REST APIs using FastAPI and PostgreSQL for an e-commerce platform
  • Implemented JWT authentication and role-based access control
  • Optimized database queries reducing response time by 40%

Junior Developer — Freelance (Jan 2023 – May 2024)
  • Developed 5+ full-stack web applications using React and Node.js
  • Integrated Stripe payment gateway for 2 client projects
  • Deployed applications on AWS EC2 with Docker containers

PROJECTS:
AI-Powered Interview System (Capstone Project)
  • Built multi-agent interview system using LangChain and Gemini API
  • Designed PostgreSQL schema with SQLAlchemy ORM
  • Implemented real-time WebSocket communication for live interviews

Fleet Management System
  • Full-stack dashboard with React, Charts.js, and FastAPI backend
  • Role-based access control with admin, manager, and driver roles
  • Real-time vehicle tracking with Google Maps API integration

TECHNICAL SKILLS:
Python, JavaScript, TypeScript, SQL, HTML/CSS
FastAPI, React, Next.js, Node.js, Express
PostgreSQL, MongoDB, Redis
Docker, AWS EC2, Git, GitHub Actions
LangChain, Google Gemini API, OpenAI API
""",
        portfolio_text="""
GitHub: github.com/aliahmedkhan (15+ repositories, 200+ contributions)
LinkedIn: linkedin.com/in/aliahmedkhan

Notable Projects:
1. AI Interview Agent - Multi-agent system with LangChain (Python, FastAPI)
2. FleetFlow Dashboard - Real-time fleet management (React, FastAPI)
3. E-Commerce API - RESTful API with auth (FastAPI, PostgreSQL)
4. Chat Application - Real-time messaging (React, Socket.io, Node.js)
5. Weather Dashboard - API integration project (React, OpenWeatherMap)
""",
        experience_years=3,
    )
    session.add(profile)
    await session.flush()
    logger.info("Created StudentProfile with resume (%d chars) and portfolio (%d chars)",
                len(profile.resume_text), len(profile.portfolio_text))


async def seed_skills(session, student_id: uuid.UUID):
    """Create skill entries that the profile_intelligence agent reads.
    
    The agent reads these as: "skill_name (skill_level)" and sends to LLM.
    """
    skills_data = [
        ("Python", "advanced"),
        ("JavaScript", "advanced"),
        ("TypeScript", "intermediate"),
        ("FastAPI", "advanced"),
        ("React", "advanced"),
        ("PostgreSQL", "intermediate"),
        ("Docker", "intermediate"),
        ("AWS", "beginner"),
        ("LangChain", "intermediate"),
        ("Git", "advanced"),
        ("REST APIs", "advanced"),
        ("SQL", "intermediate"),
    ]
    for name, level in skills_data:
        skill = Skill(
            student_id=student_id,
            skill_name=name,
            skill_level=level,
        )
        session.add(skill)
    
    await session.flush()
    logger.info("Created %d Skills for student", len(skills_data))


async def seed_session(session, student_id: uuid.UUID) -> uuid.UUID:
    """Create an active interview session.
    
    The orchestrator uses session_id for:
      - memory_agent: to look up / create InterviewMemory
      - feedback_agent: to look up Answers + AnswerScores + Memory
    """
    interview = InterviewSession(
        session_id=SESSION_ID,
        student_id=student_id,
        job_role="Full-Stack Python Developer",
        status=SessionStatus.ACTIVE,
        current_difficulty=Difficulty.MEDIUM,
    )
    session.add(interview)
    await session.flush()
    logger.info("Created InterviewSession: %s (role: %s)", interview.session_id, interview.job_role)
    return interview.session_id


async def seed_all():
    """Run the full seed pipeline."""
    async with async_session_factory() as session:
        async with session.begin():
            print("=" * 60)
            print("  DATABASE SEEDING SCRIPT")
            print("  Populating data required by all Interview Agents")
            print("=" * 60)
            print()

            await clean_old_data(session)

            student_id = await seed_user(session)
            await seed_profile(session, student_id)
            await seed_skills(session, student_id)
            session_id = await seed_session(session, student_id)

            # Note: InterviewMemory, Question, Answer, AnswerScore, InterviewReport
            # are all CREATED by the agents during the interview flow.
            # We don't need to seed them — the agents create them.

            print()
            print("=" * 60)
            print("  SEEDING COMPLETE!")
            print(f"  Student ID : {student_id}")
            print(f"  Session ID : {session_id}")
            print("=" * 60)
            print()
            print("Data created for agents:")
            print("  ✓ User (name, email, role)")
            print("  ✓ StudentProfile (resume_text, portfolio_text, experience_years)")
            print("  ✓ Skills (12 skills with levels)")
            print("  ✓ InterviewSession (job_role, status, difficulty)")
            print()
            print("Data that agents CREATE during interview:")
            print("  → InterviewMemory (memory_agent)")
            print("  → Question (orchestrator)")
            print("  → Answer + AnswerScore (answer_evaluator)")
            print("  → InterviewReport (feedback_agent)")


if __name__ == "__main__":
    asyncio.run(seed_all())
