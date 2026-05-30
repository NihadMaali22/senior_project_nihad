# ============================================================
# Authentication API Routes
# ============================================================
"""
Endpoints for user login, registration, and profile retrieval.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user, require_role
from app.auth.schemas import (
    LoginRequest,
    RegisterRequest,
    TokenPayload,
    TokenResponse,
    UserResponse,
    StudentProfileResponse,
)
from app.auth.service import authenticate_user, create_access_token, hash_password
from app.db.models import User
from app.dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="User Login")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Authenticate with username and password to receive a JWT access token.

    Default accounts after seeding:
    - **admin** / admin123 (role: admin)
    - **khalid** / student123 (role: student, student_id: 1)
    - **noor** / student123 (role: student, student_id: 2)
    - **tariq** / student123 (role: student, student_id: 3)
    - **hassan** / student123 (role: student, student_id: 5)
    """
    user = await authenticate_user(session, request.username, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token, expires_in = create_access_token(
        username=user.username,
        user_id=user.id,
        role=user.role,
        student_id=user.student_id,
    )

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User (Admin Only)",
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    _: TokenPayload = Depends(require_role("admin")),
):
    """
    Create a new user account. Requires admin role.
    """
    # Check if username already exists
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.username == request.username)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' already exists",
        )

    new_user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        email=request.email,
        full_name=request.full_name,
        role=request.role,
        student_id=request.student_id,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()

    logger.info(f"New user registered: {request.username} (role: {request.role})")
    return new_user


@router.get("/me", response_model=UserResponse, summary="Get Current User Profile")
async def get_me(
    current_user: TokenPayload = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Returns the profile of the currently authenticated user.
    """
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.id == current_user.user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.get(
    "/student-profile",
    response_model=StudentProfileResponse,
    summary="Get Current Student Profile",
)
async def get_student_profile(
    current_user: TokenPayload = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve the student profile details for the currently logged in student.
    """
    if current_user.student_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current user is not associated with a student record",
        )

    from sqlalchemy import select, func
    from app.db.models import Student, Department, GraduationRequirement, Enrollment, Course

    # 1. Fetch Student, Department details
    query = (
        select(Student, Department)
        .outerjoin(Department, Student.department_id == Department.id)
        .where(Student.id == current_user.student_id)
    )
    result = await session.execute(query)
    row = result.first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student record not found for ID {current_user.student_id}",
        )
    student, department = row

    # 2. Fetch Graduation Requirements to calculate remaining credits
    min_credits = 132  # Default fallback
    if student.department_id is not None:
        grad_req_query = select(GraduationRequirement).where(
            GraduationRequirement.department_id == student.department_id
        )
        grad_req_res = await session.execute(grad_req_query)
        grad_req = grad_req_res.scalar_one_or_none()
        if grad_req:
            min_credits = grad_req.min_total_credits

    remaining_credits = max(0, min_credits - student.total_credits)

    # 3. Fetch current registered hours (sum of credits for courses enrolled in the latest semester)
    # Let's find the latest semester from the enrollments
    sem_query = (
        select(Enrollment.semester)
        .where(Enrollment.student_id == student.id)
        .order_by(Enrollment.academic_year.desc(), Enrollment.created_at.desc())
        .limit(1)
    )
    sem_res = await session.execute(sem_query)
    latest_semester = sem_res.scalar_one_or_none() or "Spring"

    # Sum credits of courses enrolled in this latest semester
    reg_credits_query = (
        select(func.sum(Course.credits))
        .select_from(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .where(
            Enrollment.student_id == student.id,
            Enrollment.semester == latest_semester,
            Enrollment.status.in_(["enrolled", "in_progress"])
        )
    )
    reg_credits_res = await session.execute(reg_credits_query)
    registered_credits = reg_credits_res.scalar() or 0

    return StudentProfileResponse(
        student_id=student.id,
        student_number=student.student_number,
        first_name=student.first_name,
        last_name=student.last_name,
        full_name=student.full_name,
        email=student.email,
        gpa=float(student.gpa),
        total_credits=student.total_credits,
        registered_credits=int(registered_credits),
        remaining_credits=int(remaining_credits),
        status=student.status,
        academic_standing=student.academic_standing,
        department_name=department.name if department else None,
        department_code=department.code if department else None,
        semester=latest_semester,
    )

