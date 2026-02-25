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
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


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
