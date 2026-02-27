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
    """Create all tables on startup (for new auth tables)."""
    async with engine.begin() as conn:
        # Certificate domain: ensure existing DB has the required columns before
        # we create certificate_blocks (FK -> certificates.file_hash).
        # This is intentionally limited to certificate schema only.
        await conn.execute(
            text(
                """
                ALTER TABLE certificates
                    ADD COLUMN IF NOT EXISTS file_path VARCHAR(1024);
                """
            )
        )
        await conn.execute(
            text(
                """
                ALTER TABLE certificates
                    ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
                """
            )
        )
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM   pg_constraint
                        WHERE  conname = 'uq_certificates_file_hash'
                    ) THEN
                        IF EXISTS (
                            SELECT 1
                            FROM   pg_indexes
                            WHERE  schemaname = current_schema()
                            AND    indexname = 'uq_certificates_file_hash'
                        ) THEN
                            EXECUTE 'DROP INDEX uq_certificates_file_hash';
                        END IF;

                        EXECUTE 'ALTER TABLE certificates ADD CONSTRAINT uq_certificates_file_hash UNIQUE (file_hash)';
                    END IF;
                END $$;
                """
            )
        )
        await conn.run_sync(Base.metadata.create_all)
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

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(college_router)
app.include_router(company_router)
app.include_router(csv_router)
app.include_router(certificate_router)