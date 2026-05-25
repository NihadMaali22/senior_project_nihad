# ============================================================
# Robot Session API Routes
# ============================================================
"""
Two endpoints that implement the Robot QR login flow:

  POST /api/v1/robot/session
      Called by the robot → generates a one-time QR token linked
      to a specific student.

  POST /api/v1/robot/verify-session
      Called by the frontend after the student scans the QR →
      validates the token and returns a full JWT so the student
      is logged in automatically.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import create_access_token
from app.config import get_settings
from app.dependencies import get_db_session
from app.robot.schemas import (
    RobotSessionCreateRequest,
    RobotSessionCreateResponse,
    RobotSessionVerifyRequest,
    RobotSessionVerifyResponse,
)
from app.robot.service import create_robot_session, verify_robot_session

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/robot", tags=["Robot Session"])


# ============================================================
# POST /robot/session
# ============================================================
@router.post(
    "/session",
    response_model=RobotSessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QR Token for Robot",
    description=(
        "The robot calls this endpoint to obtain a short-lived QR token "
        "tied to the student it is currently serving. "
        "The returned `qr_data` should be encoded as a QR code and displayed "
        "on the robot screen for the student to scan."
    ),
)
async def create_session(
    request: RobotSessionCreateRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RobotSessionCreateResponse:
    """Generate a temporary QR token for a given student."""
    try:
        robot_session = await create_robot_session(
            session=db,
            student_id=request.student_id,
            ttl_seconds=request.ttl_seconds,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # Build the deep-link URL the frontend will handle
    qr_data = f"{settings.FRONTEND_URL}/robot-login?token={robot_session.token}"

    expires_in = int(
        (robot_session.expires_at - robot_session.created_at).total_seconds()
        if robot_session.created_at
        else request.ttl_seconds
    )

    return RobotSessionCreateResponse(
        token=robot_session.token,
        qr_data=qr_data,
        expires_at=robot_session.expires_at,
        expires_in=request.ttl_seconds,
    )


# ============================================================
# POST /robot/verify-session
# ============================================================
@router.post(
    "/verify-session",
    response_model=RobotSessionVerifyResponse,
    summary="Verify QR Token and Issue JWT",
    description=(
        "The frontend calls this endpoint after the student scans the QR code. "
        "If the token is valid (exists, unused, not expired), a standard JWT "
        "access token is issued — the student is now authenticated. "
        "Each token can only be used **once**."
    ),
)
async def verify_session(
    request: RobotSessionVerifyRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RobotSessionVerifyResponse:
    """Validate a QR token and return a JWT for the matched student."""
    try:
        user = await verify_robot_session(session=db, token=request.token)

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        # Token was already consumed
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except TimeoutError as exc:
        # Token expired — 410 Gone is the most semantically correct code
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        # Student has no linked user account
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # Issue a normal JWT — identical to what /auth/login returns
    jwt_token, expires_in = create_access_token(
        username=user.username,
        user_id=user.id,
        role=user.role,
        student_id=user.student_id,
    )

    return RobotSessionVerifyResponse(
        access_token=jwt_token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
    )
