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


# ============================================================
# GPA Computation Helper
# ============================================================
_GRADE_POINTS: dict[str, float] = {
    "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0,
    "F": 0.0,
}


def _derive_academic_standing(gpa: float) -> str:
    """Derive academic standing label from GPA."""
    if gpa < 1.0:
        return "dismissal"
    elif gpa < 1.5:
        return "probation"       # severe
    elif gpa < 2.0:
        return "probation"
    else:
        return "good"


async def _compute_gpa_from_enrollments(
    session: AsyncSession,
    student_id: int,
) -> tuple[float, int]:
    """
    Compute GPA and total earned credits directly from the enrollments table.

    Uses the weighted formula:
        GPA = Σ(grade_points × course_credits) / Σ(course_credits)

    Only completed enrollments with a numeric grade_points value are included.
    Returns (gpa, total_credits_earned).
    """
    result = await session.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.status == "completed",
            Enrollment.grade_points.is_not(None),
        )
    )
    rows = result.all()

    if not rows:
        return 0.0, 0

    total_quality_points = 0.0
    total_credits = 0

    for enrollment, course in rows:
        gp = float(enrollment.grade_points)
        cr = int(course.credits)
        total_quality_points += gp * cr
        total_credits += cr

    gpa = round(total_quality_points / total_credits, 3) if total_credits > 0 else 0.0
    return gpa, total_credits


async def get_full_student_profile(session: AsyncSession, student_id: int) -> Optional[dict[str, Any]]:
    """
    Fetch student base info, compute GPA, and bucket enrollments
    into completed and current in a single database query over enrollments.
    """
    result = await session.execute(
        select(Student)
        .options(selectinload(Student.department), selectinload(Student.advisor))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        return None

    enroll_result = await session.execute(
        select(Enrollment, Course)
        .join(Course, Enrollment.course_id == Course.id)
        .where(Enrollment.student_id == student_id)
        .order_by(Enrollment.academic_year, Enrollment.semester)
    )
    rows = enroll_result.all()

    completed_courses = []
    current_enrollments = []
    failed_courses = []
    
    total_quality_points = 0.0
    total_credits = 0

    for enrollment, course in rows:
        if enrollment.status == "completed":
            completed_courses.append({
                "course_code": course.code,
                "course_name": course.name,
                "credits": course.credits,
                "grade": enrollment.grade,
                "grade_points": float(enrollment.grade_points) if enrollment.grade_points else None,
                "semester": enrollment.semester,
                "academic_year": enrollment.academic_year,
            })
            if enrollment.grade_points is not None:
                gp = float(enrollment.grade_points)
                cr = int(course.credits)
                total_quality_points += gp * cr
                total_credits += cr
        elif enrollment.status in ["enrolled", "in_progress"]:
            current_enrollments.append({
                "course_code": course.code,
                "course_name": course.name,
                "credits": course.credits,
                "semester": enrollment.semester,
                "academic_year": enrollment.academic_year,
                "status": enrollment.status,
            })
        elif enrollment.status == "failed":
            failed_courses.append({
                "course_code": course.code,
                "course_name": course.name,
                "grade": enrollment.grade,
                "semester": enrollment.semester,
                "academic_year": enrollment.academic_year,
            })

    gpa = round(total_quality_points / total_credits, 3) if total_credits > 0 else 0.0
    academic_standing = _derive_academic_standing(gpa)

    return {
        "id": student.id,
        "student_number": student.student_number,
        "full_name": student.full_name,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "department": student.department.name if student.department else None,
        "department_code": student.department.code if student.department else None,
        "advisor_name": student.advisor.name if student.advisor else None,
        "enrollment_year": student.enrollment_year,
        "total_credits": total_credits,
        "gpa": gpa,
        "status": student.status,
        "academic_standing": academic_standing,
        "completed_courses": completed_courses,
        "current_enrollments": current_enrollments,
        "failed_courses": failed_courses,
    }


async def get_student_info(session: AsyncSession, student_id: int) -> Optional[dict[str, Any]]:
    """
    Retrieve complete student profile including department info.
    GPA and total_credits are computed dynamically from enrollments
    to guarantee accuracy regardless of the cached stored field.

    Returns:
        Dict with student details or None if not found.
    """
    result = await session.execute(
        select(Student)
        .options(selectinload(Student.department), selectinload(Student.advisor))
        .where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        return None

    # ── Compute GPA dynamically (never trust the cached stored field) ──
    computed_gpa, computed_credits = await _compute_gpa_from_enrollments(session, student_id)
    # Fall back to 0.0 only if no completed enrollments exist yet
    gpa = computed_gpa if computed_credits > 0 else 0.0
    total_credits = computed_credits if computed_credits > 0 else int(student.total_credits)
    academic_standing = _derive_academic_standing(gpa)

    return {
        "id": student.id,
        "student_number": student.student_number,
        "full_name": student.full_name,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "department": student.department.name if student.department else None,
        "department_code": student.department.code if student.department else None,
        "advisor_name": student.advisor.name if student.advisor else None,
        "enrollment_year": student.enrollment_year,
        "total_credits": total_credits,
        "gpa": gpa,
        "status": student.status,
        "academic_standing": academic_standing,
    }


async def get_student_gpa(session: AsyncSession, student_id: int) -> Optional[dict[str, Any]]:
    """Get GPA and credit info for a student — always computed from enrollments."""
    result = await session.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        return None

    computed_gpa, computed_credits = await _compute_gpa_from_enrollments(session, student_id)
    gpa = computed_gpa if computed_credits > 0 else 0.0
    total_credits = computed_credits if computed_credits > 0 else int(student.total_credits)
    academic_standing = _derive_academic_standing(gpa)

    return {
        "student_number": student.student_number,
        "full_name": f"{student.first_name} {student.last_name}",
        "gpa": gpa,
        "total_credits": total_credits,
        "academic_standing": academic_standing,
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

    # Fetch all completed enrollments for these prerequisites in one query
    prereq_ids = [prereq.prerequisite_id for prereq, _ in prerequisites]
    enrollment_result = await session.execute(
        select(Enrollment)
        .where(
            Enrollment.student_id == student_id,
            Enrollment.course_id.in_(prereq_ids),
            Enrollment.status == "completed",
        )
    )
    
    # Map each prerequisite to its highest grade enrollment
    completed_map = {}
    for e in enrollment_result.scalars().all():
        if e.course_id not in completed_map or (e.grade_points or 0) > (completed_map[e.course_id].grade_points or 0):
            completed_map[e.course_id] = e

    for prereq, prereq_course in prerequisites:
        enrollment = completed_map.get(prereq.prerequisite_id)

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

    computed_gpa, computed_credits = await _compute_gpa_from_enrollments(session, student_id)
    gpa = computed_gpa if computed_credits > 0 else 0.0

    return {
        "department": student.department_id,
        "min_total_credits": req.min_total_credits,
        "min_gpa": float(req.min_gpa),
        "min_major_credits": req.min_major_credits,
        "max_years": req.max_years,
        "requires_internship": req.requires_internship,
        "requires_capstone": req.requires_capstone,
        "student_credits": student.total_credits,
        "student_gpa": gpa,
        "credits_remaining": max(0, req.min_total_credits - student.total_credits),
        "gpa_met": gpa >= float(req.min_gpa),
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


# ============================================================
# GPA Recalculation — Sync cached fields to DB
# ============================================================
async def recalculate_student_stats(
    session: AsyncSession,
    student_id: int,
    commit: bool = True,
) -> dict[str, Any]:
    """
    Recompute GPA, total_credits, and academic_standing from enrollments
    and persist the result back to the students table.

    This keeps the stored fields (used as a cache / denormalized copy) in sync
    after any grade change, import, or administrative update.

    Args:
        session: Async DB session.
        student_id: The student to update.
        commit: If True, flush and commit the session. Set False when calling
                inside a larger transaction that will commit later.

    Returns:
        Dict with the updated values.
    """
    # Fetch student
    result = await session.execute(
        select(Student).where(Student.id == student_id)
    )
    student = result.scalar_one_or_none()
    if student is None:
        return {"error": f"Student {student_id} not found"}

    # Compute from enrollments
    computed_gpa, computed_credits = await _compute_gpa_from_enrollments(session, student_id)

    # Use stored values as baseline if no completed enrollments yet
    new_credits = computed_credits if computed_credits > 0 else int(student.total_credits)
    new_standing = _derive_academic_standing(computed_gpa if computed_credits > 0 else 0.0)

    old_credits = int(student.total_credits)
    old_standing = student.academic_standing

    # Only write if something changed
    changed = (
        new_credits != old_credits
        or new_standing != old_standing
    )

    if changed:
        student.total_credits = new_credits  # type: ignore[assignment]
        student.academic_standing = new_standing

        if commit:
            await session.flush()
            await session.commit()

        logger.info(
            f"[GPA SYNC] student_id={student_id} "
            f"credits: {old_credits} → {new_credits} | "
            f"standing: {old_standing} → {new_standing}"
        )
    else:
        logger.debug(f"[GPA SYNC] student_id={student_id} — no change needed")

    return {
        "student_id": student_id,
        "student_number": student.student_number,
        "full_name": student.full_name,
        "gpa": new_gpa,
        "total_credits": new_credits,
        "academic_standing": new_standing,
        "changed": changed,
    }


async def recalculate_all_students_stats(
    session: AsyncSession,
) -> dict[str, Any]:
    """
    Recalculate and persist GPA/credits/standing for ALL students.
    Useful after a bulk grade import or seed.

    Returns a summary dict with counts and list of updated students.
    """
    students_result = await session.execute(select(Student.id))
    student_ids = [row[0] for row in students_result.all()]

    updated = []
    skipped = []
    errors = []

    for sid in student_ids:
        try:
            result = await recalculate_student_stats(session, sid, commit=False)
            if result.get("changed"):
                updated.append(result)
            else:
                skipped.append(sid)
        except Exception as e:
            logger.error(f"[GPA SYNC] Failed for student_id={sid}: {e}")
            errors.append({"student_id": sid, "error": str(e)})

    if updated:
        await session.flush()
        await session.commit()

    logger.info(
        f"[GPA SYNC] Batch complete — "
        f"updated={len(updated)}, skipped={len(skipped)}, errors={len(errors)}"
    )

    return {
        "total_students": len(student_ids),
        "updated": len(updated),
        "skipped": len(skipped),
        "errors": len(errors),
        "updated_details": updated,
        "error_details": errors,
    }
