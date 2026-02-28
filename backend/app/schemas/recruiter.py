from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RecruiterCollegeResponse(BaseModel):
    id: str
    name: str
    principal_id: str
    principal_name: str


class RecruiterDepartmentResponse(BaseModel):
    id: str
    name: str


class RecruiterStudentListEntry(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None
    semester: Optional[int] = None
    average_marks: float
    certificate_points: int
    total_score: float
    skills: Optional[list[str]] = None
    resume_url: Optional[str] = None


class RecruiterStudentInterviewSummary(BaseModel):
    session_id: str
    job_role: str
    status: str
    started_at: str
    ended_at: Optional[str] = None
    final_score: Optional[float] = None
    recommendation: Optional[str] = None


class RecruiterStudentPipelineSummary(BaseModel):
    pipeline_id: str
    job_id: str
    status: str
    ai_session_id: Optional[str] = None
    round2_link: Optional[str] = None
    hired_company_name: Optional[str] = None
    updated_at: str


class RecruiterStudentProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None
    semester: Optional[int] = None
    skills: Optional[list[str]] = None
    resume_url: Optional[str] = None
    interviews: list[RecruiterStudentInterviewSummary]
    pipelines: list[RecruiterStudentPipelineSummary]
