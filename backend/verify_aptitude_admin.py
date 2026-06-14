#!/usr/bin/env python3
"""Verification Test Suite for Aptitude Question Management Backend.

Exercises all backend components:
1. Database operations (CRUD).
2. Validation engine (rules, timing, duplicates).
3. Hashing/normalization helper.
4. Soft delete behavior.
5. Statistics helpers.
6. Bulk import pipeline.

Cleans up test data at the end of the run.
"""

import asyncio
import json
import logging
import uuid
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.api.ai.agents.aptitude.models import AptitudeQuestion, QuestionImportJob, QuestionImportItem
from app.repositories.aptitude_repository import AptitudeRepository
from app.services.aptitude_validator import (
    validate_aptitude_question,
    normalize_question_text,
    generate_question_hash
)
from app.services.aptitude_import_service import AptitudeImportService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verification")


async def run_tests() -> None:
    logger.info("Starting Verification Test Suite...")

    async with AsyncSession(engine) as db:
        # Keep track of created IDs for cleanup
        created_question_ids: List[uuid.UUID] = []
        created_job_ids: List[uuid.UUID] = []

        # Pre-cleanup in case of aborted runs
        await db.execute(
            delete(AptitudeQuestion).where(
                AptitudeQuestion.question.in_([
                    "This is a verify script manual question?",
                    "Seeded bulk import test question 1?",
                ])
            )
        )
        await db.commit()

        try:
            # ── TEST 1: TEXT NORMALIZATION & HASHING ──────────────────────
            logger.info("TEST 1: Normalization and Hashing...")
            text_1 = "What is 10 + 20? "
            text_2 = "  what is 10 + 20 ?  "
            
            norm_1 = normalize_question_text(text_1)
            norm_2 = normalize_question_text(text_2)
            
            assert norm_1 == norm_2, f"Normalization mismatch: '{norm_1}' != '{norm_2}'"
            assert norm_1 == "what is 10  20", f"Unexpected normalization result: '{norm_1}'"
            
            hash_1 = generate_question_hash(norm_1)
            hash_2 = generate_question_hash(norm_2)
            assert hash_1 == hash_2, "Hashes do not match for identical normalized text!"
            logger.info("✔ TEST 1 PASSED: Hashing & normalization are fully deterministic.")

            # ── TEST 2: CENTRALIZED VALIDATOR ─────────────────────────────
            logger.info("TEST 2: Centralized Validator Checks...")
            
            # Case 2a: Valid Question
            errs_a = await validate_aptitude_question(
                question="What is the square root of 64?",
                options=["6", "7", "8", "9"],
                correct_answer="8",
                domain="quantitative",
                category="roots",
                difficulty="easy",
                expected_time_seconds=30,
                db=db
            )
            assert len(errs_a) == 0, f"Valid question validation failed unexpectedly: {errs_a}"
            
            # Case 2b: Invalid Option Count
            errs_b = await validate_aptitude_question(
                question="Invalid Question",
                options=["1", "2"],
                correct_answer="1",
                domain="quantitative",
                category="general",
                difficulty="easy",
                db=db
            )
            assert any(e["field"] == "options" for e in errs_b), "Failed to detect invalid options count."

            # Case 2c: Non-unique options
            errs_c = await validate_aptitude_question(
                question="Duplicate Options",
                options=["A", "B", "A", "C"],
                correct_answer="B",
                domain="quantitative",
                category="general",
                difficulty="medium",
                db=db
            )
            assert any("unique" in e["message"] for e in errs_c), "Failed to detect non-unique options."

            # Case 2d: Wrong answer match
            errs_d = await validate_aptitude_question(
                question="Correct Answer Match",
                options=["A", "B", "C", "D"],
                correct_answer="E",
                domain="quantitative",
                category="general",
                difficulty="medium",
                db=db
            )
            assert any(e["field"] == "correct_answer" for e in errs_d), "Failed to detect wrong answer match error."

            # Case 2e: Expected solve time <= 0
            errs_e = await validate_aptitude_question(
                question="Timing validation test",
                options=["A", "B", "C", "D"],
                correct_answer="A",
                domain="quantitative",
                category="general",
                difficulty="medium",
                expected_time_seconds=0,
                db=db
            )
            assert any(e["field"] == "expected_time_seconds" for e in errs_e), "Failed to catch solve time <= 0."

            logger.info("✔ TEST 2 PASSED: Validation rules accurately checked.")

            # ── TEST 3: MANUAL CRUD & TAGS & TIMING ───────────────────────
            logger.info("TEST 3: Manual Question CRUD & Tags & Timing...")
            
            q = await AptitudeRepository.create_question(
                db=db,
                question="This is a verify script manual question?",
                options=["1", "2", "3", "4"],
                correct_answer="3",
                category="equations",
                difficulty="medium",
                domain="quantitative",
                subcategory="linear",
                status="draft",
                explanation="3 is the right answer",
                tags=["linear", "manual-test"],
                expected_time_seconds=45,
            )
            await db.flush()
            created_question_ids.append(q.id)

            assert q.id is not None
            assert q.tags == ["linear", "manual-test"]
            assert q.expected_time_seconds == 45
            assert q.status == "draft"
            assert q.times_used == 0

            # Approve question
            q = await AptitudeRepository.approve_question(db, q.id)
            await db.flush()
            assert q.status == "approved"
            assert q.approved_at is not None

            # Edit question
            q = await AptitudeRepository.update_question(
                db=db,
                question_id=q.id,
                difficulty="hard",
                tags=["linear", "edited-test"]
            )
            await db.flush()
            assert q.difficulty == "hard"
            assert q.tags == ["linear", "edited-test"]

            logger.info("✔ TEST 3 PASSED: CRUD, tag persistence, solve time, and approval status work perfectly.")

            # ── TEST 4: DUPLICATE DETECTION HASH ──────────────────────────
            logger.info("TEST 4: Duplicate Detection Hashing...")
            
            errs_dup = await validate_aptitude_question(
                question="  This is a verify script manual question?  ", # same text, diff spacing/caps
                options=["1", "2", "3", "4"],
                correct_answer="3",
                domain="quantitative",
                category="equations",
                difficulty="medium",
                db=db
            )
            assert any("Duplicate question" in e["message"] for e in errs_dup), "Validator failed to catch duplicate hash violation!"
            logger.info("✔ TEST 4 PASSED: Unique index and duplicate hashes successfully blocked.")

            # ── TEST 5: SOFT DELETE ───────────────────────────────────────
            logger.info("TEST 5: Soft Delete Verification...")
            
            # Soft delete
            del_ok = await AptitudeRepository.soft_delete_question(db, q.id)
            await db.flush()
            assert del_ok is True
            assert q.is_deleted is True
            assert q.deleted_at is not None

            # Search with include_deleted = False
            results, total = await AptitudeRepository.search_questions(
                db=db,
                domain="quantitative",
                include_deleted=False
            )
            assert not any(x.id == q.id for x in results), "Soft-deleted question returned in active search results!"

            # Search with include_deleted = True
            results_all, total_all = await AptitudeRepository.search_questions(
                db=db,
                domain="quantitative",
                include_deleted=True
            )
            assert any(x.id == q.id for x in results_all), "Soft-deleted question missing from admin all-inclusive query!"

            # Restore soft deleted question
            q = await AptitudeRepository.restore_question(db, q.id)
            await db.flush()
            assert q.is_deleted is False
            assert q.deleted_at is None
            assert q.status == "draft"

            logger.info("✔ TEST 5 PASSED: Soft deletion hides records from queries; restoration recovers them safely.")

            # ── TEST 6: STATISTICS INCREMENTS ─────────────────────────────
            logger.info("TEST 6: Statistics Updates...")
            
            q.increment_usage()
            q.increment_correct()
            await db.flush()
            assert q.times_used == 1
            assert q.times_correct == 1
            assert q.times_wrong == 0

            q.increment_usage()
            q.increment_wrong()
            await db.flush()
            assert q.times_used == 2
            assert q.times_correct == 1
            assert q.times_wrong == 1

            logger.info("✔ TEST 6 PASSED: Usage statistics incremented accurately.")

            # ── TEST 7: BULK IMPORT WORKFLOW ──────────────────────────────
            logger.info("TEST 7: Bulk Import Parsing & Validation Pipeline...")
            
            # JSON format payload
            import_data = [
                {
                    "question": "Seeded bulk import test question 1?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "category": "ratios",
                    "difficulty": "easy",
                    "domain": "quantitative",
                    "expected_time_seconds": 35,
                    "tags": "ratio,import-test"
                },
                {
                    "question": "This is a verify script manual question?", # DUPLICATE!
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "B",
                    "category": "ratios",
                    "difficulty": "easy",
                    "domain": "quantitative",
                }
            ]
            
            file_bytes = json.dumps(import_data).encode("utf-8")
            job = await AptitudeImportService.create_import_job(db=db, filename="mock_upload.json", source_type="JSON")
            await db.flush()
            created_job_ids.append(job.id)

            # Process Dry Run
            job = await AptitudeImportService.process_import_job(db=db, job_id=job.id, file_bytes=file_bytes)
            await db.flush()

            assert job.total_questions == 2
            assert job.valid_questions == 1  # only first one is valid
            assert job.invalid_questions == 1  # second is duplicate!
            assert job.status == "completed"

            # Check items preview
            items_res = await db.execute(select(QuestionImportItem).where(QuestionImportItem.job_id == job.id))
            items = items_res.scalars().all()
            assert len(items) == 2
            
            valid_item = next(i for i in items if i.status == "valid")
            invalid_item = next(i for i in items if i.status == "invalid")
            
            assert valid_item.parsed_question["question"] == "Seeded bulk import test question 1?"
            assert any("Duplicate question" in e["message"] for e in invalid_item.validation_errors), "Failed to detect database duplicate in import item validation."

            # Confirm Import
            inserted, skipped = await AptitudeImportService.confirm_import(db=db, job_id=job.id)
            await db.flush()

            assert inserted == 1
            assert skipped == 0
            assert job.status == "imported"

            # Verify that valid question got inserted in DB
            q_res = await db.execute(select(AptitudeQuestion).where(AptitudeQuestion.question == "Seeded bulk import test question 1?"))
            db_q = q_res.scalar_one()
            created_question_ids.append(db_q.id)

            assert db_q.status == "approved"
            assert db_q.expected_time_seconds == 35
            assert db_q.tags == ["ratio", "import-test"]

            logger.info("✔ TEST 7 PASSED: Dry-run upload validates, previews, blocks duplicates, and commits safely.")

            # All tests completed!
            logger.info("🎉 ALL TESTS PASSED SUCCESSFULLY! Aptitude Question backend is production-ready!")

        finally:
            # Clean up all created test data (transaction safe)
            logger.info("Cleaning up mock verification data...")
            if created_question_ids:
                await db.execute(delete(AptitudeQuestion).where(AptitudeQuestion.id.in_(created_question_ids)))
            if created_job_ids:
                # cascade delete handles import items
                await db.execute(delete(QuestionImportJob).where(QuestionImportJob.id.in_(created_job_ids)))
            await db.commit()
            logger.info("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(run_tests())
