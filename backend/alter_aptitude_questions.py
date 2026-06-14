#!/usr/bin/env python3
"""Migration script: add Aptitude Question admin, timing, stats, tags, and soft-delete fields.

Adds:
- aptitude_questions.domain
- aptitude_questions.subcategory
- aptitude_questions.status
- aptitude_questions.created_by
- aptitude_questions.created_at
- aptitude_questions.updated_at
- aptitude_questions.approved_at
- aptitude_questions.approved_by
- aptitude_questions.is_active
- aptitude_questions.tags
- aptitude_questions.expected_time_seconds
- aptitude_questions.normalized_question_hash
- aptitude_questions.times_used
- aptitude_questions.times_correct
- aptitude_questions.times_wrong
- aptitude_questions.is_deleted
- aptitude_questions.deleted_at
- question_import_jobs table
- question_import_items table

Safe to run multiple times.
"""

import asyncio
import logging
from sqlalchemy import text

from app.core.database import engine
from app.api.ai.agents.aptitude.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migration")


async def main() -> None:
    logger.info("Starting schema updates...")
    async with engine.begin() as conn:
        # Step 1: Create all tables first (creates new import job tables)
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Metadata tables check/creation complete.")

        # Step 2: Add columns to aptitude_questions
        logger.info("Adding columns to aptitude_questions...")
        await conn.execute(
            text(
                """
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
                """
            )
        )
        logger.info("Columns altered successfully.")

        # Step 3: Backfill existing rows
        logger.info("Backfilling statuses for existing questions...")
        await conn.execute(
            text(
                """
                UPDATE aptitude_questions
                SET status = 'approved'
                WHERE status IS NULL OR status = 'draft';
                """
            )
        )

        logger.info("Backfilling hashes for existing questions...")
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
            logger.info("Backfilled %d question hashes.", len(to_update))
        else:
            logger.info("No questions needed hash backfilling.")

    logger.info("Migration script completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
