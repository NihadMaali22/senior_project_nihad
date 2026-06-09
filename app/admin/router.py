# ============================================================
# Admin Dashboard API
# ============================================================
"""
Admin-only endpoints for system management, statistics,
student management, and data seeding.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import require_role
from app.auth.schemas import TokenPayload
from app.db.models import (
    ConversationHistory,
    Course,
    Enrollment,
    Student,
    Warning,
)
from app.db.schemas import StudentResponse, SystemStats
from app.dependencies import get_db_session
from app.rag.document_store import get_document_count

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get(
    "/stats",
    response_model=SystemStats,
    summary="System Statistics",
    description="Get an overview of system statistics.",
)
async def get_system_stats(
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin")),
):
    """Get system-wide statistics for the admin dashboard."""
    # Run all database count queries and the Qdrant document count concurrently
    (
        students_res,
        courses_res,
        enrollments_res,
        conversations_res,
        warnings_res,
        total_documents,
    ) = await asyncio.gather(
        session.execute(select(func.count()).select_from(Student)),
        session.execute(select(func.count()).select_from(Course)),
        session.execute(select(func.count()).select_from(Enrollment)),
        session.execute(select(func.count(func.distinct(ConversationHistory.session_id)))),
        session.execute(
            select(func.count())
            .select_from(Warning)
            .where(Warning.is_resolved == False)  # noqa: E712
        ),
        asyncio.to_thread(get_document_count),
    )

    total_students = students_res.scalar() or 0
    total_courses = courses_res.scalar() or 0
    total_enrollments = enrollments_res.scalar() or 0
    total_conversations = conversations_res.scalar() or 0
    active_warnings = warnings_res.scalar() or 0


    return SystemStats(
        total_students=total_students,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_documents=total_documents,
        total_conversations=total_conversations,
        active_warnings=active_warnings,
    )


@router.get(
    "/students",
    response_model=list[StudentResponse],
    summary="List All Students",
    description="Get a list of all students in the system.",
)
async def list_students(
    status_filter: str = None,
    department_code: str = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin", "advisor")),
):
    """List students with optional filtering."""
    query = select(Student)

    if status_filter:
        query = query.where(Student.status == status_filter)

    if department_code:
        from app.db.models import Department
        dept_subquery = select(Department.id).where(Department.code == department_code.upper())
        query = query.where(Student.department_id.in_(dept_subquery))

    query = query.offset(offset).limit(limit).order_by(Student.id)

    result = await session.execute(query)
    students = result.scalars().all()
    return students


@router.get(
    "/students/{student_id}",
    response_model=StudentResponse,
    summary="Get Student Details",
    description="Get detailed information for a specific student.",
)
async def get_student(
    student_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin", "advisor")),
):
    """Get a student's full profile."""
    result = await session.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} not found",
        )
    return student


@router.post(
    "/seed",
    summary="Seed Database",
    description="Populate the database with sample data. Requires admin role.",
)
async def seed_database(
    _: TokenPayload = Depends(require_role("admin")),
):
    """Trigger database seeding with sample data."""
    try:
        from app.db.seed import run_seed
        await run_seed()
        return {"message": "Database seeded successfully"}
    except Exception as e:
        logger.error(f"Seeding failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database seeding failed: {str(e)}",
        )


@router.post(
    "/ingest",
    summary="Trigger Document Ingestion",
    description="Ingest all regulation documents from the data directory.",
)
async def trigger_ingestion(
    _: TokenPayload = Depends(require_role("admin")),
):
    """Trigger ingestion of all regulation documents."""
    try:
        from app.rag.ingestion import ingest_documents
        result = await ingest_documents()
        return result
    except Exception as e:
        logger.error(f"Ingestion trigger failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.post(
    "/students/{student_id}/recalculate-gpa",
    summary="Recalculate Student GPA",
    description=(
        "Recompute GPA, total_credits, and academic_standing for a single student "
        "from their actual enrollment records and persist the result to the database. "
        "Use this after any grade change or administrative correction."
    ),
)
async def recalculate_student_gpa(
    student_id: int,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin", "advisor")),
):
    """Recalculate and sync GPA for a single student."""
    from app.sql_agent.queries import recalculate_student_stats

    result = await recalculate_student_stats(session, student_id)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    return result


@router.post(
    "/students/recalculate-all-gpa",
    summary="Recalculate GPA for All Students",
    description=(
        "Recompute GPA, total_credits, and academic_standing for ALL students "
        "from their enrollment records. Use after bulk grade imports or database seeding."
    ),
)
async def recalculate_all_gpa(
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin")),
):
    """Recalculate and sync GPA for all students in the system."""
    from app.sql_agent.queries import recalculate_all_students_stats

    result = await recalculate_all_students_stats(session)
    return result


@router.post(
    "/conversations/purge",
    summary="Purge Old Conversations",
    description=(
        "Delete all conversation history rows older than `ttl_days` days "
        "(default: 30). Use this for periodic storage maintenance."
    ),
)
async def purge_conversations(
    ttl_days: int = 30,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin")),
):
    """Delete old conversation history rows to reclaim DB storage."""
    from app.memory.conversation import purge_old_conversations

    deleted = await purge_old_conversations(session, ttl_days=ttl_days)
    return {
        "deleted_rows": deleted,
        "ttl_days": ttl_days,
        "message": f"Deleted {deleted} conversation row(s) older than {ttl_days} days.",
    }
