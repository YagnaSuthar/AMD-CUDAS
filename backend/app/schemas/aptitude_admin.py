import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AptitudeQuestionCreate(BaseModel):
    question: str = Field(..., description="The question text")
    options: List[str] = Field(..., description="List of exactly 4 choices")
    correct_answer: str = Field(..., description="The correct answer text matching one option")
    category: str = Field(..., description="E.g. percentage, profit_loss")
    difficulty: str = Field(..., description="easy, medium, hard")
    domain: str = Field(..., description="quantitative, logical_reasoning, verbal_ability, data_interpretation")
    subcategory: Optional[str] = Field(default=None)
    explanation: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    expected_time_seconds: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default="draft")
    source: Optional[str] = Field(default="admin")

    @field_validator("expected_time_seconds")
    @classmethod
    def validate_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("expected_time_seconds must be greater than 0")
        return v


class AptitudeQuestionUpdate(BaseModel):
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[str] = None
    domain: Optional[str] = None
    subcategory: Optional[str] = None
    explanation: Optional[str] = None
    tags: Optional[List[str]] = None
    expected_time_seconds: Optional[int] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

    @field_validator("expected_time_seconds")
    @classmethod
    def validate_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("expected_time_seconds must be greater than 0")
        return v


class AptitudeQuestionResponse(BaseModel):
    id: uuid.UUID
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None
    domain: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    difficulty: str
    status: str
    source: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[uuid.UUID] = None
    is_active: bool
    tags: Optional[List[str]] = None
    expected_time_seconds: Optional[int] = None
    times_used: int
    times_correct: int
    times_wrong: int
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AptitudeQuestionListResponse(BaseModel):
    questions: List[AptitudeQuestionResponse]
    total: int
    limit: int
    offset: int


class QuestionImportJobResponse(BaseModel):
    id: uuid.UUID
    filename: str
    source_type: str
    status: str
    total_questions: int
    valid_questions: int
    invalid_questions: int
    error_log: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuestionImportItemResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    raw_data: Dict[str, Any]
    parsed_question: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[Dict[str, Any]]] = None
    status: str

    class Config:
        from_attributes = True


class QuestionImportJobDetailResponse(BaseModel):
    job: QuestionImportJobResponse
    items: List[QuestionImportItemResponse]


class TaxonomyHierarchyResponse(BaseModel):
    # Represents hierarchy: { domain: { category: [ subcategory1, subcategory2 ] } }
    hierarchy: Dict[str, Dict[str, List[str]]]
