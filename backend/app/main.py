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
from app.core.database import engine, Base

# Import all models so they are registered with Base.metadata
import app.models  # noqa: F401

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:

        # ✅ STEP 1: CREATE TABLES FIRST
        await conn.run_sync(Base.metadata.create_all)

        # ✅ STEP 2: THEN RUN ALTERS

        # auth_users
        await conn.execute(
            text("""
                ALTER TABLE auth_users
                    ADD COLUMN IF NOT EXISTS department VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS semester INTEGER,
                    ADD COLUMN IF NOT EXISTS roll_number VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS company_name VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS skills JSONB,
                    ADD COLUMN IF NOT EXISTS resume_url VARCHAR(512);
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

        # extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            print(f"Warning: {e}")

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

# ── Existing AI Routes (untouched) ───────────────────────────────────────

app.include_router(api_router)

# ── New Auth / RBAC Routes ────────────────────────────────────────────────

from app.routers.auth import router as auth_router  # noqa: E402
from app.routers.admin import router as admin_router  # noqa: E402
from app.routers.college import router as college_router  # noqa: E402
from app.routers.company import router as company_router  # noqa: E402
from app.routers.csv_upload import router as csv_router  # noqa: E402
from app.routers.certificate import router as certificate_router  # noqa: E402
from app.routers.jobs import router as jobs_router  # noqa: E402
from app.routers.pipeline import router as pipeline_router  # noqa: E402
from app.routers.recruiter import router as recruiter_router  # noqa: E402
from app.routers.messages import router as messages_router  # noqa: E402
from app.api.ai.agents.interview.router import router as ai_interview_router  # noqa: E402
from app.routers.rag import router as rag_router  # noqa: E402
from app.routers.verification import router as verification_router  # noqa: E402

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(college_router)
app.include_router(company_router)
app.include_router(csv_router)
app.include_router(certificate_router)
app.include_router(jobs_router)
app.include_router(pipeline_router)
app.include_router(recruiter_router)
app.include_router(messages_router)
app.include_router(ai_interview_router, prefix="/ai/interview", tags=["AI Interview"])
app.include_router(rag_router)
app.include_router(verification_router)