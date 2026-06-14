"""
CUDAS Application Entry Point.
Includes AI agent routes (preserved) and new auth/RBAC routes.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.core.database import engine, Base, async_session_factory

# ── Router Imports ────────────────────────────────────────────────────────
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.college import router as college_router
from app.routers.company import router as company_router
from app.routers.csv_upload import router as csv_router
from app.routers.certificate import router as certificate_router
from app.routers.jobs import router as jobs_router
from app.routers.pipeline import router as pipeline_router
from app.routers.recruiter import router as recruiter_router
from app.routers.messages import router as messages_router
from app.routers.rag import router as rag_router
from app.routers.verification import router as verification_router
from app.routers.projects import router as projects_router
from app.routers.exam import router as exam_router
from app.routers.subject import router as subject_router
from app.routers.mentor import router as mentor_router
from app.api.ai.agents.interview.router import router as ai_interview_router
from app.api.ai.agents.aptitude.router import router as ai_aptitude_router
from app.routers.aptitude_admin import admin_router as aptitude_admin_router, public_taxonomy_router

# Import all models so they are registered with Base.metadata
import app.models  # noqa: F401
import app.api.ai.agents.aptitude.models  # noqa: F401

# Embedding model warm-up
from app.services.embedding_service import warm_up_embedding_model  # noqa: E402

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:

        # STEP 1: CREATE TABLES FIRST
        await conn.run_sync(Base.metadata.create_all)

        # STEP 2: THEN RUN ALTERS

        # auth_users
        await conn.execute(
            text("""
                ALTER TABLE auth_users
                    ADD COLUMN IF NOT EXISTS department VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS semester INTEGER,
                    ADD COLUMN IF NOT EXISTS enrollment_number VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS skills JSONB,
                    ADD COLUMN IF NOT EXISTS resume_url VARCHAR(512);
            """)
        )

        # student_profiles
        await conn.execute(
            text("""
                ALTER TABLE student_profiles
                    ADD COLUMN IF NOT EXISTS has_projects BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS project_summary TEXT;
            """)
        )

        # interview_sessions
        await conn.execute(
            text("""
                ALTER TABLE interview_sessions
                    ADD COLUMN IF NOT EXISTS mode VARCHAR(50) DEFAULT 'basic';
            """)
        )

        # certificates
        await conn.execute(
            text("""
                ALTER TABLE certificates
                    ADD COLUMN IF NOT EXISTS file_path VARCHAR(1024);
            """)
        )

        await conn.execute(
            text("""
                ALTER TABLE certificates
                    ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
            """)
        )

        # constraint
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uq_certificates_file_hash'
                    ) THEN
                        EXECUTE 'ALTER TABLE certificates ADD CONSTRAINT uq_certificates_file_hash UNIQUE (file_hash)';
                    END IF;
                END $$;
            """)
        )

        # enrollment_number unique constraint
        await conn.execute(
            text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'uq_users_enrollment_number'
                    ) THEN
                        EXECUTE 'ALTER TABLE auth_users ADD CONSTRAINT uq_users_enrollment_number UNIQUE (enrollment_number)';
                    END IF;
                END $$;
            """)
        )

        # ── Messages table: role-based messaging columns ──
        await conn.execute(
            text("""
                ALTER TABLE messages
                    ADD COLUMN IF NOT EXISTS sender_role VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS receiver_role VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS receiver_ids JSONB,
                    ADD COLUMN IF NOT EXISTS semester_id INTEGER,
                    ADD COLUMN IF NOT EXISTS cc_ids JSONB;
            """)
        )

        # Make recipient_id nullable (bulk messages don't have a single recipient)
        await conn.execute(
            text("""
                ALTER TABLE messages
                    ALTER COLUMN recipient_id DROP NOT NULL;
            """)
        )

        # Drop the old message_type enum constraint if it exists and use varchar
        await conn.execute(
            text("""
                ALTER TABLE messages
                    ALTER COLUMN message_type TYPE VARCHAR(50) USING message_type::VARCHAR(50);
            """)
        )

        # ── Notifications table: starring and sender_role ──
        await conn.execute(
            text("""
                ALTER TABLE notifications
                    ADD COLUMN IF NOT EXISTS is_starred BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS sender_role VARCHAR(50);
            """)
        )

        # Drop the old notification_type enum constraint and use varchar
        await conn.execute(
            text("""
                ALTER TABLE notifications
                    ALTER COLUMN notification_type TYPE VARCHAR(50) USING notification_type::VARCHAR(50);
            """)
        )

        # extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Warning: {e}")

        # ── Aptitude sessions: question sequence column ──
        await conn.execute(
            text("""
                ALTER TABLE aptitude_sessions
                    ADD COLUMN IF NOT EXISTS question_sequence JSONB DEFAULT '[]'::jsonb;
            """)
        )

        # ── Aptitude questions: admin management columns ──
        await conn.execute(
            text("""
                ALTER TABLE aptitude_questions
                    ADD COLUMN IF NOT EXISTS domain VARCHAR(64),
                    ADD COLUMN IF NOT EXISTS subcategory VARCHAR(64),
                    ADD COLUMN IF NOT EXISTS status VARCHAR(16) DEFAULT 'draft',
                    ADD COLUMN IF NOT EXISTS created_by UUID,
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW(),
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
                    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
                    ADD COLUMN IF NOT EXISTS approved_by UUID,
                    ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
                    ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb,
                    ADD COLUMN IF NOT EXISTS expected_time_seconds INTEGER,
                    ADD COLUMN IF NOT EXISTS normalized_question_hash VARCHAR(64),
                    ADD COLUMN IF NOT EXISTS times_used INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS times_correct INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS times_wrong INTEGER DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
            """)
        )

        # Backfill status & active flags for existing questions
        await conn.execute(
            text("""
                UPDATE aptitude_questions
                SET status = 'approved'
                WHERE status IS NULL OR status = 'draft';
            """)
        )

        # Backfill hashes for existing questions that don't have a hash
        res = await conn.execute(
            text("SELECT id, question FROM aptitude_questions WHERE normalized_question_hash IS NULL")
        )
        to_update = res.all()
        if to_update:
            from app.services.aptitude_validator import normalize_question_text, generate_question_hash
            for q_id, q_text in to_update:
                norm = normalize_question_text(q_text)
                q_hash = generate_question_hash(norm)
                await conn.execute(
                    text("UPDATE aptitude_questions SET normalized_question_hash = :hash WHERE id = :id"),
                    {"hash": q_hash, "id": q_id}
                )

    # Seed aptitude questions (best-effort; only if DB table is empty)
    try:
        from app.api.ai.agents.aptitude.service import seed_questions_if_empty

        json_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "api",
            "ai",
            "agents",
            "aptitude",
            "aptitude_questions.json",
        )

        async with async_session_factory() as session:
            inserted = await seed_questions_if_empty(db=session, json_path=json_path)
            if inserted:
                await session.commit()
    except Exception as exc:
        print(f"Warning: Aptitude seeding skipped due to error: {exc}")

    # ── Warm up the embedding model once at startup ──────────────────────
    # The model is heavy (~90 MB). Loading it here ensures it is ready in
    # memory before the first interview request and never reloaded again.
    try:
        import logging as _logging
        _log = _logging.getLogger(__name__)
        _log.info("[RAG] Pre-loading embedding model at server startup…")
        warm_up_embedding_model()
        _log.info("[RAG] Embedding model warm-up complete")
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "[RAG] Embedding model warm-up failed (will load on first request): %s", exc
        )

    yield


app = FastAPI(
    title="CUDAS — AI Agents Powered Education Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files: certificate uploads ─────────────────────────────────────

CERT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "certificate")
os.makedirs(CERT_DIR, exist_ok=True)
app.mount("/certificates", StaticFiles(directory=CERT_DIR), name="certificates")

# ── Register All Routers ─────────────────────────────────────────────────

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(aptitude_admin_router)
app.include_router(public_taxonomy_router)
app.include_router(college_router)
app.include_router(company_router)
app.include_router(csv_router)
app.include_router(certificate_router)
app.include_router(jobs_router)
app.include_router(pipeline_router)
app.include_router(recruiter_router)
app.include_router(messages_router)
app.include_router(ai_interview_router, prefix="/ai/interview", tags=["AI Interview"])
app.include_router(ai_aptitude_router, prefix="/ai/aptitude", tags=["AI Aptitude"])
app.include_router(rag_router)
app.include_router(verification_router)
app.include_router(projects_router)
app.include_router(exam_router)
app.include_router(subject_router, prefix="/api")
app.include_router(mentor_router, prefix="/api")