# ============================================================
# Conversation Memory — Session-based History
# ============================================================
"""
Manages conversation history stored in PostgreSQL.
Provides context from previous turns to the LLM for
multi-turn conversations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationHistory

logger = logging.getLogger(__name__)

# Maximum number of previous turns to include in context
MAX_HISTORY_TURNS = 10


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
    # Don't flush here — let the request handler commit
    logger.debug(f"Saved {role} message to session {session_id}")


async def get_conversation_history(
    session: AsyncSession,
    session_id: str,
    limit: int = MAX_HISTORY_TURNS,
) -> List[Dict[str, Any]]:
    """
    Retrieve recent conversation history for a session.
    Filters history to only include messages from the current active conversation segment
    (messages separated by no more than 30 minutes of inactivity).

    Args:
        session: Async database session.
        session_id: Conversation session identifier.
        limit: Maximum number of messages to retrieve.

    Returns:
        List of message dicts with 'role' and 'content'.
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

    from datetime import datetime, timezone
    
    # Inactivity threshold: 30 minutes
    INACTIVITY_THRESHOLD_MINUTES = 30
    
    active_messages = []
    # Compare against current time first. If the student hasn't typed for 30 mins, we start fresh.
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
    from sqlalchemy import func
    result = await session.execute(
        select(func.count())
        .select_from(ConversationHistory)
        .where(ConversationHistory.session_id == session_id)
    )
    return result.scalar() or 0
