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
        "keywords": [
            "student info", "my profile", "who am i", "my information", "my details",
            "معلوماتي", "ملفي الأكاديمي", "بياناتي", "من أنا", "تفاصيلي"
        ],
    },
    "get_gpa": {
        "description": "Get student's current GPA",
        "requires_student_id": True,
        "keywords": [
            "gpa", "grade point", "cumulative grade", "my grades", "academic performance",
            "معدلي", "المعدل التراكمي", "معدل", "علاماتي", "درجاتي"
        ],
    },
    "get_completed_courses": {
        "description": "List all completed courses with grades",
        "requires_student_id": True,
        "keywords": [
            "completed courses", "courses i passed", "my courses", "finished courses", "course history",
            "المواد التي أكملتها", "المواد المكتملة", "المواد التي نجحت بها", "سجل المواد", "المواد الناجح فيها"
        ],
    },
    "get_current_enrollments": {
        "description": "Get current semester enrollments",
        "requires_student_id": True,
        "keywords": [
            "current courses", "enrolled", "this semester", "registered courses", "my schedule",
            "المواد التي منزلها", "المواد منزلها", "المواد المسجلة حاليا", "جدولي", "المواد الحالية", "منزل", "مسجل", "منزلها", "مسجلها", "جدول الدراسي", "شو منزل"
        ],
    },
    "get_failed_courses": {
        "description": "Get courses the student has failed",
        "requires_student_id": True,
        "keywords": [
            "failed courses", "courses i failed", "failures", "retake", "fail",
            "المواد الراسبة", "المواد التي رسبت بها", "الإعادة", "الرسوب", "راسب", "رسبت"
        ],
    },
    "get_prerequisites": {
        "description": "Get prerequisites for a specific course",
        "requires_student_id": False,
        "requires_course_code": True,
        "keywords": [
            "prerequisites", "prereq", "required before", "what do i need for",
            "متطلبات", "متطلب سابق", "شروط المادة"
        ],
    },
    "check_prerequisites": {
        "description": "Check if student has met prerequisites for a course",
        "requires_student_id": True,
        "requires_course_code": True,
        "keywords": [
            "can i take", "eligible for", "prerequisites met", "allowed to register",
            "هل يمكنني أخذ", "هل يحق لي أخذ", "هل متطلبات مادة"
        ],
    },
    "get_warnings": {
        "description": "Get academic warnings for the student",
        "requires_student_id": True,
        "keywords": [
            "warnings", "probation", "academic warning", "disciplinary",
            "الإنذارات", "إنذار", "تنبيه"
        ],
    },
    "get_graduation_requirements": {
        "description": "Get graduation requirements and progress",
        "requires_student_id": True,
        "keywords": [
            "graduation", "requirements", "graduate", "degree requirements", "how many hours",
            "متطلبات التخرج", "التخرج", "كم ساعة متبقية للتخرج"
        ],
    },
    "get_remaining_courses": {
        "description": "Get courses still needed for graduation",
        "requires_student_id": True,
        "keywords": [
            "remaining courses", "courses left", "still need", "missing courses",
            "المواد المتبقية", "المواد اللي ضايلالي", "المواد الناقصة", "المواد المتبقية للتخرج"
        ],
    },
    "check_eligibility": {
        "description": "Full eligibility check for course registration",
        "requires_student_id": True,
        "requires_course_code": True,
        "keywords": [
            "can i register", "am i eligible", "can i enroll",
            "هل يمكنني تسجيل", "هل أنا مؤهل لتسجيل", "هل يحق لي تسجيل"
        ],
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
    # Direct course code pattern (e.g., CS111, MATH101, CS111L, CSE499A)
    match = re.search(r'\b([A-Z]{2,4}\d{3}[A-Z]?)\b', question.upper())
    if match:
        return match.group(1)

    # Natural language course names (both Arabic and English)
    question_lower = question.lower()
    name_mappings = {
        # Senior Projects
        "senior project 2": "CSE499B",
        "senior project 1": "CSE499A",
        "senior project ii": "CSE499B",
        "senior project i": "CSE499A",
        "senior project": "CSE499A",
        "مشروع تخرج 2": "CSE499B",
        "مشروع التخرج 2": "CSE499B",
        "مشروع تخرج 1": "CSE499A",
        "مشروع التخرج 1": "CSE499A",
        "مشروع تخرج": "CSE499A",
        "مشروع التخرج": "CSE499A",
        "سينيور": "CSE499A",
        "سينير": "CSE499A",

        # Internship
        "internship 1": "CS490",
        "internship 2": "CS491",
        "تدريب 1": "CS490",
        "التدريب 1": "CS490",
        "تدريب 2": "CS491",
        "التدريب 2": "CS491",
        "تدريب ميداني": "CS490",
        "التدريب الميداني": "CS490",
        "تدريب": "CS490",
        "التدريب": "CS490",

        # Capstone
        "capstone project": "CS499",
        "capstone": "CS499",

        # Core Courses
        "software engineering": "CS323",
        "software engineer": "CS323",
        "se": "CS323",
        "هندسة البرمجيات": "CS323",
        "هندسة برمجيات": "CS323",
        "برمجيات": "CS323",
        "سوفتوير": "CS323",
        "سوفتير": "CS323",

        "web programming": "CS322",
        "web development": "CS322",
        "برمجة الويب": "CS322",
        "برمجة ويب": "CS322",

        "embedded systems": "EE411",
        "embedded system": "EE411",
        "الأنظمة المدمجة": "EE411",
        "أنظمة مدمجة": "EE411",
        "امبيدد": "EE411",

        "operating systems": "CS321",
        "operating system": "CS321",
        "نظم التشغيل": "CS321",
        "نظم تشغيل": "CS321",
        "أوبيريتنج سيستم": "CS321",
        "اوبريتنج": "CS321",

        "microprocessor systems": "EE322",
        "microprocessor": "EE322",
        "المعالجات الدقيقة": "EE322",
        "معالجات دقيقة": "EE322",
        "مايكرو": "EE322",

        "computer network": "EE321",
        "computer networks": "EE321",
        "networks": "EE321",
        "شبكات الحاسوب": "EE321",
        "شبكات حاسوب": "EE321",
        "شبكات": "EE321",

        "advanced digital systems": "EE311",
        "أنظمة رقمية متقدمة": "EE311",

        "digital logic design": "EE211",
        "digital logic": "EE211",
        "تصميم المنطق الرقمي": "EE211",
        "منطق رقمي": "EE211",
        "لوجيك": "EE211",

        "computer organization": "EE221",
        "تنظيم الحاسوب": "EE221",
        "معمارية الحاسوب": "EE221",

        "data structures": "CS201",
        "data structure": "CS201",
        "هياكل البيانات": "CS201",
        "هياكل بيانات": "CS201",
        "داتا ستركشر": "CS201",
        "ستركشر": "CS201",

        "object oriented programming": "CS211",
        "oop": "CS211",
        "البرمجة كائنية التوجه": "CS211",
        "برمجة كائنية": "CS211",

        "programming fundamentals 2": "CS112",
        "برمجة 2": "CS112",
        "أساسيات البرمجة 2": "CS112",

        "programming fundamentals i": "CS111",
        "programming fundamentals 1": "CS111",
        "programming fundamentals": "CS111",
        "برمجة 1": "CS111",
        "أساسيات البرمجة 1": "CS111",

        "algorithms": "CS312",
        "algorithm analysis": "CS312",
        "خوارزميات": "CS312",

        "database": "CS311",
        "databases": "CS311",
        "قواعد البيانات": "CS311",
        "قواعد بيانات": "CS311",
        "داتابيس": "CS311",

        "electronics 2": "EE313",
        "electronics ii": "EE313",
        "إلكترونيات 2": "EE313",
        "الكترونيات 2": "EE313",

        "electronics 1": "EE312",
        "electronics i": "EE312",
        "إلكترونيات 1": "EE312",
        "الكترونيات 1": "EE312",

        "electrical circuit 2": "EE213",
        "electrical circuit ii": "EE213",
        "دوائر كهربائية 2": "EE213",
        "سيركت 2": "EE213",

        "electrical circuit 1": "EE212",
        "electrical circuit i": "EE212",
        "دوائر كهربائية 1": "EE212",
        "سيركت 1": "EE212",

        "signals and systems": "EE222",
        "إشارات وأنظمة": "EE222",
        "اشارات وانظمة": "EE222",

        "probability": "MATH302",
        "احتمالات": "MATH302",

        "numerical methods": "MATH301",
        "طرق عددية": "MATH301",

        "discrete math": "MATH211",
        "discrete mathematics": "MATH211",
        "رياضيات متقطعة": "MATH211",

        "calculus 2": "MATH102",
        "calculus ii": "MATH102",
        "تفاضل وتكامل 2": "MATH102",
        "كلكولس 2": "MATH102",

        "calculus 1": "MATH101",
        "calculus i": "MATH101",
        "تفاضل وتكامل 1": "MATH101",
        "كلكولس 1": "MATH101",

        "linear algebra": "MATH201",
        "جبر خطي": "MATH201",

        "physics 2": "PHYS102",
        "physics ii": "PHYS102",
        "فيزياء 2": "PHYS102",

        "physics 1": "PHYS101",
        "physics i": "PHYS101",
        "فيزياء 1": "PHYS101",

        "technical writing": "EL201",
        "كتابة تقنية": "EL201",

        "intermediate english": "EL101",
        "إنجليزي متوسط": "EL101",

        "advanced english": "EL102",
        "إنجليزي متقدم": "EL102",
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
        if any(kw in question_lower for kw in ["can i take", "can i register", "eligible", "can i enroll", "تسجيل", "أسجل", "مؤهل", "يحق لي", "هل يمكنني"]):
            return "check_eligibility"
        if any(kw in question_lower for kw in ["prerequisites", "prereq", "required before", "متطلب", "متطلبات", "قبل"]):
            if any(kw in question_lower for kw in ["met", "have i", "did i", "أخذت", "خلصت", "أنهيت"]):
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
            data = await queries.get_full_student_profile(session, student_id)
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
