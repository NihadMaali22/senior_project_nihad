# ============================================================
# Pre-built SQL Queries — Safe, Parameterized Data Access
# ============================================================
"""
All SQL queries for the academic assistant use SQLAlchemy ORM.
These are safe, parameterized queries that avoid SQL injection.
Each function returns structured data dictionaries.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Course,
    Department,
    Enrollment,
    GraduationRequirement,
    Instructor,
    Prerequisite,
    RequiredCourse,
    Student,
    Warning,
)

logger = logging.getLogger(__name__)


async def get_student_info(session: AsyncSession, student_id: int) -> Optional[dict[str, Any]]:
    """
    Retrieve complete student profile including department info.

    Returns:
        Dict with student details or None if not found.
    """
    result = await session.execute(
        select(Student)
        .options(selectinload(Student.department))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        return None

    return {
        "id": student.id,
        "student_number": student.student_number,
        "full_name": student.full_name,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "department": student.department.name if student.department else None,
        "department_code": student.department.code if student.department else None,
        "enrollment_year": student.enrollment_year,
        "total_credits": student.total_credits,
        "gpa": float(student.gpa),
        "status": student.status,
        "academic_standing": student.academic_standing,
    }


async def get_student_gpa(session: AsyncSession, student_id: int) -> Optional[dict[str, Any]]:
    """Get just the GPA and credit info for a student."""
    result = await session.execute(
        select(
            Student.gpa,
            Student.total_credits,
            Student.academic_standing,
            Student.student_number,
            Student.first_name,
            Student.last_name,
        ).where(Student.id == student_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    return {
        "student_number": row.student_number,
        "full_name": f"{row.first_name} {row.last_name}",
        "gpa": float(row.gpa),
        "total_credits": row.total_credits,
        "academic_standing": row.academic_standing,
    }


async def get_completed_courses(
    session: AsyncSession,
    student_id: int,
) -> list[dict[str, Any]]:
    """
    Get all courses a student has completed (passed).

    Returns:
        List of completed course records with grades.
    """
    result = await session.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "completed",
        )
        .order_by(Enrollment.academic_year, Enrollment.semester)
    )

    courses = []
    for enrollment, course in result.all():
        courses.append({
            "course_code": course.code,
            "course_name": course.name,
            "credits": course.credits,
            "grade": enrollment.grade,
            "grade_points": float(enrollment.grade_points) if enrollment.grade_points else None,
            "semester": enrollment.semester,
            "academic_year": enrollment.academic_year,
        })
    return courses


async def get_current_enrollments(
    session: AsyncSession,
    student_id: int,
) -> list[dict[str, Any]]:
    """Get courses the student is currently enrolled in (in_progress)."""
    result = await session.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status.in_(["enrolled", "in_progress"]),
        )
    )

    return [
        {
            "course_code": course.code,
            "course_name": course.name,
            "credits": course.credits,
            "semester": enrollment.semester,
            "academic_year": enrollment.academic_year,
            "status": enrollment.status,
        }
        for enrollment, course in result.all()
    ]


async def get_failed_courses(
    session: AsyncSession,
    student_id: int,
) -> list[dict[str, Any]]:
    """Get all courses a student has failed."""
    result = await session.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "failed",
        )
    )

    return [
        {
            "course_code": course.code,
            "course_name": course.name,
            "grade": enrollment.grade,
            "semester": enrollment.semester,
            "academic_year": enrollment.academic_year,
        }
        for enrollment, course in result.all()
    ]


async def get_prerequisites_for_course(
    session: AsyncSession,
    course_code: str,
) -> dict[str, Any]:
    """
    Get all prerequisites for a given course code.

    Returns:
        Dict containing course info and its prerequisite list.
    """
    # Find the course
    course_result = await session.execute(
        select(Course).where(Course.code == course_code.upper())
    )
    course = course_result.scalar_one_or_none()
    if course is None:
        return {"error": f"Course '{course_code}' not found"}

    # Get prerequisites
    prereq_result = await session.execute(
        select(Prerequisite, Course)
        .join(Course, Prerequisite.prerequisite_id == Course.id)
        .where(Prerequisite.course_id == course.id)
    )

    prereqs = [
        {
            "prerequisite_code": prereq_course.code,
            "prerequisite_name": prereq_course.name,
            "min_grade": prereq.min_grade,
            "is_mandatory": prereq.is_mandatory,
        }
        for prereq, prereq_course in prereq_result.all()
    ]

    return {
        "course_code": course.code,
        "course_name": course.name,
        "credits": course.credits,
        "min_gpa": float(course.min_gpa),
        "min_credits": course.min_credits,
        "prerequisites": prereqs,
    }


async def check_prerequisites_met(
    session: AsyncSession,
    student_id: int,
    course_code: str,
) -> dict[str, Any]:
    """
    Check whether a student has met ALL prerequisites for a course.

    Returns:
        Dict with overall status and per-prerequisite details.
    """
    # Get the course
    course_result = await session.execute(
        select(Course).where(Course.code == course_code.upper())
    )
    course = course_result.scalar_one_or_none()
    if course is None:
        return {"error": f"Course '{course_code}' not found", "all_met": False}

    # Get prerequisites
    prereq_result = await session.execute(
        select(Prerequisite, Course)
        .join(Course, Prerequisite.prerequisite_id == Course.id)
        .where(Prerequisite.course_id == course.id)
    )
    prerequisites = prereq_result.all()

    if not prerequisites:
        return {
            "course_code": course.code,
            "all_met": True,
            "prerequisites": [],
            "message": "No prerequisites required for this course.",
        }

    # Grade ordering for comparison
    grade_order = {"A": 10, "A-": 9, "B+": 8, "B": 7, "B-": 6, "C+": 5, "C": 4, "C-": 3, "D+": 2, "D": 1, "F": 0}

    results = []
    all_met = True

    for prereq, prereq_course in prerequisites:
        # Check if student completed this prerequisite
        enrollment_result = await session.execute(
            select(Enrollment)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.course_id == prereq.prerequisite_id,
                Enrollment.status == "completed",
            )
            .order_by(Enrollment.grade_points.desc())
            .limit(1)
        )
        enrollment = enrollment_result.scalar_one_or_none()

        if enrollment is None:
            met = False
            all_met = False
            status = "NOT_TAKEN"
            grade_achieved = None
        else:
            grade_achieved = enrollment.grade
            min_grade_val = grade_order.get(prereq.min_grade, 0)
            achieved_val = grade_order.get(enrollment.grade, 0)
            met = achieved_val >= min_grade_val
            status = "MET" if met else "NOT_MET"
            if not met:
                all_met = False

        results.append({
            "prerequisite_code": prereq_course.code,
            "prerequisite_name": prereq_course.name,
            "min_grade_required": prereq.min_grade,
            "grade_achieved": grade_achieved,
            "is_mandatory": prereq.is_mandatory,
            "status": status,
            "met": met,
        })

    return {
        "course_code": course.code,
        "course_name": course.name,
        "all_met": all_met,
        "prerequisites": results,
    }


async def get_student_warnings(
    session: AsyncSession,
    student_id: int,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """Get academic warnings for a student."""
    query = select(Warning).where(Warning.student_id == student_id)
    if active_only:
        query = query.where(Warning.is_resolved == False)  # noqa: E712
    query = query.order_by(Warning.created_at.desc())

    result = await session.execute(query)
    return [
        {
            "id": w.id,
            "warning_type": w.warning_type,
            "description": w.description,
            "semester": w.semester,
            "academic_year": w.academic_year,
            "is_resolved": w.is_resolved,
        }
        for w in result.scalars().all()
    ]


async def get_graduation_requirements(
    session: AsyncSession,
    student_id: int,
) -> Optional[dict[str, Any]]:
    """
    Get graduation requirements for the student's department.
    Also checks progress toward graduation.
    """
    # Get student with department
    student_result = await session.execute(
        select(Student).where(Student.id == student_id)
    )
    student = student_result.scalar_one_or_none()
    if student is None or student.department_id is None:
        return None

    # Get requirements for this department
    req_result = await session.execute(
        select(GraduationRequirement)
        .where(GraduationRequirement.department_id == student.department_id)
        .limit(1)
    )
    req = req_result.scalar_one_or_none()
    if req is None:
        return {"error": "No graduation requirements defined for this department."}

    # Get required courses
    required_result = await session.execute(
        select(RequiredCourse, Course)
        .join(Course, RequiredCourse.course_id == Course.id)
        .where(RequiredCourse.graduation_req_id == req.id)
    )

    # Get student's completed courses
    completed_result = await session.execute(
        select(Enrollment.course_id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "completed",
        )
    )
    completed_ids = {row[0] for row in completed_result.all()}

    required_courses = []
    for rc, course in required_result.all():
        required_courses.append({
            "course_code": course.code,
            "course_name": course.name,
            "credits": course.credits,
            "is_core": rc.is_core,
            "completed": course.id in completed_ids,
        })

    completed_required = sum(1 for c in required_courses if c["completed"])
    total_required = len(required_courses)

    return {
        "department": student.department_id,
        "min_total_credits": req.min_total_credits,
        "min_gpa": float(req.min_gpa),
        "min_major_credits": req.min_major_credits,
        "max_years": req.max_years,
        "requires_internship": req.requires_internship,
        "requires_capstone": req.requires_capstone,
        "student_credits": student.total_credits,
        "student_gpa": float(student.gpa),
        "credits_remaining": max(0, req.min_total_credits - student.total_credits),
        "gpa_met": float(student.gpa) >= float(req.min_gpa),
        "required_courses": required_courses,
        "required_courses_completed": completed_required,
        "required_courses_total": total_required,
    }


async def get_remaining_courses(
    session: AsyncSession,
    student_id: int,
) -> list[dict[str, Any]]:
    """Get courses still needed for graduation."""
    grad_info = await get_graduation_requirements(session, student_id)
    if grad_info is None or "error" in grad_info:
        return []

    return [
        {
            "course_code": c["course_code"],
            "course_name": c["course_name"],
            "credits": c["credits"],
            "is_core": c["is_core"],
        }
        for c in grad_info.get("required_courses", [])
        if not c["completed"]
    ]


async def get_course_info(
    session: AsyncSession,
    course_code: str,
) -> Optional[dict[str, Any]]:
    """Get detailed information about a specific course."""
    result = await session.execute(
        select(Course)
        .options(selectinload(Course.department))
        .where(Course.code == course_code.upper())
    )
    course = result.scalar_one_or_none()
    if course is None:
        return None

    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "credits": course.credits,
        "department": course.department.name if course.department else None,
        "course_type": course.course_type,
        "min_gpa": float(course.min_gpa),
        "min_credits": course.min_credits,
        "description": course.description,
    }


async def check_course_eligibility(
    session: AsyncSession,
    student_id: int,
    course_code: str,
) -> dict[str, Any]:
    """
    Comprehensive check of whether a student can register for a course.
    Checks: prerequisites, GPA requirement, credit requirement, and enrollment status.
    """
    # Get student info
    student_info = await get_student_info(session, student_id)
    if student_info is None:
        return {"eligible": False, "reason": "Student not found."}

    # Get course info
    course_info = await get_course_info(session, course_code)
    if course_info is None:
        return {"eligible": False, "reason": f"Course '{course_code}' not found."}

    checks = []
    eligible = True

    # 1. Check student status
    if student_info["status"] != "active":
        eligible = False
        checks.append({
            "check": "student_status",
            "passed": False,
            "detail": f"Student status is '{student_info['status']}'. Must be 'active' to register.",
        })
    else:
        checks.append({"check": "student_status", "passed": True, "detail": "Student is active."})

    # 2. Check academic standing
    if student_info["academic_standing"] == "dismissal":
        eligible = False
        checks.append({
            "check": "academic_standing",
            "passed": False,
            "detail": "Student is dismissed. Cannot register for courses.",
        })
    else:
        checks.append({
            "check": "academic_standing",
            "passed": True,
            "detail": f"Academic standing: {student_info['academic_standing']}",
        })

    # 3. Check minimum GPA
    if course_info["min_gpa"] > 0 and student_info["gpa"] < course_info["min_gpa"]:
        eligible = False
        checks.append({
            "check": "min_gpa",
            "passed": False,
            "detail": f"Course requires GPA ≥ {course_info['min_gpa']}, student has {student_info['gpa']}.",
        })
    else:
        checks.append({
            "check": "min_gpa",
            "passed": True,
            "detail": f"GPA requirement met ({student_info['gpa']} ≥ {course_info['min_gpa']}).",
        })

    # 4. Check minimum credits
    if course_info["min_credits"] > 0 and student_info["total_credits"] < course_info["min_credits"]:
        eligible = False
        checks.append({
            "check": "min_credits",
            "passed": False,
            "detail": f"Course requires ≥ {course_info['min_credits']} credits, student has {student_info['total_credits']}.",
        })
    else:
        checks.append({
            "check": "min_credits",
            "passed": True,
            "detail": f"Credit requirement met ({student_info['total_credits']} ≥ {course_info['min_credits']}).",
        })

    # 5. Check prerequisites
    prereq_check = await check_prerequisites_met(session, student_id, course_code)
    if "error" not in prereq_check:
        if not prereq_check["all_met"]:
            eligible = False
            unmet = [p for p in prereq_check["prerequisites"] if not p["met"]]
            unmet_str = ", ".join([f"{p['prerequisite_code']} (need {p['min_grade_required']})" for p in unmet])
            checks.append({
                "check": "prerequisites",
                "passed": False,
                "detail": f"Unmet prerequisites: {unmet_str}",
            })
        else:
            checks.append({
                "check": "prerequisites",
                "passed": True,
                "detail": "All prerequisites met.",
            })

    # 6. Check if already completed or enrolled
    already_result = await session.execute(
        select(Enrollment)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_info["id"],
            Enrollment.status.in_(["completed", "enrolled", "in_progress"]),
        )
    )
    already = already_result.scalars().all()
    if already:
        statuses = [e.status for e in already]
        if "completed" in statuses:
            eligible = False
            checks.append({
                "check": "already_completed",
                "passed": False,
                "detail": "Student has already completed this course.",
            })
        elif "in_progress" in statuses or "enrolled" in statuses:
            eligible = False
            checks.append({
                "check": "already_enrolled",
                "passed": False,
                "detail": "Student is currently enrolled in this course.",
            })
    else:
        checks.append({"check": "not_duplicate", "passed": True, "detail": "Not previously completed or enrolled."})

    return {
        "eligible": eligible,
        "student": student_info,
        "course": course_info,
        "checks": checks,
    }
