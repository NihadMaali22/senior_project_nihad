# ============================================================
# Conversation Memory — Session-based History
# ============================================================
"""
Manages conversation history stored in PostgreSQL.
Provides context from previous turns to the LLM for
multi-turn conversations.

TTL policy:
  - MAX_HISTORY_TURNS   : max messages returned per LLM context call (sliding window)
  - MAX_STORED_MESSAGES : hard cap per session in DB — oldest are pruned on each save
  - TTL_DAYS            : rows older than this are removed by purge_old_conversations()
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationHistory

logger = logging.getLogger(__name__)

# ── Tuneable limits ──────────────────────────────────────────
# How many recent messages are fed to the LLM as context
MAX_HISTORY_TURNS: int = 10

# Hard cap: maximum messages we keep per session in the DB.
# When exceeded the oldest messages are deleted immediately.
MAX_STORED_MESSAGES: int = 50

# Rows older than this are removed by purge_old_conversations()
TTL_DAYS: int = 30
# ─────────────────────────────────────────────────────────────


async def save_message(
    session: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    user_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Save a conversation message to the database.

    After inserting, enforces the MAX_STORED_MESSAGES cap per session:
    if the session now has more rows than the cap, the oldest excess rows
    are deleted immediately (in the same transaction).

    Args:
        session: Async database session.
        session_id: Conversation session identifier.
        role: 'user', 'assistant', or 'system'.
        content: The message content.
        user_id: Optional user ID for attribution.
        metadata: Optional metadata (query type, decision, etc.).
    """
    message = ConversationHistory(
        user_id=user_id,
        session_id=session_id,
        role=role,
        content=content,
        metadata_=metadata or {},
    )
    session.add(message)
    await session.flush()   # get the new row committed so COUNT is accurate

    # ── Enforce per-session hard cap ──────────────────────────
    count_result = await session.execute(
        select(func.count())
        .select_from(ConversationHistory)
        .where(ConversationHistory.session_id == session_id)
    )
    total = count_result.scalar() or 0

    if total > MAX_STORED_MESSAGES:
        excess = total - MAX_STORED_MESSAGES
        # Identify the IDs of the oldest messages to delete
        oldest_ids_result = await session.execute(
            select(ConversationHistory.id)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at.asc())
            .limit(excess)
        )
        ids_to_delete = [row[0] for row in oldest_ids_result.all()]

        if ids_to_delete:
            await session.execute(
                delete(ConversationHistory).where(
                    ConversationHistory.id.in_(ids_to_delete)
                )
            )
            logger.debug(
                f"[CONV TTL] Pruned {len(ids_to_delete)} old message(s) "
                f"from session {session_id} (cap={MAX_STORED_MESSAGES})"
            )
    # ── Don't commit here — let the request handler commit ───


async def get_conversation_history(
    session: AsyncSession,
    session_id: str,
    limit: int = MAX_HISTORY_TURNS,
) -> List[Dict[str, Any]]:
    """
    Retrieve recent conversation history for a session.
    Filters history to only include messages from the current active conversation segment
    (messages separated by no more than 30 minutes of inactivity).

    Uses the composite index (session_id, created_at) for O(log n) lookup.

    Args:
        session: Async database session.
        session_id: Conversation session identifier.
        limit: Maximum number of messages to retrieve (sliding window for LLM).

    Returns:
        List of message dicts with 'role', 'content', and 'created_at'.
    """
    result = await session.execute(
        select(ConversationHistory)
        .where(ConversationHistory.session_id == session_id)
        .order_by(ConversationHistory.created_at.desc())
        .limit(limit)
    )

    messages = result.scalars().all()
    if not messages:
        return []

    # Inactivity threshold: 30 minutes
    INACTIVITY_THRESHOLD_MINUTES = 30

    active_messages = []
    # Compare against current time first. If the student hasn't typed for 30 mins, start fresh.
    reference_time = datetime.now(timezone.utc)

    for msg in messages:
        msg_time = msg.created_at
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)

        gap_minutes = (reference_time - msg_time).total_seconds() / 60.0

        # If there's a gap of more than 30 minutes, this message belongs to a previous session
        if gap_minutes > INACTIVITY_THRESHOLD_MINUTES:
            break

        active_messages.append(msg)
        reference_time = msg_time

    # Reverse to get chronological order
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }
        for msg in reversed(active_messages)
    ]


async def get_conversation_context(
    session: AsyncSession,
    session_id: str,
    limit: int = MAX_HISTORY_TURNS,
) -> str:
    """
    Get conversation history formatted as a string for LLM context.

    Returns:
        Formatted conversation history string.
    """
    history = await get_conversation_history(session, session_id, limit)

    if not history:
        return ""

    lines = []
    for msg in history:
        role_label = "Student" if msg["role"] == "user" else "Advisor"
        lines.append(f"{role_label}: {msg['content']}")

    return "\n".join(lines)


async def get_session_count(
    session: AsyncSession,
    session_id: str,
) -> int:
    """Get the number of messages in a conversation session."""
    result = await session.execute(
        select(func.count())
        .select_from(ConversationHistory)
        .where(ConversationHistory.session_id == session_id)
    )
    return result.scalar() or 0


async def purge_old_conversations(
    session: AsyncSession,
    ttl_days: int = TTL_DAYS,
) -> int:
    """
    Delete all conversation rows older than `ttl_days` days.

    This is a maintenance function — call it from a scheduled job or
    the admin API to reclaim storage. The idx_conv_created_at index
    makes this query fast even on large tables.

    Args:
        session: Async database session.
        ttl_days: Rows older than this many days will be deleted.

    Returns:
        Number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    result = await session.execute(
        delete(ConversationHistory).where(
            ConversationHistory.created_at < cutoff
        )
    )
    deleted = result.rowcount or 0
    await session.commit()
    logger.info(
        f"[CONV PURGE] Deleted {deleted} conversation row(s) older than {ttl_days} days "
        f"(cutoff={cutoff.date()})"
    )
    return deleted
