# ============================================================
# Authentication Middleware — JWT Bearer Dependency
# ============================================================
"""
FastAPI dependencies for extracting and validating JWT tokens,
and enforcing role-based access control on endpoints.
"""

from __future__ import annotations

import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.schemas import TokenPayload
from app.auth.service import decode_access_token

logger = logging.getLogger(__name__)

# HTTP Bearer scheme — extracts "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenPayload:
    """
    Dependency that extracts and validates the JWT from the Authorization header.

    Raises:
        HTTPException 401 if no token or token is invalid/expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token received: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[TokenPayload]:
    """
    Optional authentication — returns None if no token is provided.
    Useful for endpoints that work with or without authentication.
    """
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def require_role(*allowed_roles: str):
    """
    Factory that creates a dependency requiring specific user roles.

    Usage:
        @router.get("/admin/stats", dependencies=[Depends(require_role("admin"))])
    """
    async def role_checker(
        user: TokenPayload = Depends(get_current_user),
    ) -> TokenPayload:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}",
            )
        return user

    return role_checker
