"""
Auth router — login, register principal, verify email, forgot/reset password, refresh, me.
"""

import uuid
import random
import re
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
    UpdateProfileRequest,
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
        await db.flush()
        
        # Send OTP email
        sent = send_verification_email(user.email, otp)
        if not sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send OTP email. Please configure SMTP_EMAIL/SMTP_PASSWORD in backend/app/.env (Gmail requires an App Password) and check backend logs for [EMAIL ERROR].",
            )
        
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
        verification_token=otp,
        verification_token_expiry=expiry,
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

    sent = send_verification_email(body.email, otp)
    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please configure SMTP_EMAIL/SMTP_PASSWORD in backend/app/.env (Gmail requires an App Password) and check backend logs for [EMAIL ERROR].",
        )

    return MessageResponse(message="Registration successful! Please check your email for OTP to verify your account.")


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

    await db.flush()

    sent = send_verification_email(body.email, otp)
    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Please configure SMTP_EMAIL/SMTP_PASSWORD in backend/app/.env (Gmail requires an App Password) and check backend logs for [EMAIL ERROR].",
        )
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


import os
import shutil
from fastapi import UploadFile, File

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
        phone_number=current_user.phone_number,
        parent_id=str(current_user.parent_id) if current_user.parent_id else None,
        skills=current_user.skills if current_user.skills else [],
        resume_url=current_user.resume_url,
        goal=current_user.goal,
    )


# ── Update Profile ────────────────────────────────────────────────────────


@router.put("/profile", response_model=MessageResponse)
async def update_profile(
    body: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update the current user's profile (phone number, skills, goal)."""
    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin profile cannot be updated")

    if body.phone_number is not None:
        current_user.phone_number = body.phone_number
    if body.skills is not None:
        current_user.skills = body.skills
    if body.goal is not None:
        current_user.goal = body.goal

    await db.commit()
    return MessageResponse(message="Profile updated successfully.")

# Storage for resumes (using same dir as certificates as requested)
RESUME_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "certificate")

@router.post("/resume", response_model=MessageResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a resume file for the current user.

    Pipeline:
      1. Save file to disk
      2. Extract text via OCR (pypdf)
      3. Extract skills from text
      4. Update user profile (skills, resume_url, StudentProfile.resume_text)
      5. RAG: Chunk → Embed → Store in pgvector (Document + Chunk + ChunkEmbedding)
    """
    import logging
    _logger = logging.getLogger(__name__)

    if isinstance(current_user, dict):
        raise HTTPException(status_code=403, detail="Admin cannot upload resume")

    _logger.info("Resume upload started for user %s", current_user.id)

    os.makedirs(RESUME_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    unique_name = f"resume_{current_user.id}{ext}"
    file_path = os.path.join(RESUME_DIR, unique_name)

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        _logger.info("Resume file saved: %s", file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc

    # ── Step 2: OCR text extraction ───────────────────────────────────────
    extracted_text = ""
    try:
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception:
            PdfReader = None

        if PdfReader is not None:
            reader = PdfReader(file_path)
            extracted_text = "\n".join([(p.extract_text() or "") for p in reader.pages]).strip()
            _logger.info("OCR extracted %d chars from %d pages", len(extracted_text), len(reader.pages))
    except Exception as e:
        _logger.warning("OCR extraction failed: %s", e)
        extracted_text = ""

    # ── Step 3: Extract skills from text ──────────────────────────────────
    extracted_skills: list[str] = []
    try:
        if extracted_text:
            text = extracted_text
            m = re.search(
                r"(?is)(?:^|\n)\s*(?:technical\s+)?skills\s*[:\-]?\s*(.+?)(?:\n\s*\n|\n[A-Z][A-Za-z \t]{2,}:|\n[A-Z][A-Z \t]{2,}\n|$)",
                text,
            )
            skills_blob = m.group(1) if m else ""
            if not skills_blob:
                skills_blob = "\n".join(text.splitlines()[:60])

            parts = re.split(r"[\n,;|/•\u2022\t]+", skills_blob)
            cleaned: list[str] = []
            for p in parts:
                s = re.sub(r"\s+", " ", (p or "").strip())
                if not s:
                    continue
                if len(s) < 2 or len(s) > 40:
                    continue
                if re.search(r"\d{4,}", s):
                    continue
                cleaned.append(s)

            seen: set[str] = set()
            for s in cleaned:
                k = s.lower()
                if k in seen:
                    continue
                seen.add(k)
                extracted_skills.append(s)
            extracted_skills = extracted_skills[:50]
            _logger.info("Extracted %d skills from resume text", len(extracted_skills))
    except Exception:
        extracted_skills = []

    # ── Step 4: Update user profile ───────────────────────────────────────
    current_user.resume_url = f"/certificates/{unique_name}"

    if extracted_skills:
        existing = current_user.skills or []
        seen = {str(x).strip().lower() for x in existing if str(x).strip()}
        merged = list(existing)
        for s in extracted_skills:
            k = s.strip().lower()
            if not k or k in seen:
                continue
            seen.add(k)
            merged.append(s)
        current_user.skills = merged

    from app.models.interview import StudentProfile
    from app.models.auth import AuthUser

    user_result = await db.execute(select(AuthUser).where(AuthUser.id == current_user.id))
    user_exists = user_result.scalar_one_or_none()
    if user_exists is None:
        raise HTTPException(status_code=404, detail="User not found in database")

    try:
        profile_result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == current_user.id)
        )
        profile = profile_result.scalar_one_or_none()
        if profile:
            profile.resume_text = extracted_text
        else:
            db.add(StudentProfile(student_id=current_user.id, resume_text=extracted_text))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update student profile: {str(e)}") from e

    # ── Step 5: RAG Pipeline — Chunk → Embed → Store in pgvector ──────────
    rag_msg = ""
    if extracted_text and len(extracted_text.strip()) > 50:
        try:
            from app.services.chunking_service import ChunkingService
            from app.services.embedding_service import EmbeddingService
            from app.services.vector_store_service import VectorStoreService
            from app.models.rag import Document
            from sqlalchemy import delete

            _logger.info("RAG Pipeline: Starting for resume of user %s", current_user.id)

            # Delete old resume documents for this user (avoid duplicates on re-upload)
            old_docs = await db.execute(
                select(Document).where(
                    Document.user_id == current_user.id,
                    Document.title.like("Resume -%"),
                )
            )
            for old_doc in old_docs.scalars().all():
                await db.execute(delete(Document).where(Document.id == old_doc.id))
                _logger.info("Deleted old resume document: %s", old_doc.id)
            await db.flush()

            # Chunk the text
            chunker = ChunkingService()
            chunks = chunker.chunk_text(extracted_text)
            _logger.info("RAG Pipeline: Chunked resume into %d segments", len(chunks))

            if chunks:
                # Embed the chunks
                embedder = EmbeddingService()
                vectors = embedder.embed_batch(chunks)
                _logger.info("RAG Pipeline: Embedded %d chunks (dim=%d)", len(vectors), len(vectors[0]) if vectors else 0)

                # Store in pgvector
                store = VectorStoreService(db)
                doc_id = await store.store_document_with_embeddings(
                    user_id=current_user.id,
                    title=f"Resume - {current_user.name}",
                    raw_content=extracted_text,
                    chunks=chunks,
                    vectors=vectors,
                    content_type="application/pdf",
                    agent_type="career_roadmap",
                )
                _logger.info("RAG Pipeline: Stored resume document %s with %d chunks in pgvector", doc_id, len(chunks))
                rag_msg = f" RAG: {len(chunks)} chunks embedded."

            # Also create a structured profile summary document for richer retrieval
            profile_summary = _build_profile_summary(current_user, extracted_skills)
            if profile_summary:
                # Delete old profile summary
                old_profiles = await db.execute(
                    select(Document).where(
                        Document.user_id == current_user.id,
                        Document.title.like("Profile Summary -%"),
                    )
                )
                for old_doc in old_profiles.scalars().all():
                    await db.execute(delete(Document).where(Document.id == old_doc.id))
                await db.flush()

                profile_chunks = chunker.chunk_text(profile_summary)
                if profile_chunks:
                    profile_vectors = embedder.embed_batch(profile_chunks)
                    await store.store_document_with_embeddings(
                        user_id=current_user.id,
                        title=f"Profile Summary - {current_user.name}",
                        raw_content=profile_summary,
                        chunks=profile_chunks,
                        vectors=profile_vectors,
                        content_type="text/plain",
                        agent_type="career_roadmap",
                    )
                    _logger.info("RAG Pipeline: Stored profile summary with %d chunks", len(profile_chunks))

        except Exception as e:
            _logger.error("RAG Pipeline failed (non-fatal): %s", e, exc_info=True)
            # RAG failure is non-fatal — the resume is still saved
    else:
        _logger.warning("Skipping RAG pipeline — extracted text too short (%d chars)", len(extracted_text.strip()) if extracted_text else 0)

    try:
        await db.commit()
        _logger.info("Resume upload committed successfully for user %s", current_user.id)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save changes: {str(e)}") from e

    return MessageResponse(message=f"Resume uploaded successfully.{rag_msg}")


def _build_profile_summary(user, skills: list[str]) -> str:
    """Build a structured text summary of the user's profile for RAG embedding."""
    lines = [
        f"Student Name: {user.name}",
        f"Department: {user.department or 'Not specified'}",
        f"Semester: {user.semester or 'Not specified'}",
        f"Career Goal: {user.goal or 'Not specified'}",
        f"Skills: {', '.join(skills) if skills else 'None extracted'}",
    ]
    if hasattr(user, 'skills') and user.skills:
        all_skills = list(set((user.skills or []) + skills))
        lines[-1] = f"Skills: {', '.join(all_skills)}"
    return "\n".join(lines)

