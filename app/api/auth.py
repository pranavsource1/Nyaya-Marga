"""Authentication endpoints."""
from datetime import timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_role,
)
from app.core.database import get_db
from app.core.config import settings
from app.models.domain_models import User, UserRole

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# Schemas
class TokenRequest(BaseModel):
    """Login request."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    email: str
    full_name: str


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: str
    password: str
    full_name: str
    department: str
    role: str = "viewer"  # Default to viewer


class MeResponse(BaseModel):
    """Current user info."""
    user_id: str
    email: str
    full_name: str
    department: str
    role: str


# Endpoints

@router.post("/token", response_model=TokenResponse)
async def login(body: TokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Login endpoint.
    POST /api/v1/auth/token
    Returns JWT token.
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Validate user exists and password is correct
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token_expires = timedelta(hours=settings.access_token_expire_hours)
    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "role": user.role.value,
            "email": user.email,
            "dept": user.department
        },
        expires_delta=access_token_expires
    )

    # Update last login
    user.last_login_at = __import__("datetime").datetime.utcnow()
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        role=user.role.value,
        email=user.email,
        full_name=user.full_name
    )


@router.get("/me", response_model=MeResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current user information.
    Protected endpoint - requires valid JWT.
    """
    return MeResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        department=current_user.get("dept", ""),
        role=current_user["role"]
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    body: UserRegisterRequest,
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user (admin only).
    POST /api/v1/auth/register
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate role
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join([r.value for r in UserRole])}"
        )

    # Create new user
    hashed_password = hash_password(body.password)
    new_user = User(
        email=body.email,
        password_hash=hashed_password,
        full_name=body.full_name,
        department=body.department,
        role=role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create access token for new user
    access_token = create_access_token(
        data={
            "user_id": str(new_user.id),
            "role": new_user.role.value,
            "email": new_user.email,
            "dept": new_user.department
        },
        expires_delta=timedelta(hours=settings.access_token_expire_hours)
    )

    return TokenResponse(
        access_token=access_token,
        user_id=str(new_user.id),
        role=new_user.role.value,
        email=new_user.email,
        full_name=new_user.full_name
    )
