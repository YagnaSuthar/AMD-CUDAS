from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

<<<<<<< HEAD
=======
class RecruiterStudentProjectSummary(BaseModel):
    id: str
    project_name: str
    description: Optional[str] = None
    tech_stack: Optional[str] = None
    github_url: Optional[str] = None
    verification_status: Optional[str] = None

class RecruiterStudentCertificateSummary(BaseModel):
    id: str
    title: str
    file_path: Optional[str] = None
    points: int
    is_verified: bool

>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a

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
<<<<<<< HEAD
=======
    projects: list[RecruiterStudentProjectSummary] = []
    certificates: list[RecruiterStudentCertificateSummary] = []
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
