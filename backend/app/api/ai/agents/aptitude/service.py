import json
import logging
import os
import random
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.aptitude.models import AptitudeAttempt, AptitudeQuestion, AptitudeSession
from app.services.aptitude_validator import normalize_question_text, generate_question_hash

logger = logging.getLogger(__name__)


def _validate_question_record(q: AptitudeQuestion) -> None:
    options = q.options
    if not isinstance(options, list):
        raise ValueError("options must be a list")
    if len(options) != 4:
        raise ValueError("question must have exactly 4 options")
    opt_str = [str(x).strip() for x in options]
    if any(not x for x in opt_str):
        raise ValueError("options cannot be empty")
    if len(set(opt_str)) != 4:
        raise ValueError("options must be unique")
    if str(q.correct_answer).strip() not in opt_str:
        raise ValueError("correct_answer must match one of the options")


def generate_question_llm(*, category: Optional[str] = None) -> Dict[str, Any]:
    raise NotImplementedError("LLM generation is not implemented yet")


class AptitudeService:
    @staticmethod
    async def start_session(*, user_id: str, total_questions: int, category: Optional[str], db: AsyncSession) -> Dict[str, Any]:
        sess = AptitudeSession(
            user_id=str(user_id),
            total_questions=int(total_questions),
            current_index=0,
            score=0,
            used_question_ids=[],
            question_sequence=[],
            created_at=datetime.utcnow(),
            completed_at=None,
        )
        db.add(sess)
        await db.flush()

        # Precompute a balanced, randomized sequence once per session.
        # This prevents repetition, removes predictability, and makes /next deterministic.
        seq = await AptitudeService._build_question_sequence(
            total_questions=int(total_questions),
            category=category,
            db=db,
        )
        sess.question_sequence = [str(x) for x in seq]
        sess.current_index = 0
        sess.used_question_ids = []
        await db.flush()

        q = await AptitudeService.get_next_question(session_id=sess.id, user_id=str(user_id), db=db, category=category)
        return q

    @staticmethod
    async def _build_question_sequence(
        *,
        total_questions: int,
        category: Optional[str],
        db: AsyncSession,
    ) -> list[uuid.UUID]:
        # Target distribution ~33/33/33
        total = max(1, int(total_questions or 0))
        base = total // 3
        rem = total % 3
        targets = {"easy": base, "medium": base, "hard": base}
        for diff in ("easy", "medium", "hard"):
            if rem <= 0:
                break
            targets[diff] += 1
            rem -= 1

        base_where = [
            AptitudeQuestion.is_deleted == False,
            AptitudeQuestion.status == "approved",
            AptitudeQuestion.is_active == True,
        ]
        if category:
            base_where.append(AptitudeQuestion.category == category)

        async def _fetch_ids(diff: str) -> list[uuid.UUID]:
            # Prefer curated first, but fall back to any source.
            curated = await db.execute(
                select(AptitudeQuestion.id)
                .where(AptitudeQuestion.difficulty == diff, AptitudeQuestion.source == "curated", *base_where)
                .order_by(func.random())
                .limit(500)
            )
            curated_ids = list(curated.scalars().all() or [])

            any_res = await db.execute(
                select(AptitudeQuestion.id)
                .where(AptitudeQuestion.difficulty == diff, *base_where)
                .order_by(func.random())
                .limit(500)
            )
            any_ids = list(any_res.scalars().all() or [])

            seen: set[uuid.UUID] = set()
            out: list[uuid.UUID] = []
            for x in curated_ids + any_ids:
                if x in seen:
                    continue
                seen.add(x)
                out.append(x)
            return out

        easy_ids = await _fetch_ids("easy")
        medium_ids = await _fetch_ids("medium")
        hard_ids = await _fetch_ids("hard")

        random.shuffle(easy_ids)
        random.shuffle(medium_ids)
        random.shuffle(hard_ids)

        selected: list[uuid.UUID] = []
        selected.extend(easy_ids[: targets["easy"]])
        selected.extend(medium_ids[: targets["medium"]])
        selected.extend(hard_ids[: targets["hard"]])

        # If any bucket is short, fill from remaining pool of other difficulties.
        if len(selected) < total:
            already = set(selected)
            leftovers: list[uuid.UUID] = []
            leftovers.extend([x for x in easy_ids[targets["easy"] :] if x not in already])
            leftovers.extend([x for x in medium_ids[targets["medium"] :] if x not in already])
            leftovers.extend([x for x in hard_ids[targets["hard"] :] if x not in already])
            random.shuffle(leftovers)
            selected.extend(leftovers[: max(0, total - len(selected))])

        # If still short, do a final fallback: any difficulty.
        if len(selected) < total:
            already = set(selected)
            any_res = await db.execute(
                select(AptitudeQuestion.id)
                .where(*base_where)
                .order_by(func.random())
                .limit(1000)
            )
            any_ids = [x for x in (any_res.scalars().all() or []) if x not in already]
            random.shuffle(any_ids)
            selected.extend(any_ids[: max(0, total - len(selected))])

        # Final shuffle for unpredictability.
        selected = selected[:total]
        random.shuffle(selected)
        return selected

    @staticmethod
    async def _get_session_for_user(*, session_id: uuid.UUID, user_id: str, db: AsyncSession) -> AptitudeSession:
        res = await db.execute(
            select(AptitudeSession).where(AptitudeSession.id == session_id, AptitudeSession.user_id == str(user_id))
        )
        sess = res.scalar_one_or_none()
        if sess is None:
            raise HTTPException(status_code=404, detail="Aptitude session not found")
        return sess

    @staticmethod
    async def get_next_question(*, session_id: uuid.UUID, user_id: str, db: AsyncSession, category: Optional[str] = None) -> Dict[str, Any]:
        sess = await AptitudeService._get_session_for_user(session_id=session_id, user_id=user_id, db=db)
        if sess.completed_at is not None or sess.current_index >= sess.total_questions:
            raise HTTPException(status_code=400, detail="Session already completed")

        # If the session has a precomputed sequence, serve from it deterministically.
        if isinstance(getattr(sess, "question_sequence", None), list) and sess.question_sequence:
            idx = int(sess.current_index or 0)
            seq_raw = [x for x in (sess.question_sequence or []) if isinstance(x, str) and x.strip()]

            while idx < len(seq_raw) and idx < int(sess.total_questions or 0):
                try:
                    qid = uuid.UUID(seq_raw[idx])
                except Exception:
                    idx += 1
                    continue

                qres = await db.execute(select(AptitudeQuestion).where(AptitudeQuestion.id == qid))
                q = qres.scalar_one_or_none()
                if q is None:
                    idx += 1
                    continue

                try:
                    _validate_question_record(q)
                except ValueError as exc:
                    logger.warning("Invalid aptitude question rejected id=%s error=%s", q.id, exc)
                    idx += 1
                    continue

                sess.used_question_ids = list(sess.used_question_ids or []) + [str(q.id)]
                sess.current_index = idx + 1
                await db.flush()

                return {
                    "session_id": sess.id,
                    "question_id": q.id,
                    "question": q.question,
                    "options": [str(x) for x in q.options],
                    "category": q.category,
                    "difficulty": q.difficulty,
                    "current_index": sess.current_index,
                    "total_questions": sess.total_questions,
                }

            # Sequence exhausted; treat as completion.
            raise HTTPException(status_code=404, detail="No more questions")

        used_ids: list[uuid.UUID] = []
        if isinstance(sess.used_question_ids, list):
            for x in sess.used_question_ids:
                if isinstance(x, str) and x.strip():
                    try:
                        used_ids.append(uuid.UUID(x.strip()))
                    except Exception:
                        continue

        # Balanced selection targets
        # - Difficulty distribution: ~33% easy/medium/hard
        # - Category balancing: avoid same category streaks > 3
        next_index = len(used_ids) + 1

        def _difficulty_schedule(total: int) -> list[str]:
            # Cyclic schedule approximates 33/33/33 for any total.
            cycle = ["easy", "medium", "hard"]
            return [cycle[i % 3] for i in range(int(total or 0))]

        schedule = _difficulty_schedule(int(sess.total_questions or 0))
        desired_difficulty = schedule[next_index - 1] if 1 <= next_index <= len(schedule) else None

        recent_categories: list[str] = []
        if used_ids:
            tail_ids = used_ids[-3:]
            recent_res = await db.execute(select(AptitudeQuestion.id, AptitudeQuestion.category).where(AptitudeQuestion.id.in_(tail_ids)))
            cat_by_id = {row[0]: str(row[1] or "") for row in (recent_res.all() or [])}
            for qid in tail_ids:
                cat = cat_by_id.get(qid)
                if cat:
                    recent_categories.append(cat)

        def _max_consecutive_if_added(cat: str) -> int:
            streak = 0
            for c in reversed(recent_categories):
                if c != cat:
                    break
                streak += 1
            return streak + 1

        def _difficulty_fallbacks(primary: Optional[str]) -> list[Optional[str]]:
            if not primary:
                return [None]
            primary = str(primary).lower()
            if primary == "easy":
                return ["easy", "medium", "hard"]
            if primary == "hard":
                return ["hard", "medium", "easy"]
            return ["medium", "easy", "hard"]

        base_where = [
            AptitudeQuestion.is_deleted == False,
            AptitudeQuestion.status == "approved",
            AptitudeQuestion.is_active == True,
        ]
        if category:
            base_where.append(AptitudeQuestion.category == category)
        if used_ids:
            base_where.append(~AptitudeQuestion.id.in_(used_ids))

        q: Optional[AptitudeQuestion] = None
        max_category_streak = 3

        # Strategy:
        # 1) Try desired difficulty first, then fall back to others.
        # 2) Prefer curated questions.
        # 3) Pull a small random candidate set and pick one that doesn't violate category streak.
        for diff in _difficulty_fallbacks(desired_difficulty):
            diff_where = list(base_where)
            if diff:
                diff_where.append(AptitudeQuestion.difficulty == diff)

            for curated_first in (True, False):
                stmt = select(AptitudeQuestion)
                if curated_first:
                    stmt = stmt.where(AptitudeQuestion.source == "curated", *diff_where)
                else:
                    stmt = stmt.where(*diff_where)

                stmt = stmt.order_by(func.random()).limit(50)
                res = await db.execute(stmt)
                candidates = list(res.scalars().all() or [])
                if not candidates:
                    continue

                random.shuffle(candidates)
                picked = None
                for cand in candidates:
                    cand_cat = str(getattr(cand, "category", "") or "")
                    if not cand_cat:
                        picked = cand
                        break
                    if _max_consecutive_if_added(cand_cat) <= max_category_streak:
                        picked = cand
                        break

                # If we couldn't satisfy category balance, allow any candidate (fallback).
                q = picked or candidates[0]
                break

            if q is not None:
                break

        if q is None:
            raise HTTPException(status_code=404, detail="No aptitude questions available")

        try:
            _validate_question_record(q)
        except ValueError as exc:
            logger.warning("Invalid aptitude question rejected id=%s error=%s", q.id, exc)
            raise HTTPException(status_code=422, detail=f"Invalid question in pool: {exc}") from exc

        sess.used_question_ids = list(sess.used_question_ids or []) + [str(q.id)]
        sess.current_index = int(sess.current_index or 0) + 1
        await db.flush()

        return {
            "session_id": sess.id,
            "question_id": q.id,
            "question": q.question,
            "options": [str(x) for x in q.options],
            "category": q.category,
            "difficulty": q.difficulty,
            "current_index": sess.current_index,
            "total_questions": sess.total_questions,
        }

    @staticmethod
    async def submit_answer(
        *,
        session_id: uuid.UUID,
        user_id: str,
        question_id: uuid.UUID,
        selected_option: str,
        time_taken: Optional[int],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        sess = await AptitudeService._get_session_for_user(session_id=session_id, user_id=user_id, db=db)
        if sess.completed_at is not None:
            raise HTTPException(status_code=400, detail="Session already completed")

        qres = await db.execute(select(AptitudeQuestion).where(AptitudeQuestion.id == question_id))
        q = qres.scalar_one_or_none()
        if q is None:
            raise HTTPException(status_code=404, detail="Question not found")

        try:
            _validate_question_record(q)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid question: {exc}") from exc

        attempt_exists = await db.execute(
            select(AptitudeAttempt.id).where(
                AptitudeAttempt.session_id == session_id,
                AptitudeAttempt.question_id == question_id,
            )
        )
        if attempt_exists.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Question already answered in this session")

        normalized_selected = str(selected_option).strip()
        if normalized_selected not in [str(x).strip() for x in q.options]:
            raise HTTPException(status_code=422, detail="selected_option must match one of the options")

        is_correct = normalized_selected == str(q.correct_answer).strip()
        if is_correct:
            sess.score = int(sess.score or 0) + 1

        # Increment question usage statistics
        try:
            q.increment_usage()
            if is_correct:
                q.increment_correct()
            else:
                q.increment_wrong()
        except Exception as stats_err:
            logger.warning("Failed to increment stats: %s", stats_err)

        attempt = AptitudeAttempt(
            session_id=session_id,
            question_id=question_id,
            selected_option=normalized_selected,
            is_correct=bool(is_correct),
            time_taken=int(time_taken) if time_taken is not None else None,
        )
        db.add(attempt)
        await db.flush()

        attempted_count_res = await db.execute(
            select(func.count(AptitudeAttempt.id)).where(AptitudeAttempt.session_id == session_id)
        )
        attempted_count = int(attempted_count_res.scalar_one() or 0)

        if attempted_count >= int(sess.total_questions):
            sess.completed_at = datetime.utcnow()
            await db.flush()

        return {
            "correct": bool(is_correct),
            "correct_answer": str(q.correct_answer),
            "explanation": q.explanation,
            "score": int(sess.score or 0),
            "current_index": int(sess.current_index or 0),
            "total_questions": int(sess.total_questions or 0),
            "is_completed": sess.completed_at is not None,
        }

    @staticmethod
    async def get_report(*, session_id: uuid.UUID, user_id: str, db: AsyncSession) -> Dict[str, Any]:
        sess = await AptitudeService._get_session_for_user(session_id=session_id, user_id=user_id, db=db)

        attempts_res = await db.execute(
            select(AptitudeAttempt, AptitudeQuestion)
            .join(AptitudeQuestion, AptitudeQuestion.id == AptitudeAttempt.question_id)
            .where(AptitudeAttempt.session_id == session_id)
        )
        rows = attempts_res.all()

        attempted = len(rows)
        total_questions = int(sess.total_questions or 0)

        # Prefer counting attempts for correctness (source of truth), but keep session score as fallback.
        correct_count = sum(1 for a, _q in rows if getattr(a, "is_correct", False))
        score = int(correct_count if attempted else (sess.score or 0))

        accuracy_percent = round((score / attempted) * 100.0, 2) if attempted else 0.0

        attempts_out: list[Dict[str, Any]] = []
        for attempt, question in rows:
            attempts_out.append(
                {
                    "question": str(getattr(question, "question", "") or ""),
                    "your_answer": str(getattr(attempt, "selected_option", "") or ""),
                    "correct_answer": str(getattr(question, "correct_answer", "") or ""),
                    "is_correct": bool(getattr(attempt, "is_correct", False)),
                    "explanation": getattr(question, "explanation", None),
                }
            )

        breakdown: Dict[str, Dict[str, Any]] = {}
        for attempt, question in rows:
            cat = str(question.category or "unknown")
            entry = breakdown.setdefault(cat, {"attempted": 0, "correct": 0, "accuracy_percent": 0.0})
            entry["attempted"] += 1
            if attempt.is_correct:
                entry["correct"] += 1

        for cat, entry in breakdown.items():
            att = int(entry.get("attempted") or 0)
            cor = int(entry.get("correct") or 0)
            entry["accuracy_percent"] = round((cor / att) * 100.0, 2) if att else 0.0

        return {
            # Existing fields (backward compatible)
            "session_id": sess.id,
            "total_questions": total_questions,
            "attempted": attempted,
            "score": score,
            "accuracy_percent": accuracy_percent,
            "category_breakdown": breakdown,

            # New detailed fields
            "total": total_questions,
            "accuracy": accuracy_percent,
            "attempts": attempts_out,
        }


async def seed_questions_if_empty(*, db: AsyncSession, json_path: str) -> int:
    print("Seeding aptitude questions (smart sync)...")

    if not os.path.exists(json_path):
        logger.warning("Aptitude seed file not found: %s", json_path)
        return 0

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as exc:
        logger.warning("Aptitude seeding failed to read JSON: %s", exc)
        return 0

    if not isinstance(raw, list):
        raise RuntimeError("aptitude_questions.json must be a list")

    existing_res = await db.execute(select(AptitudeQuestion.question))
    existing_questions = existing_res.all() or []
    existing_set = {str(row[0]).strip() for row in existing_questions if row and row[0]}

    inserted = 0
    skipped_existing = 0
    for item in raw:
        try:
            question_text = str(item.get("question", "")).strip()
            if not question_text:
                raise ValueError("question cannot be empty")

            if question_text in existing_set:
                skipped_existing += 1
                continue

            norm = normalize_question_text(question_text)
            q_hash = generate_question_hash(norm)

            q = AptitudeQuestion(
                question=question_text,
                options=item.get("options", []),
                correct_answer=str(item.get("correct_answer", "")).strip(),
                category=str(item.get("category", "general")).strip() or "general",
                difficulty=str(item.get("difficulty", "easy")).strip() or "easy",
                source=str(item.get("source", "curated")).strip() or "curated",
                explanation=str(item.get("explanation", "")).strip() or None,
                domain=str(item.get("domain", "quantitative")).strip() or "quantitative",
                subcategory=str(item.get("subcategory", "")).strip() or None,
                status="approved",  # Seeded questions are approved immediately
                normalized_question_hash=q_hash,
                is_active=True,
                is_deleted=False,
                tags=item.get("tags") or [],
                expected_time_seconds=item.get("expected_time_seconds") or 60,
            )
            _validate_question_record(q)
            db.add(q)
            inserted += 1
            existing_set.add(question_text)
        except Exception as exc:
            logger.warning("Skipping invalid seed question: %s", exc)
            continue

    if inserted <= 0:
        print(f"New questions added: 0")
        print(f"Skipped existing questions: {skipped_existing}")
        return 0

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.warning("Error inserting questions: %s", str(exc))
        return 0

    print(f"New questions added: {inserted}")
    print(f"Skipped existing questions: {len(raw) - inserted}")
    return inserted
