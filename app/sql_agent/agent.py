# ============================================================
# SQL Agent — Intelligent Query Dispatcher
# ============================================================
"""
The SQL Agent translates natural language academic queries into
structured database operations. It uses a template-based approach
where the LLM classifies the query type, and the agent executes
the corresponding pre-built, parameterized query.

This is intentionally NOT raw SQL generation — it's safer and
more predictable for a production system.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.sql_agent import queries

logger = logging.getLogger(__name__)

# ============================================================
# Query type definitions and their handlers
# ============================================================
QUERY_TYPE_MAP = {
    "get_student_info": {
        "description": "Get student profile and basic information",
        "requires_student_id": True,
        "keywords": ["student info", "my profile", "who am i", "my information", "my details"],
    },
    "get_gpa": {
        "description": "Get student's current GPA",
        "requires_student_id": True,
        "keywords": ["gpa", "grade point", "cumulative grade", "my grades", "academic performance"],
    },
    "get_completed_courses": {
        "description": "List all completed courses with grades",
        "requires_student_id": True,
        "keywords": ["completed courses", "courses i passed", "my courses", "finished courses", "course history"],
    },
    "get_current_enrollments": {
        "description": "Get current semester enrollments",
        "requires_student_id": True,
        "keywords": ["current courses", "enrolled", "this semester", "registered courses", "my schedule"],
    },
    "get_failed_courses": {
        "description": "Get courses the student has failed",
        "requires_student_id": True,
        "keywords": ["failed courses", "courses i failed", "failures", "retake"],
    },
    "get_prerequisites": {
        "description": "Get prerequisites for a specific course",
        "requires_student_id": False,
        "requires_course_code": True,
        "keywords": ["prerequisites", "prereq", "required before", "what do i need for"],
    },
    "check_prerequisites": {
        "description": "Check if student has met prerequisites for a course",
        "requires_student_id": True,
        "requires_course_code": True,
        "keywords": ["can i take", "eligible for", "prerequisites met", "allowed to register"],
    },
    "get_warnings": {
        "description": "Get academic warnings for the student",
        "requires_student_id": True,
        "keywords": ["warnings", "probation", "academic warning", "disciplinary"],
    },
    "get_graduation_requirements": {
        "description": "Get graduation requirements and progress",
        "requires_student_id": True,
        "keywords": ["graduation", "requirements", "graduate", "degree requirements", "how many hours"],
    },
    "get_remaining_courses": {
        "description": "Get courses still needed for graduation",
        "requires_student_id": True,
        "keywords": ["remaining courses", "courses left", "still need", "missing courses"],
    },
    "check_eligibility": {
        "description": "Full eligibility check for course registration",
        "requires_student_id": True,
        "requires_course_code": True,
        "keywords": ["can i register", "am i eligible", "can i enroll"],
    },
}


def extract_course_code(question: str) -> Optional[str]:
    """
    Extract a course code from a natural language question.

    Supports patterns like:
    - CS101, IT201, MATH101
    - "Internship 1" → CS490
    - "Internship 2" → CS491
    - "Capstone" → CS499
    """
    # Direct course code pattern (e.g., CS101, MATH201)
    match = re.search(r'\b([A-Z]{2,4}\d{3})\b', question.upper())
    if match:
        return match.group(1)

    # Natural language course names
    question_lower = question.lower()
    name_mappings = {
        "internship 2": "CS491",
        "internship 1": "CS490",
        "internship ii": "CS491",
        "internship i": "CS490",
        "capstone": "CS499",
        "capstone project": "CS499",
        "senior project": "CS499",
        "data structures": "CS201",
        "algorithms": "CS202",
        "database": "CS301",
        "databases": "CS301",
        "operating systems": "CS302",
        "software engineering": "CS310",
        "artificial intelligence": "CS350",
        "ai course": "CS350",
        "networking": "IT201",
        "cybersecurity": "IT301",
        "web development": "IT302",
        "calculus": "MATH101",
        "linear algebra": "MATH201",
        "statistics": "MATH202",
        "probability": "MATH202",
        "physics": "PHYS101",
        "circuit": "EE201",
        "digital logic": "EE301",
    }
    for name, code in name_mappings.items():
        if name in question_lower:
            return code

    return None


def classify_query_type(question: str) -> str:
    """
    Simple keyword-based classification of the SQL query type.
    This is used as a fallback when the LLM router sends to SQL.

    Returns:
        The query type key from QUERY_TYPE_MAP.
    """
    question_lower = question.lower()

    # Check for course-specific questions
    has_course = extract_course_code(question) is not None

    if has_course:
        if any(kw in question_lower for kw in ["can i take", "can i register", "eligible", "can i enroll"]):
            return "check_eligibility"
        if any(kw in question_lower for kw in ["prerequisites", "prereq", "required before"]):
            if any(kw in question_lower for kw in ["met", "have i", "did i"]):
                return "check_prerequisites"
            return "get_prerequisites"

    # Non-course-specific queries
    for query_type, info in QUERY_TYPE_MAP.items():
        for keyword in info["keywords"]:
            if keyword in question_lower:
                return query_type

    # Default to student info
    return "get_student_info"


async def execute_sql_query(
    session: AsyncSession,
    question: str,
    student_id: Optional[int] = None,
    query_type: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute the appropriate SQL query based on the question.

    Args:
        session: Async database session.
        question: The user's natural language question.
        student_id: The authenticated student's ID.
        query_type: Optionally pre-classified query type.

    Returns:
        Dict containing the query results and metadata.
    """
    if query_type is None:
        query_type = classify_query_type(question)

    logger.info(f"SQL Agent executing query_type='{query_type}' for student_id={student_id}")

    course_code = extract_course_code(question)

    try:
        if query_type == "get_student_info" and student_id:
            data = await queries.get_student_info(session, student_id)
        elif query_type == "get_gpa" and student_id:
            data = await queries.get_student_gpa(session, student_id)
        elif query_type == "get_completed_courses" and student_id:
            data = await queries.get_completed_courses(session, student_id)
        elif query_type == "get_current_enrollments" and student_id:
            data = await queries.get_current_enrollments(session, student_id)
        elif query_type == "get_failed_courses" and student_id:
            data = await queries.get_failed_courses(session, student_id)
        elif query_type == "get_prerequisites" and course_code:
            data = await queries.get_prerequisites_for_course(session, course_code)
        elif query_type == "check_prerequisites" and student_id and course_code:
            data = await queries.check_prerequisites_met(session, student_id, course_code)
        elif query_type == "get_warnings" and student_id:
            data = await queries.get_student_warnings(session, student_id)
        elif query_type == "get_graduation_requirements" and student_id:
            data = await queries.get_graduation_requirements(session, student_id)
        elif query_type == "get_remaining_courses" and student_id:
            data = await queries.get_remaining_courses(session, student_id)
        elif query_type == "check_eligibility" and student_id and course_code:
            data = await queries.check_course_eligibility(session, student_id, course_code)
        else:
            data = {"error": "Could not determine query. Please provide more details."}

        return {
            "query_type": query_type,
            "course_code": course_code,
            "data": data,
            "success": "error" not in (data if isinstance(data, dict) else {}),
        }

    except Exception as e:
        logger.error(f"SQL Agent error: {e}", exc_info=True)
        return {
            "query_type": query_type,
            "data": {"error": str(e)},
            "success": False,
        }
