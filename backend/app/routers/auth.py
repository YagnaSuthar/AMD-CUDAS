"""
Auth router — login, register principal, verify email, forgot/reset password, refresh, me.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.auth import AuthUser, AuthUserRole, College, ApprovalStatus
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    RegisterPrincipalRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
    ResendOTPRequest,
)
from app.services.email_service import send_reset_password_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Login ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Check static CUDAS admin first
    if (
        body.email == settings.CUDAS_ADMIN_EMAIL
        and body.password == settings.CUDAS_ADMIN_PASSWORD
    ):
        token_data = {"sub": body.email, "role": "CUDAS_ADMIN"}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            role="CUDAS_ADMIN",
            name="CUDAS Admin",
        )

    # Regular user login
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user or (user.hashed_password and not verify_password(body.password, user.hashed_password)):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user.hashed_password is None or user.must_reset_password:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Password reset required before login.",
                "reset_required": True,
                "email": user.email
            }
        )

    if not user.is_verified:
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        user.verification_token = otp
        user.verification_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
        
        # Send OTP email
        send_verification_email(user.email, otp)
        
        # Return a custom error that the frontend can catch to redirect to OTP page
        return JSONResponse(
            status_code=403, 
            content={"detail": "Email not verified. A new OTP has been sent to your email.", "unverified": True, "email": user.email}
        )

    # Check if college principal and college is approved
    if user.role == AuthUserRole.COLLEGE_PRINCIPAL:
        college_result = await db.execute(
            select(College).where(College.principal_id == user.id)
        )
        college = college_result.scalar_one_or_none()
        if college and college.status == ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=403,
                detail="Your college registration is pending admin approval.",
            )
        if college and college.status == ApprovalStatus.REJECTED:
            raise HTTPException(
                status_code=403,
                detail="Your college registration has been rejected.",
            )

    # Check if company admin and company is approved
    if user.role == AuthUserRole.COMPANY_ADMIN:
        from app.models.auth import Company
        company_result = await db.execute(
            select(Company).where(Company.company_admin_id == user.id)
        )
        company = company_result.scalar_one_or_none()
        if company and company.status == ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=403,
                detail="Your company registration is pending admin approval.",
            )
        if company and company.status == ApprovalStatus.REJECTED:
            raise HTTPException(
                status_code=403,
                detail="Your company registration has been rejected.",
            )

    token_data = {"sub": user.email, "role": user.role, "user_id": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=user.role,
        name=user.name,
    )


# ── Register College Principal ────────────────────────────────────────────


@router.post("/register-principal", response_model=MessageResponse)
async def register_principal(
    body: RegisterPrincipalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Check email uniqueness
    existing = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now(timezone.utc) + timedelta(minutes=15)

    user = AuthUser(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=AuthUserRole.COLLEGE_PRINCIPAL,
        is_verified=False,
        phone_number=body.phone_number,
        company_name=body.company_name,
    )
    db.add(user)
    await db.flush()

    college = College(
        name=body.college_name,
        principal_id=user.id,
    )
    db.add(college)

    return MessageResponse(message="Registration successful! Please login to verify your account.")


# ── Verify Email ──────────────────────────────────────────────────────────


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(body: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if user.is_verified:
        return MessageResponse(message="Email is already verified.")

    if user.verification_token != body.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user.verification_token_expiry and user.verification_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expiry = None

    return MessageResponse(message="Email verified successfully! You can now log in.")


# ── Resend OTP ────────────────────────────────────────────────────────────

@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(body: ResendOTPRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal user existence
        return MessageResponse(message="If the email is registered, a new OTP has been sent.")

    if user.is_verified:
        return MessageResponse(message="Email is already verified.")

    otp = str(random.randint(100000, 999999))
    user.verification_token = otp
    user.verification_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=15)

    send_verification_email(body.email, otp)
    return MessageResponse(message="A new OTP has been sent to your email.")


# ── Forgot Password ──────────────────────────────────────────────────────


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AuthUser).where(AuthUser.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal whether email exists
        return MessageResponse(message="If the email exists, a reset link has been sent.")

    reset_token = str(uuid.uuid4())
    user.reset_token = reset_token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

    base_url = str(request.base_url).rstrip("/").replace("/api", "").replace(":8000", ":5173")
    send_reset_password_email(body.email, reset_token, base_url)

    return MessageResponse(message="If the email exists, a reset link has been sent.")


# ── Reset Password ────────────────────────────────────────────────────────


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuthUser).where(AuthUser.reset_token == body.token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if user.reset_token_expiry and user.reset_token_expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    user.hashed_password = hash_password(body.new_password)
    user.must_reset_password = False
    user.reset_token = None
    user.reset_token_expiry = None

    return MessageResponse(message="Password reset successful! You can now log in.")


# ── Refresh Token ─────────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    email = payload.get("sub")
    role = payload.get("role")

    token_data = {"sub": email, "role": role}

    # For CUDAS admin
    if role == "CUDAS_ADMIN":
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            role="CUDAS_ADMIN",
            name="CUDAS Admin",
        )

    result = await db.execute(select(AuthUser).where(AuthUser.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    token_data["user_id"] = str(user.id)
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=user.role,
        name=user.name,
    )


# ── Current User ──────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        return UserResponse(**current_user)
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_verified=current_user.is_verified,
        department=current_user.department,
        semester=current_user.semester,
        roll_number=current_user.roll_number,
        parent_id=str(current_user.parent_id) if current_user.parent_id else None,
    )
