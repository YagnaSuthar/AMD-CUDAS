import csv
import io
import json
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set

import pandas as pd
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.aptitude.models import QuestionImportJob, QuestionImportItem
from app.repositories.aptitude_repository import AptitudeRepository
from app.services.aptitude_validator import (
    validate_aptitude_question,
    normalize_question_text,
    generate_question_hash
)

logger = logging.getLogger(__name__)


class AptitudeImportService:
    """
    Service layer coordinating bulk import jobs, file parsers, validations, previews, and imports.
    """

    @staticmethod
    def _parse_options(row: Dict[str, Any]) -> List[str]:
        """Helper to parse options from a dictionary representing a file row."""
        # 1. Look for options in separate columns: option_1/a, option_2/b, option_3/c, option_4/d
        opts = []
        for key in ["option_1", "option_a", "option1", "opt_1", "opt1"]:
            if row.get(key) is not None:
                opts.append(str(row[key]).strip())
                break
        for key in ["option_2", "option_b", "option2", "opt_2", "opt2"]:
            if row.get(key) is not None:
                opts.append(str(row[key]).strip())
                break
        for key in ["option_3", "option_c", "option3", "opt_3", "opt3"]:
            if row.get(key) is not None:
                opts.append(str(row[key]).strip())
                break
        for key in ["option_4", "option_d", "option4", "opt_4", "opt4"]:
            if row.get(key) is not None:
                opts.append(str(row[key]).strip())
                break

        if len(opts) == 4:
            return opts

        # 2. Look for options as an array or comma-separated string
        options_val = row.get("options")
        if options_val is not None:
            if isinstance(options_val, list):
                return [str(o).strip() for o in options_val]
            if isinstance(options_val, str):
                cleaned = options_val.strip()
                if cleaned.startswith("[") and cleaned.endswith("]"):
                    try:
                        parsed = json.loads(cleaned)
                        if isinstance(parsed, list):
                            return [str(o).strip() for o in parsed]
                    except Exception:
                        pass
                # Comma separated
                return [o.strip() for o in cleaned.split(",") if o.strip()]

        return []

    @staticmethod
    def _parse_tags(row: Dict[str, Any]) -> List[str]:
        """Helper to parse tags array or string."""
        tags_val = row.get("tags")
        if tags_val is not None:
            if isinstance(tags_val, list):
                return [str(t).strip() for t in tags_val]
            if isinstance(tags_val, str):
                cleaned = tags_val.strip()
                if cleaned.startswith("[") and cleaned.endswith("]"):
                    try:
                        parsed = json.loads(cleaned)
                        if isinstance(parsed, list):
                            return [str(t).strip() for t in parsed]
                    except Exception:
                        pass
                return [t.strip() for t in cleaned.split(",") if t.strip()]
        return []

    @staticmethod
    def _parse_integer(val: Any) -> Optional[int]:
        if val is None or str(val).strip() == "":
            return None
        try:
            # handle floats like 10.0
            return int(float(val))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_pdf_text(full_text: str) -> List[Dict[str, Any]]:
        """
        Parse raw PDF text into a list of question dictionaries.

        Supports multiple common MCQ formats:
          - Numbered questions: Q1. / Q2. / Q 1. / 1. / 1)
          - Labeled questions: Question: / Question 1:
          - Options: A. / B. / C. / D.  or  A) / B) / C) / D)  or  a. / b. / c. / d.
          - Answer: Answer: X  or  Correct Answer: X
          - Metadata: Explanation: / Category: / Difficulty: / Domain:
        """
        records: List[Dict[str, Any]] = []

        if not full_text or not full_text.strip():
            return records

        # ── Step 1: Split the full text into per-question blocks ─────────
        # Pattern matches: Q1. / Q2. / Q 1. / Q.1 / Q1) / 1. / 1) / Question: / Question 1:
        # We use a regex that captures common numbered-question headers.
        split_pattern = re.compile(
            r'(?:^|\n)\s*'
            r'(?:'
            r'Q\.?\s*\d+[\.):]'     # Q1. Q1) Q1: Q.1 Q 1.
            r'|Q\d+[\.):]'           # Q1. Q1) Q1:
            r'|Question\s*\d*\s*[\.:)]'  # Question: Question 1: Question 1.
            r'|(?<=\n)\d{1,3}[\.):]'     # 1. 1) 1: (at start of line)
            r')',
            re.IGNORECASE | re.MULTILINE,
        )

        # Find all split positions
        matches = list(split_pattern.finditer(full_text))

        if not matches:
            # Fallback: try splitting by "Question:" exactly (legacy)
            legacy_blocks = full_text.split("Question:")
            if len(legacy_blocks) > 1:
                for b in legacy_blocks[1:]:
                    block_text = b.strip()
                    if block_text:
                        parsed = AptitudeImportService._parse_single_question_block(block_text)
                        if parsed:
                            records.append(parsed)
            return records

        # Extract text blocks between consecutive matches
        blocks: List[str] = []
        for i, m in enumerate(matches):
            start = m.end()  # text after the header
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            block_text = full_text[start:end].strip()
            if block_text:
                blocks.append(block_text)

        logger.info("PDF splitter found %d question block(s)", len(blocks))

        for idx, block in enumerate(blocks):
            parsed = AptitudeImportService._parse_single_question_block(block)
            if parsed:
                records.append(parsed)
            else:
                logger.warning("PDF block %d could not be parsed into a valid question", idx + 1)

        return records

    @staticmethod
    def _parse_single_question_block(block: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single question block into a structured dict.
        Expects the block text to start with the question text,
        followed by options (A./B./C./D.), answer, and optional metadata.
        """
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            return None

        # ── Regex patterns for options and metadata ──────────────────────
        option_pattern = re.compile(
            r'^(?:'
            r'([A-Da-d])\s*[\.):]'   # A. / A) / A: / a. / a)
            r'|([A-Da-d])\s*\)'      # A)  (already covered but explicit)
            r')\s*(.*)',
            re.IGNORECASE,
        )
        answer_pattern = re.compile(
            r'^(?:Correct\s+Answer|Answer)\s*[:\-]\s*(.*)',
            re.IGNORECASE,
        )
        explanation_pattern = re.compile(r'^Explanation\s*[:\-]\s*(.*)', re.IGNORECASE)
        category_pattern = re.compile(r'^Category\s*[:\-]\s*(.*)', re.IGNORECASE)
        difficulty_pattern = re.compile(r'^Difficulty\s*[:\-]\s*(.*)', re.IGNORECASE)
        domain_pattern = re.compile(r'^Domain\s*[:\-]\s*(.*)', re.IGNORECASE)

        # ── Walk through lines to classify them ──────────────────────────
        question_lines: List[str] = []
        options: Dict[str, str] = {}  # keyed by A/B/C/D
        answer = ""
        explanation = ""
        category = "general"
        difficulty = "medium"
        domain = "quantitative"
        current_option_key: Optional[str] = None
        reading_question = True  # True until we hit the first option

        for line in lines:
            # Check answer first (before options, since "A." could conflict)
            ans_match = answer_pattern.match(line)
            if ans_match:
                answer = ans_match.group(1).strip()
                reading_question = False
                current_option_key = None
                continue

            # Check metadata
            expl_match = explanation_pattern.match(line)
            if expl_match:
                explanation = expl_match.group(1).strip()
                reading_question = False
                current_option_key = None
                continue

            cat_match = category_pattern.match(line)
            if cat_match:
                category = cat_match.group(1).strip()
                reading_question = False
                current_option_key = None
                continue

            diff_match = difficulty_pattern.match(line)
            if diff_match:
                difficulty = diff_match.group(1).strip().lower()
                reading_question = False
                current_option_key = None
                continue

            dom_match = domain_pattern.match(line)
            if dom_match:
                domain = dom_match.group(1).strip().lower()
                reading_question = False
                current_option_key = None
                continue

            # Check option
            opt_match = option_pattern.match(line)
            if opt_match:
                key = (opt_match.group(1) or opt_match.group(2)).upper()
                text = opt_match.group(3).strip()
                options[key] = text
                reading_question = False
                current_option_key = key
                continue

            # Continuation line: could be a multi-line option or multi-line question
            if current_option_key and not reading_question:
                # Append to last option
                options[current_option_key] += " " + line
            elif reading_question:
                question_lines.append(line)

        # ── Assemble the question text ──────────────────────────────────
        question_text = " ".join(question_lines).strip()
        if not question_text:
            return None

        # ── Build ordered option list (A, B, C, D) ──────────────────────
        ordered_options = []
        for key in ["A", "B", "C", "D"]:
            if key in options:
                ordered_options.append(options[key])

        # ── Resolve correct_answer to the full option text ──────────────
        resolved_answer = answer
        if answer:
            clean_ans = answer.strip().rstrip(".").strip()
            # If the answer is just a letter like "A" or "B", resolve to full text
            if clean_ans.upper() in options:
                resolved_answer = options[clean_ans.upper()]
            else:
                # Check if the answer text matches any option (exact or starts with)
                for opt_text in ordered_options:
                    if opt_text.lower() == clean_ans.lower():
                        resolved_answer = opt_text
                        break
                else:
                    # Keep the raw answer — validator will catch mismatches
                    resolved_answer = clean_ans

        if not resolved_answer:
            return None

        return {
            "question": question_text,
            "options": ordered_options if len(ordered_options) == 4 else [],
            "correct_answer": resolved_answer,
            "explanation": explanation,
            "category": category,
            "difficulty": difficulty,
            "domain": domain,
        }

    @staticmethod
    async def create_import_job(
        db: AsyncSession, *, filename: str, source_type: str
    ) -> QuestionImportJob:
        job = QuestionImportJob(
            filename=filename,
            source_type=source_type.upper(),
            status="pending",
            total_questions=0,
            valid_questions=0,
            invalid_questions=0,
            created_at=datetime.utcnow(),
        )
        db.add(job)
        await db.flush()
        return job

    @staticmethod
    async def process_import_job(
        db: AsyncSession, job_id: uuid.UUID, file_bytes: bytes
    ) -> QuestionImportJob:
        # Fetch job
        res = await db.execute(select(QuestionImportJob).where(QuestionImportJob.id == job_id))
        job = res.scalar_one_or_none()
        if not job:
            raise ValueError(f"Import job {job_id} not found")

        raw_records: List[Dict[str, Any]] = []

        try:
            # 1. Parse records depending on source_type
            if job.source_type == "JSON":
                parsed_json = json.loads(file_bytes.decode("utf-8"))
                if isinstance(parsed_json, list):
                    raw_records = parsed_json
                elif isinstance(parsed_json, dict) and "questions" in parsed_json:
                    raw_records = parsed_json["questions"]
                else:
                    raise ValueError("JSON must be a list of questions or a dict with a 'questions' key")

            elif job.source_type == "CSV":
                stream = io.StringIO(file_bytes.decode("utf-8"))
                reader = csv.DictReader(stream)
                raw_records = list(reader)

            elif job.source_type == "XLSX":
                excel_file = io.BytesIO(file_bytes)
                df = pd.read_excel(excel_file)
                # replace NaN with None
                df = df.where(pd.notnull(df), None)
                raw_records = df.to_dict(orient="records")

            elif job.source_type == "PDF":
                # ── PDF Extraction ──────────────────────────────────────
                pdf_file = io.BytesIO(file_bytes)
                reader = PdfReader(pdf_file)
                full_text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"

                logger.info("PDF raw extracted text length: %d chars", len(full_text))
                logger.debug("PDF raw text (first 2000 chars):\n%s", full_text[:2000])

                raw_records = AptitudeImportService._parse_pdf_text(full_text)

                logger.info("PDF parser produced %d question record(s)", len(raw_records))
                for i, rec in enumerate(raw_records):
                    logger.debug(
                        "PDF parsed Q%d: question=%r, options=%r, answer=%r",
                        i + 1,
                        (rec.get("question") or "")[:80],
                        rec.get("options"),
                        rec.get("correct_answer"),
                    )

                # If no structured records found, create a dummy invalid item
                # so the admin can review the parsed text
                if not raw_records:
                    raw_records.append({
                        "question": "Failed to parse structured PDF format.",
                        "error_details": (
                            "PDF extracted text didn't match any known question pattern "
                            "(Q1./Q2., Question:, etc.). "
                            "Extracted text preview: " + full_text[:500]
                        ),
                        "options": [],
                        "correct_answer": "",
                        "category": "general",
                        "difficulty": "medium",
                    })

            else:
                raise ValueError(f"Unsupported source type: {job.source_type}")

        except Exception as e:
            logger.exception("Error parsing import file")
            job.status = "failed"
            job.error_log = {"error": f"File parsing failed: {str(e)}"}
            job.completed_at = datetime.utcnow()
            await db.flush()
            return job

        # 2. Validate and store preview items
        job.total_questions = len(raw_records)
        valid_count = 0
        invalid_count = 0

        # Keep track of hashes processed in THIS batch to check for batch duplicates
        batch_hashes: Set[str] = set()

        for idx, rec in enumerate(raw_records):
            # Parse fields out of record
            q_text = str(rec.get("question") or rec.get("question_text") or "").strip()
            options = AptitudeImportService._parse_options(rec)
            correct_answer = str(rec.get("correct_answer") or rec.get("correct") or "").strip()
            category = str(rec.get("category") or "general").strip()
            difficulty = str(rec.get("difficulty") or "easy").strip().lower()
            domain = str(rec.get("domain") or "").strip().lower() or None
            subcategory = str(rec.get("subcategory") or "").strip() or None
            explanation = str(rec.get("explanation") or "").strip() or None
            tags = AptitudeImportService._parse_tags(rec)
            expected_time = AptitudeImportService._parse_integer(rec.get("expected_time_seconds") or rec.get("expected_time"))

            # Build parsed object for storing in DB
            parsed_q = {
                "question": q_text,
                "options": options,
                "correct_answer": correct_answer,
                "category": category,
                "difficulty": difficulty,
                "domain": domain,
                "subcategory": subcategory,
                "explanation": explanation,
                "tags": tags,
                "expected_time_seconds": expected_time,
                "status": "draft",
                "source": "imported",
            }

            # Run validator (checks DB duplicates + batch duplicates)
            validation_errors = await validate_aptitude_question(
                question=q_text,
                options=options,
                correct_answer=correct_answer,
                domain=domain,
                category=category,
                difficulty=difficulty,
                expected_time_seconds=expected_time,
                db=db,
                current_batch_hashes=batch_hashes,
            )

            # Record batch hash to prevent later duplicate in this batch
            if q_text:
                norm = normalize_question_text(q_text)
                batch_hashes.add(generate_question_hash(norm))

            is_valid = len(validation_errors) == 0
            item_status = "valid" if is_valid else "invalid"

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            # Save as Import Item preview
            item = QuestionImportItem(
                job_id=job.id,
                raw_data=rec,
                parsed_question=parsed_q,
                validation_errors=validation_errors if validation_errors else None,
                status=item_status,
            )
            db.add(item)

        # Update job stats
        job.valid_questions = valid_count
        job.invalid_questions = invalid_count
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        await db.flush()
        return job

    @staticmethod
    async def confirm_import(
        db: AsyncSession, job_id: uuid.UUID, confirmed_by: Optional[uuid.UUID] = None
    ) -> Tuple[int, int]:
        """
        Confirms import job by inserting only valid, non-duplicate questions.
        Returns Tuple[inserted_count, skipped_count].
        """
        # Fetch job
        res = await db.execute(
            select(QuestionImportJob).where(
                QuestionImportJob.id == job_id,
                QuestionImportJob.status == "completed"
            )
        )
        job = res.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Active/Completed Import Job not found")

        # Fetch valid items
        items_res = await db.execute(
            select(QuestionImportItem).where(
                QuestionImportItem.job_id == job_id,
                QuestionImportItem.status == "valid"
            )
        )
        items = items_res.scalars().all()

        inserted_count = 0
        skipped_count = 0

        # Maintain double-check set of hashes we are introducing to prevent double-inserting within confirmation
        introduced_hashes: Set[str] = set()

        for item in items:
            pq = item.parsed_question
            if not pq:
                continue

            q_text = pq["question"]
            norm = normalize_question_text(q_text)
            q_hash = generate_question_hash(norm)

            # Extra safety check: verify the duplicate hasn't been added to DB in the meantime, 
            # and that it is not inside our current list of introduced questions
            if q_hash in introduced_hashes:
                skipped_count += 1
                item.status = "invalid"
                item.validation_errors = [{"field": "question", "message": "Duplicate conflict within confirmation"}]
                continue

            from app.api.ai.agents.aptitude.models import AptitudeQuestion
            stmt = select(AptitudeQuestion.id).where(AptitudeQuestion.normalized_question_hash == q_hash)
            existing_res = await db.execute(stmt)
            if existing_res.scalar_one_or_none() is not None:
                skipped_count += 1
                item.status = "invalid"
                item.validation_errors = [{"field": "question", "message": "Duplicate question already exists in DB"}]
                continue

            # Eligible for insertion! Mark status as approved as per workflow
            pq["status"] = "approved"

            await AptitudeRepository.create_question(
                db=db,
                question=pq["question"],
                options=pq["options"],
                correct_answer=pq["correct_answer"],
                category=pq["category"],
                difficulty=pq["difficulty"],
                domain=pq.get("domain"),
                subcategory=pq.get("subcategory"),
                status="approved",  # only approved questions can be used in tests!
                source="imported",
                explanation=pq.get("explanation"),
                tags=pq.get("tags"),
                expected_time_seconds=pq.get("expected_time_seconds"),
                created_by=confirmed_by,
            )

            # Record
            introduced_hashes.add(q_hash)
            item.status = "imported"
            inserted_count += 1

        # Mark job status
        job.status = "imported"
        await db.flush()

        return inserted_count, skipped_count
