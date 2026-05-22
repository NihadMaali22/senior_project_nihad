# ============================================================
# Async Database Engine & Session Factory
# ============================================================
"""
Provides the async SQLAlchemy engine and session factory.
Uses asyncpg as the PostgreSQL driver for high-performance async I/O.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Create the async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # Log SQL in debug mode
    pool_size=20,                 # Maximum persistent connections
    max_overflow=10,              # Extra connections when pool is full
    pool_pre_ping=True,           # Verify connections before use
    pool_recycle=3600,            # Recycle connections after 1 hour
    connect_args={
        "server_settings": {
            "client_encoding": "UTF8",  # Ensure UTF-8 for Arabic support
        }
    },
)

# Session factory — produces AsyncSession instances
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # Don't expire objects after commit
)


async def init_db() -> None:
    """
    Initialize the database by importing models and creating tables.
    In production, use Alembic migrations instead.
    """
    from app.db.models import Base  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables that don't exist yet
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully")


async def close_db() -> None:
    """Dispose of the database engine and close all connections."""
    await engine.dispose()
    logger.info("Database engine disposed")
