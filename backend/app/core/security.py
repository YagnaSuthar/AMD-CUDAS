"""
Security utilities: password hashing, JWT tokens, and FastAPI auth dependencies.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

# ── Password Hashing ─────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        plain_bytes = plain.encode('utf-8')
        hashed_bytes = hashed.encode('utf-8')
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


# ── JWT Tokens ────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )


# ── FastAPI Dependencies ──────────────────────────────────────────────────

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Decode JWT, return the AuthUser record.
    For CUDAS_ADMIN (static account), return a dict instead.
    """
    payload = decode_access_token(token)
    email: str = payload.get("sub")
    role: str = payload.get("role")

    if not email or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Static CUDAS admin — no DB lookup
    if role == "CUDAS_ADMIN":
        if email == settings.CUDAS_ADMIN_EMAIL:
            return {
                "id": None,
                "name": "CUDAS Admin",
                "email": email,
                "role": "CUDAS_ADMIN",
                "is_verified": True,
                "parent_id": None,
            }
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    # Regular user — DB lookup
    from app.models.auth import AuthUser  # deferred to avoid circular imports

    result = await db.execute(select(AuthUser).where(AuthUser.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


class RoleChecker:
    """
    FastAPI dependency that restricts access to specific roles.
    Usage:  allowed = Depends(RoleChecker(["CUDAS_ADMIN", "COLLEGE_PRINCIPAL"]))
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user=Depends(get_current_user)):
        role = current_user.role if hasattr(current_user, "role") else current_user.get("role")
        if role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {self.allowed_roles}",
            )
        return current_user


# ── Role Aliases ──────────────────────────────────────────────────────────

principal_or_above = RoleChecker(["CUDAS_ADMIN", "COLLEGE_PRINCIPAL", "HOD", "FACULTY"])
principal_only = RoleChecker(["COLLEGE_PRINCIPAL"])
hod_only = RoleChecker(["HOD"])
faculty_only = RoleChecker(["FACULTY"])
student_only = RoleChecker(["STUDENT"])
