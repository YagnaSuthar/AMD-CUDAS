import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    package_lpa: str | None = Field(default=None, max_length=50)
    bond: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class JobUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    package_lpa: str | None = Field(default=None, max_length=50)
    bond: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=20)


class JobResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    recruiter_id: uuid.UUID
    title: str
    description: str
    package_lpa: str | None = None
    bond: str | None = None
    location: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
