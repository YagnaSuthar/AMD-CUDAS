import re
import hashlib
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Valid domains
VALID_DOMAINS = {
    "quantitative",
    "logical_reasoning",
    "verbal_ability",
    "data_interpretation"
}

# Valid difficulties
VALID_DIFFICULTIES = {"easy", "medium", "hard"}

# Valid statuses
VALID_STATUSES = {"draft", "approved", "archived"}

# Valid sources
VALID_SOURCES = {"curated", "admin", "imported", "generated"}


def normalize_question_text(text: str) -> str:
    """
    Normalizes question text:
    - lowercase
    - trim spaces
    - collapse repeated whitespace
    - remove trivial punctuation differences
    """
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove trivial punctuation differences (keeping only alphanumeric characters and basic spaces)
    text = re.sub(r"[^\w\s]", "", text)
    # Trim
    return text.strip()


def generate_question_hash(normalized_text: str) -> str:
    """Generates deterministic SHA-256 hash for normalized question text."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


async def validate_aptitude_question(
    *,
    question: str,
    options: List[Any],
    correct_answer: str,
    domain: Optional[str],
    category: str,
    difficulty: str,
    status: Optional[str] = None,
    source: Optional[str] = None,
    expected_time_seconds: Optional[int] = None,
    db: Optional[AsyncSession] = None,
    current_batch_hashes: Optional[Set[str]] = None,
    exclude_question_id: Optional[Any] = None,
) -> List[Dict[str, str]]:
    """
    Validates a question. Returns list of error dicts: [{"field": field, "message": message}]
    """
    errors = []

    # 1. Question text exists
    clean_question = (question or "").strip()
    if not clean_question:
        errors.append({"field": "question", "message": "Question text must not be empty"})

    # 2. Options must be a list of 4 elements, none empty
    if not isinstance(options, list):
        errors.append({"field": "options", "message": "Options must be a list"})
    else:
        if len(options) != 4:
            errors.append({"field": "options", "message": "Options list must have exactly 4 items"})
        
        # Check no empty option
        option_strings = []
        has_empty = False
        for opt in options:
            opt_str = str(opt).strip()
            if not opt_str:
                has_empty = True
            option_strings.append(opt_str)
        
        if has_empty:
            errors.append({"field": "options", "message": "Options cannot be empty or purely whitespace"})

        # Options unique
        if len(options) == 4 and len(set(option_strings)) != 4:
            errors.append({"field": "options", "message": "All 4 options must be unique"})

    # 3. Correct answer exists and matches one of the options
    clean_correct = (correct_answer or "").strip()
    if not clean_correct:
        errors.append({"field": "correct_answer", "message": "Correct answer must not be empty"})
    elif isinstance(options, list) and len(options) == 4:
        option_strings = [str(opt).strip() for opt in options]
        if clean_correct not in option_strings:
            errors.append({
                "field": "correct_answer", 
                "message": f"Correct answer '{clean_correct}' must exactly match one of the options: {option_strings}"
            })

    # 4. Domain valid
    if domain:
        clean_domain = domain.strip().lower()
        if clean_domain not in VALID_DOMAINS:
            errors.append({
                "field": "domain",
                "message": f"Invalid domain '{domain}'. Valid domains: {list(VALID_DOMAINS)}"
            })
    else:
        errors.append({"field": "domain", "message": "Domain is required"})

    # 5. Category valid (non-empty)
    if not (category or "").strip():
        errors.append({"field": "category", "message": "Category must not be empty"})

    # 6. Difficulty valid
    clean_diff = (difficulty or "").strip().lower()
    if clean_diff not in VALID_DIFFICULTIES:
        errors.append({
            "field": "difficulty",
            "message": f"Invalid difficulty '{difficulty}'. Valid difficulties: {list(VALID_DIFFICULTIES)}"
        })

    # 7. Status valid (if provided)
    if status:
        clean_status = status.strip().lower()
        if clean_status not in VALID_STATUSES:
            errors.append({
                "field": "status",
                "message": f"Invalid status '{status}'. Valid statuses: {list(VALID_STATUSES)}"
            })

    # 8. Source valid (if provided)
    if source:
        clean_source = source.strip().lower()
        if clean_source not in VALID_SOURCES:
            errors.append({
                "field": "source",
                "message": f"Invalid source '{source}'. Valid sources: {list(VALID_SOURCES)}"
            })

    # 9. Expected solve time > 0 if provided
    if expected_time_seconds is not None:
        try:
            val = int(expected_time_seconds)
            if val <= 0:
                errors.append({
                    "field": "expected_time_seconds",
                    "message": "Expected solve time must be greater than 0"
                })
        except (ValueError, TypeError):
            errors.append({
                "field": "expected_time_seconds",
                "message": "Expected solve time must be a valid integer"
            })

    # 10. Duplicate question text (Normalized Hash Check)
    if clean_question:
        normalized = normalize_question_text(clean_question)
        q_hash = generate_question_hash(normalized)

        # Check current batch
        if current_batch_hashes is not None and q_hash in current_batch_hashes:
            errors.append({
                "field": "question",
                "message": "Duplicate question text found in the current import batch"
            })

        # Check database (check ALL records, even deleted or archived ones to avoid unique conflict)
        if db is not None:
            from app.api.ai.agents.aptitude.models import AptitudeQuestion
            stmt = select(AptitudeQuestion.id).where(AptitudeQuestion.normalized_question_hash == q_hash)
            if exclude_question_id is not None:
                stmt = stmt.where(AptitudeQuestion.id != exclude_question_id)
            
            res = await db.execute(stmt)
            existing_id = res.scalar_one_or_none()
            if existing_id is not None:
                errors.append({
                    "field": "question",
                    "message": f"Duplicate question text already exists in database (Question ID: {existing_id})"
                })

    return errors
