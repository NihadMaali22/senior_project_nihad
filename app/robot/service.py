# ============================================================
# Robot Session Service — Business Logic
# ============================================================
"""
Handles creation and verification of temporary QR session tokens.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RobotSession, Student, User

logger = logging.getLogger(__name__)


# ============================================================
# Token Creation
# ============================================================
async def create_robot_session(
    session: AsyncSession,
    student_id: int,
    ttl_seconds: int = 300,
) -> RobotSession:
    """
    Create a new temporary QR token for a student.

    Args:
        session:     Async DB session.
        student_id:  The student this token is issued for.
        ttl_seconds: How many seconds until the token expires.

    Returns:
        The newly created RobotSession ORM object.

    Raises:
        ValueError: If the student_id does not exist in the DB.
    """
    # Verify the student exists
    student_result = await session.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    if student is None:
        raise ValueError(f"Student with id={student_id} not found")

    # Generate a cryptographically secure token (URL-safe, 32 bytes → 43 chars)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    robot_session = RobotSession(
        token=token,
        student_id=student_id,
        expires_at=expires_at,
        is_used=False,
    )
    session.add(robot_session)
    await session.flush()  # Get ID without committing

    logger.info(
        f"Robot QR session created | student_id={student_id} | "
        f"token={token[:8]}... | expires_at={expires_at.isoformat()}"
    )
    return robot_session


# ============================================================
# Token Verification
# ============================================================
async def verify_robot_session(
    session: AsyncSession,
    token: str,
) -> User:
    """
    Verify a QR token and return the associated User account.

    Validation steps:
    1. Token exists in DB
    2. Token has not been used yet
    3. Token has not expired
    4. A User account linked to the student exists and is active

    After successful verification the token is marked as used.

    Args:
        session: Async DB session.
        token:   The raw token string from the QR code.

    Returns:
        The User ORM object for the matched student.

    Raises:
        LookupError:   Token not found.
        PermissionError: Token already used.
        TimeoutError:  Token expired.
        RuntimeError:  No active user account found for this student.
    """
    # 1. Find the token
    result = await session.execute(
        select(RobotSession).where(RobotSession.token == token)
    )
    robot_session: Optional[RobotSession] = result.scalar_one_or_none()

    if robot_session is None:
        logger.warning(f"Robot session verify: token not found | token={token[:8]}...")
        raise LookupError("Token not found")

    # 2. Check if already used
    if robot_session.is_used:
        logger.warning(
            f"Robot session verify: token already used | token={token[:8]}..."
        )
        raise PermissionError("Token has already been used")

    # 3. Check expiry
    now = datetime.now(timezone.utc)
    if now > robot_session.expires_at:
        logger.warning(
            f"Robot session verify: token expired | token={token[:8]}... | "
            f"expired_at={robot_session.expires_at.isoformat()}"
        )
        raise TimeoutError("Token has expired")

    # 4. Find the User account for this student
    user_result = await session.execute(
        select(User).where(
            User.student_id == robot_session.student_id,
            User.is_active == True,  # noqa: E712
        )
    )
    user: Optional[User] = user_result.scalar_one_or_none()

    if user is None:
        logger.error(
            f"Robot session verify: no active user for student_id={robot_session.student_id}"
        )
        raise RuntimeError(
            f"No active user account found for student_id={robot_session.student_id}"
        )

    # 5. Mark token as used
    robot_session.is_used = True
    robot_session.used_at = now
    robot_session.user_id = user.id
    await session.flush()

    logger.info(
        f"Robot session verified | student_id={robot_session.student_id} | "
        f"user={user.username} | token={token[:8]}..."
    )
    return user
