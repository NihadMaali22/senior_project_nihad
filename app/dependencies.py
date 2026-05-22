# ============================================================
# FastAPI Dependency Injection
# ============================================================
"""
Shared dependencies injected into FastAPI route handlers.
Provides database sessions, current user context, and service instances.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session for each request.
    Automatically commits on success or rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
