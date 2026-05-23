# ============================================================
# Authentication Service — JWT & Password Management
# ============================================================
"""
Handles password hashing/verification and JWT token creation/validation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload
from app.config import get_settings
from app.db.models import User

logger = logging.getLogger(__name__)
settings = get_settings()

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(
    username: str,
    user_id: int,
    role: str,
    student_id: Optional[int] = None,
) -> tuple[str, int]:
    """
    Create a signed JWT access token.

    Returns:
        Tuple of (token_string, expiration_seconds)
    """
    expires_delta = timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": username,
        "user_id": user_id,
        "role": role,
        "student_id": student_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT access token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return TokenPayload(**payload)


async def authenticate_user(
    session: AsyncSession,
    username: str,
    password: str,
) -> Optional[User]:
    """
    Authenticate a user by username and password.

    Returns:
        The User object if authentication succeeds, None otherwise.
    """
    result = await session.execute(
        select(User).where(User.username == username, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"Login attempt for non-existent user: {username}")
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {username}")
        return None

    logger.info(f"User authenticated successfully: {username}")
    return user
