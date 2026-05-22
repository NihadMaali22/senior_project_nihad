# ============================================================
# Authentication API Routes
# ============================================================
"""
Endpoints for user login, registration, and profile retrieval.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user, require_role
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenPayload,
    TokenResponse,
    UserResponse,
)
from app.auth.service import authenticate_user, create_access_token, hash_password
from app.db.models import User
from app.dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="User Login")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Authenticate with username and password to receive a JWT access token.

    Default accounts after seeding:
    - **admin** / admin123 (role: admin)
    - **khalid** / student123 (role: student, student_id: 1)
    - **noor** / student123 (role: student, student_id: 2)
    - **tariq** / student123 (role: student, student_id: 3)
    - **hassan** / student123 (role: student, student_id: 5)
    """
    user = await authenticate_user(session, request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_in = create_access_token(
        username=user.username,
        user_id=user.id,
        role=user.role,
        student_id=user.student_id,
    )

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User (Admin Only)",
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin")),
):
    """
    Create a new user account. Requires admin role.
    """
    # Check if username already exists
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' already exists",
        )

    new_user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        student_id=request.student_id,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()

    logger.info(f"New user registered: {request.username} (role: {request.role})")
    return new_user


@router.get("/me", response_model=UserResponse, summary="Get Current User Profile")
async def get_me(
    current_user: TokenPayload = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the profile of the currently authenticated user.
    """
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
