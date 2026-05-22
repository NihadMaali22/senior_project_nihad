# ============================================================
# Authentication Pydantic Schemas
# ============================================================
"""
Request and response models for authentication endpoints.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=4, max_length=200)


class TokenResponse(BaseModel):
    """JWT token response after successful login."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: int
    username: str
    role: str
    student_id: Optional[int] = None


class RegisterRequest(BaseModel):
    """Registration request (admin-only)."""
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=200)
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = Field(default="student", pattern="^(admin|student|advisor)$")
    student_id: Optional[int] = None


class UserResponse(BaseModel):
    """Public user information."""
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    student_id: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


class TokenPayload(BaseModel):
    """JWT token payload structure."""
    sub: str           # username
    user_id: int
    role: str
    student_id: Optional[int] = None
    exp: int           # expiration timestamp
