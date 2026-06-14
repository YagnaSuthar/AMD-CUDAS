import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ai.agents.aptitude.models import AptitudeQuestion
from app.services.aptitude_validator import normalize_question_text, generate_question_hash


class AptitudeRepository:
    """
    Production-ready repository layer for manual question management, search, and statistics.
    """

    @staticmethod
    async def create_question(
        db: AsyncSession,
        *,
        question: str,
        options: List[str],
        correct_answer: str,
        category: str,
        difficulty: str,
        domain: Optional[str] = None,
        subcategory: Optional[str] = None,
        status: str = "draft",
        source: str = "admin",
        explanation: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expected_time_seconds: Optional[int] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> AptitudeQuestion:
        # Normalize and hash
        norm_txt = normalize_question_text(question)
        q_hash = generate_question_hash(norm_txt)

        db_question = AptitudeQuestion(
            question=question,
            options=options,
            correct_answer=correct_answer,
            category=category,
            difficulty=difficulty,
            domain=domain,
            subcategory=subcategory,
            status=status,
            source=source,
            explanation=explanation,
            tags=tags or [],
            expected_time_seconds=expected_time_seconds,
            normalized_question_hash=q_hash,
            created_by=created_by,
            is_active=True,
            is_deleted=False,
        )
        db.add(db_question)
        await db.flush()
        return db_question

    @staticmethod
    async def update_question(
        db: AsyncSession,
        question_id: uuid.UUID,
        *,
        question: Optional[str] = None,
        options: Optional[List[str]] = None,
        correct_answer: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        domain: Optional[str] = None,
        subcategory: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        explanation: Optional[str] = None,
        tags: Optional[List[str]] = None,
        expected_time_seconds: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[AptitudeQuestion]:
        res = await db.execute(
            select(AptitudeQuestion).where(
                AptitudeQuestion.id == question_id,
                AptitudeQuestion.is_deleted == False
            )
        )
        db_question = res.scalar_one_or_none()
        if not db_question:
            return None

        # Apply edits
        if question is not None:
            db_question.question = question
            norm_txt = normalize_question_text(question)
            db_question.normalized_question_hash = generate_question_hash(norm_txt)
        if options is not None:
            db_question.options = options
        if correct_answer is not None:
            db_question.correct_answer = correct_answer
        if category is not None:
            db_question.category = category
        if difficulty is not None:
            db_question.difficulty = difficulty
        if domain is not None:
            db_question.domain = domain
        if subcategory is not None:
            db_question.subcategory = subcategory
        if status is not None:
            db_question.status = status
            if status == "approved" and not db_question.approved_at:
                db_question.approved_at = datetime.utcnow()
        if source is not None:
            db_question.source = source
        if explanation is not None:
            db_question.explanation = explanation
        if tags is not None:
            db_question.tags = tags
        if expected_time_seconds is not None:
            db_question.expected_time_seconds = expected_time_seconds
        if is_active is not None:
            db_question.is_active = is_active

        await db.flush()
        return db_question

    @staticmethod
    async def approve_question(
        db: AsyncSession, question_id: uuid.UUID, approved_by: Optional[uuid.UUID] = None
    ) -> Optional[AptitudeQuestion]:
        res = await db.execute(
            select(AptitudeQuestion).where(
                AptitudeQuestion.id == question_id,
                AptitudeQuestion.is_deleted == False
            )
        )
        q = res.scalar_one_or_none()
        if not q:
            return None

        q.status = "approved"
        q.approved_at = datetime.utcnow()
        q.approved_by = approved_by
        await db.flush()
        return q

    @staticmethod
    async def archive_question(db: AsyncSession, question_id: uuid.UUID) -> Optional[AptitudeQuestion]:
        res = await db.execute(
            select(AptitudeQuestion).where(
                AptitudeQuestion.id == question_id,
                AptitudeQuestion.is_deleted == False
            )
        )
        q = res.scalar_one_or_none()
        if not q:
            return None

        q.status = "archived"
        await db.flush()
        return q

    @staticmethod
    async def restore_question(db: AsyncSession, question_id: uuid.UUID) -> Optional[AptitudeQuestion]:
        res = await db.execute(select(AptitudeQuestion).where(AptitudeQuestion.id == question_id))
        q = res.scalar_one_or_none()
        if not q:
            return None

        # Re-activate and remove deleted/archived markers
        q.is_deleted = False
        q.deleted_at = None
        q.is_active = True
        q.status = "draft"  # return to draft for review, or keep original? draft is safest.
        await db.flush()
        return q

    @staticmethod
    async def soft_delete_question(db: AsyncSession, question_id: uuid.UUID) -> bool:
        res = await db.execute(
            select(AptitudeQuestion).where(
                AptitudeQuestion.id == question_id,
                AptitudeQuestion.is_deleted == False
            )
        )
        q = res.scalar_one_or_none()
        if not q:
            return False

        q.is_deleted = True
        q.deleted_at = datetime.utcnow()
        await db.flush()
        return True

    @staticmethod
    async def search_questions(
        db: AsyncSession,
        *,
        domain: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
        include_deleted: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[AptitudeQuestion], int]:
        # Count query
        count_stmt = select(func.count(AptitudeQuestion.id))
        if not include_deleted:
            count_stmt = count_stmt.where(AptitudeQuestion.is_deleted == False)

        # Base search query
        stmt = select(AptitudeQuestion)
        if not include_deleted:
            stmt = stmt.where(AptitudeQuestion.is_deleted == False)

        # Filters
        for q in [count_stmt, stmt]:
            if domain:
                q = q.where(AptitudeQuestion.domain == domain)
            if category:
                q = q.where(AptitudeQuestion.category == category)
            if subcategory:
                q = q.where(AptitudeQuestion.subcategory == subcategory)
            if difficulty:
                q = q.where(AptitudeQuestion.difficulty == difficulty)
            if status:
                q = q.where(AptitudeQuestion.status == status)
            if source:
                q = q.where(AptitudeQuestion.source == source)
            if is_active is not None:
                q = q.where(AptitudeQuestion.is_active == is_active)
            if tags:
                for tag in tags:
                    # JSONB list contains element check
                    q = q.where(AptitudeQuestion.tags.contains([tag]))

            # Re-bind
            if q is count_stmt:
                count_stmt = q
            else:
                stmt = q

        total = await db.scalar(count_stmt) or 0

        # Sort by creation descending and apply limits
        stmt = stmt.order_by(AptitudeQuestion.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    @staticmethod
    async def bulk_insert_questions(
        db: AsyncSession, questions_data: List[Dict[str, Any]], created_by: Optional[uuid.UUID] = None
    ) -> List[AptitudeQuestion]:
        inserted = []
        for item in questions_data:
            q = await AptitudeRepository.create_question(
                db=db,
                question=item["question"],
                options=item["options"],
                correct_answer=item["correct_answer"],
                category=item["category"],
                difficulty=item["difficulty"],
                domain=item.get("domain"),
                subcategory=item.get("subcategory"),
                status=item.get("status", "draft"),
                source=item.get("source", "imported"),
                explanation=item.get("explanation"),
                tags=item.get("tags"),
                expected_time_seconds=item.get("expected_time_seconds"),
                created_by=created_by,
            )
            inserted.append(q)
        return inserted

    @staticmethod
    async def increment_usage(db: AsyncSession, question_id: uuid.UUID) -> None:
        await db.execute(
            update(AptitudeQuestion)
            .where(AptitudeQuestion.id == question_id)
            .values(times_used=AptitudeQuestion.times_used + 1)
        )

    @staticmethod
    async def increment_correct(db: AsyncSession, question_id: uuid.UUID) -> None:
        await db.execute(
            update(AptitudeQuestion)
            .where(AptitudeQuestion.id == question_id)
            .values(times_correct=AptitudeQuestion.times_correct + 1)
        )

    @staticmethod
    async def increment_wrong(db: AsyncSession, question_id: uuid.UUID) -> None:
        await db.execute(
            update(AptitudeQuestion)
            .where(AptitudeQuestion.id == question_id)
            .values(times_wrong=AptitudeQuestion.times_wrong + 1)
        )
