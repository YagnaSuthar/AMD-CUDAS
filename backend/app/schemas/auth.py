"""Pydantic schemas for authentication endpoints."""

from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Request Schemas ───────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterPrincipalRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    college_name: str
    phone_number: Optional[str] = None
    company_name: Optional[str] = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterCompanyRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    company_name: str
    phone_number: Optional[str] = None


# ── Response Schemas ──────────────────────────────────────────────────────


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    name: str


class MessageResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    role: str
    is_verified: bool = True
    department: Optional[str] = None
    semester: Optional[int] = None
    roll_number: Optional[str] = None
    phone_number: Optional[str] = None
    parent_id: Optional[str] = None
    skills: Optional[list[str]] = None
    resume_url: Optional[str] = None
    goal: Optional[str] = None

    class Config:
        from_attributes = True


class AddUserRequest(BaseModel):
    name: str
    email: EmailStr
    department: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    phone_number: Optional[str] = None
    skills: Optional[list[str]] = None
    goal: Optional[str] = None


class CareerRoadmapResponse(BaseModel):
    roadmap: str


class CollegeResponse(BaseModel):
    id: str
    name: str
    principal_name: str
    principal_email: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    id: str
    name: str
    admin_name: str
    admin_email: str
    status: str
    created_at: str

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_colleges: int
    total_companies: int
    total_users: int
    pending_approvals: int
    users_by_role: dict


# ── Timetable Schemas ─────────────────────────────────────────────────────


class TimetableCreate(BaseModel):
    semester: int
    subject_name: str
    exam_date: str
    exam_time: str


class TimetableUpdate(BaseModel):
    semester: Optional[int] = None
    subject_name: Optional[str] = None
    exam_date: Optional[str] = None
    exam_time: Optional[str] = None


class TimetableResponse(BaseModel):
    id: str
    department: str
    semester: int
    subject_name: str
    exam_date: str
    exam_time: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Marks Schemas ─────────────────────────────────────────────────────────


class MarksUpload(BaseModel):
    student_id: str
    subject_name: str
    semester: int
    marks_obtained: float
    max_marks: float = 100.0


class MarksUpdate(BaseModel):
    marks_obtained: Optional[float] = None
    max_marks: Optional[float] = None


class MarksResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    subject_name: str
    semester: int
    marks_obtained: float
    max_marks: float
    is_locked: bool = False
    uploaded_by: Optional[str] = None

    class Config:
        from_attributes = True


class MarksLockRequest(BaseModel):
    semester: int


# ── Certificate Schemas ───────────────────────────────────────────────────


class CertificateResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    file_name: str
    is_verified: bool = False
    points: int = 0
    uploaded_at: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: str
    project_name: str
    description: Optional[str] = None
    github_url: str
    tech_stack: Optional[str] = None
    verification_status: str
    verification_run_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Dashboard Overview Schemas ────────────────────────────────────────────


class DepartmentDetail(BaseModel):
    department: str
    student_count: int
    faculty_count: int
    average_marks: float


class PrincipalOverviewResponse(BaseModel):
    total_departments: int
    total_hods: int
    total_faculty: int
    total_students: int
    overall_performance: float
    departments: list[DepartmentDetail]


class StudentBrief(BaseModel):
    id: str
    name: str
    email: str
    department: Optional[str] = None
    average: float


class HodOverviewResponse(BaseModel):
    total_faculty: int
    total_students: int
    department_average: float
    top_students: list[StudentBrief]
    weak_students: list[StudentBrief]


class SubjectStat(BaseModel):
    subject_name: str
    student_count: int
    average_marks: float


class FacultyOverviewResponse(BaseModel):
    assigned_semesters: list[int]
    assigned_subjects: list[str]
    total_students: int
    subject_stats: list[SubjectStat]


class StudentMarksDetail(BaseModel):
    subject_name: str
    semester: int
    marks_obtained: float
    max_marks: float
    percentage: float


class StudentAcademicResponse(BaseModel):
    gpa: float
    total_marks: float
    max_possible: float
    percentage: float
    rank: int
    total_in_class: int
    marks: list[StudentMarksDetail]


# ── Department Schemas ────────────────────────────────────────────────────


class DepartmentCreate(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


# ── Mentor Assignment Schemas ─────────────────────────────────────────────


class MentorAssignmentCreate(BaseModel):
    faculty_id: str
    semester: int


class MentorAssignmentResponse(BaseModel):
    id: str
    faculty_id: str
    faculty_name: Optional[str] = None
    semester: int
    department: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Leaderboard Schemas ──────────────────────────────────────────────────


class LeaderboardEntry(BaseModel):
    rank: int
    student_id: str
    name: str
    email: str
    department: Optional[str] = None
    semester: Optional[int] = None
    average_marks: float
    certificate_points: int
    total_score: float
    badge: Optional[str] = None
