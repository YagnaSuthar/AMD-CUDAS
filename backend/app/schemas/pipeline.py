import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssignAiInterviewRequest(BaseModel):
    job_id: uuid.UUID
    student_id: uuid.UUID


class InviteRound2Request(BaseModel):
    pipeline_id: uuid.UUID
    round2_link: str = Field(..., min_length=1, max_length=512)


class MarkHiredRequest(BaseModel):
    pipeline_id: uuid.UUID
    hired_company_name: str = Field(..., min_length=1, max_length=255)


class PipelineResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    company_id: uuid.UUID
    recruiter_id: uuid.UUID
    student_id: uuid.UUID
    ai_session_id: uuid.UUID | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    round2_link: str | None = None
    hired_company_name: str | None = None

    class Config:
        from_attributes = True
