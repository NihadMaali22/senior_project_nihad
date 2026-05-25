# ============================================================
# Robot Session Schemas — Pydantic Models
# ============================================================
"""
Request/Response schemas for the robot QR session endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# POST /robot/session  (Robot → Backend)
# ============================================================
class RobotSessionCreateRequest(BaseModel):
    """
    Sent by the robot to request a new QR token.
    The robot must know the student_id it is serving.
    """
    student_id: int = Field(..., description="The student ID the robot is currently serving")
    ttl_seconds: int = Field(
        default=300,
        ge=30,
        le=900,
        description="Token lifetime in seconds (default: 5 min, max: 15 min)",
    )


class RobotSessionCreateResponse(BaseModel):
    """Returned to the robot so it can render the QR code."""
    token: str = Field(..., description="UUID token to embed in the QR code")
    qr_data: str = Field(..., description="Full URL the QR code should encode")
    expires_at: datetime = Field(..., description="Token expiry timestamp (UTC)")
    expires_in: int = Field(..., description="Seconds until expiry")


# ============================================================
# POST /robot/verify-session  (Frontend → Backend)
# ============================================================
class RobotSessionVerifyRequest(BaseModel):
    """
    Sent by the frontend after the student scans the QR code.
    """
    token: str = Field(..., min_length=10, description="The QR token scanned by the student")


class RobotSessionVerifyResponse(BaseModel):
    """
    Returned to the frontend — equivalent to a normal login response.
    The frontend can store the JWT and treat the student as logged in.
    """
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer")
    expires_in: int = Field(..., description="JWT lifetime in seconds")
    user_id: int
    username: str
    role: str
    student_id: Optional[int] = None
