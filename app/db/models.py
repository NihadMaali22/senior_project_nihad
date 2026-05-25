# ============================================================
# SQLAlchemy ORM Models
# ============================================================
"""
All database ORM models using SQLAlchemy 2.0 Declarative style.
These models map directly to the PostgreSQL schema tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ============================================================
# DEPARTMENT
# ============================================================
class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    instructors: Mapped[List["Instructor"]] = relationship(back_populates="department")
    courses: Mapped[List["Course"]] = relationship(back_populates="department")
    students: Mapped[List["Student"]] = relationship(back_populates="department")
    graduation_requirements: Mapped[List["GraduationRequirement"]] = relationship(
        back_populates="department"
    )

    def __repr__(self) -> str:
        return f"<Department(id={self.id}, code='{self.code}', name='{self.name}')>"


# ============================================================
# INSTRUCTOR
# ============================================================
class Instructor(Base):
    __tablename__ = "instructors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="instructors")
    students_advised: Mapped[List["Student"]] = relationship(back_populates="advisor")

    def __repr__(self) -> str:
        return f"<Instructor(id={self.id}, name='{self.name}')>"


# ============================================================
# COURSE
# ============================================================
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    course_type: Mapped[str] = mapped_column(String(50), default="required")
    min_gpa: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0)
    min_credits: Mapped[int] = mapped_column(Integer, default=0)
    max_capacity: Mapped[int] = mapped_column(Integer, default=40)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("credits > 0", name="ck_courses_credits_positive"),
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="courses")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="course")
    prerequisites: Mapped[List["Prerequisite"]] = relationship(
        back_populates="course",
        foreign_keys="Prerequisite.course_id",
    )
    is_prerequisite_for: Mapped[List["Prerequisite"]] = relationship(
        back_populates="prerequisite_course",
        foreign_keys="Prerequisite.prerequisite_id",
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, code='{self.code}', name='{self.name}')>"


# ============================================================
# PREREQUISITE
# ============================================================
class Prerequisite(Base):
    __tablename__ = "prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    prerequisite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    min_grade: Mapped[str] = mapped_column(String(5), default="D")
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("course_id", "prerequisite_id", name="uq_prerequisite"),
        CheckConstraint("course_id != prerequisite_id", name="ck_no_self_prerequisite"),
    )

    # Relationships
    course: Mapped["Course"] = relationship(
        back_populates="prerequisites", foreign_keys=[course_id]
    )
    prerequisite_course: Mapped["Course"] = relationship(
        back_populates="is_prerequisite_for", foreign_keys=[prerequisite_id]
    )

    def __repr__(self) -> str:
        return f"<Prerequisite(course_id={self.course_id}, prereq_id={self.prerequisite_id})>"


# ============================================================
# STUDENT
# ============================================================
class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    enrollment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_credits: Mapped[int] = mapped_column(Integer, default=0)
    gpa: Mapped[float] = mapped_column(Numeric(4, 3), default=0.000)
    status: Mapped[str] = mapped_column(String(30), default="active")
    academic_standing: Mapped[str] = mapped_column(String(30), default="good")
    advisor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(back_populates="students")
    advisor: Mapped[Optional["Instructor"]] = relationship(back_populates="students_advised")
    enrollments: Mapped[List["Enrollment"]] = relationship(back_populates="student")
    warnings: Mapped[List["Warning"]] = relationship(back_populates="student")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Student(id={self.id}, number='{self.student_number}', name='{self.full_name}')>"


# ============================================================
# ENROLLMENT
# ============================================================
class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    instructor_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True
    )
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="enrolled")
    grade: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    grade_points: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id", "course_id", "semester", "academic_year",
            name="uq_enrollment"
        ),
        Index("idx_enrollments_student", "student_id"),
        Index("idx_enrollments_course", "course_id"),
        Index("idx_enrollments_status", "status"),
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")

    def __repr__(self) -> str:
        return (
            f"<Enrollment(student_id={self.student_id}, "
            f"course_id={self.course_id}, grade='{self.grade}')>"
        )


# ============================================================
# GRADUATION REQUIREMENT
# ============================================================
class GraduationRequirement(Base):
    __tablename__ = "graduation_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    min_total_credits: Mapped[int] = mapped_column(Integer, default=132)
    min_gpa: Mapped[float] = mapped_column(Numeric(3, 2), default=2.00)
    min_major_credits: Mapped[int] = mapped_column(Integer, default=90)
    max_years: Mapped[int] = mapped_column(Integer, default=7)
    requires_internship: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_capstone: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    department: Mapped["Department"] = relationship(back_populates="graduation_requirements")
    required_courses: Mapped[List["RequiredCourse"]] = relationship(
        back_populates="graduation_requirement"
    )

    def __repr__(self) -> str:
        return f"<GraduationRequirement(dept_id={self.department_id}, min_credits={self.min_total_credits})>"


# ============================================================
# REQUIRED COURSE (for graduation)
# ============================================================
class RequiredCourse(Base):
    __tablename__ = "required_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graduation_req_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("graduation_requirements.id", ondelete="CASCADE"), nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    is_core: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("graduation_req_id", "course_id", name="uq_required_course"),
    )

    # Relationships
    graduation_requirement: Mapped["GraduationRequirement"] = relationship(
        back_populates="required_courses"
    )

    def __repr__(self) -> str:
        return f"<RequiredCourse(grad_req={self.graduation_req_id}, course={self.course_id})>"


# ============================================================
# WARNING
# ============================================================
class Warning(Base):
    __tablename__ = "warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    warning_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="warnings")

    def __repr__(self) -> str:
        return f"<Warning(student_id={self.student_id}, type='{self.warning_type}')>"


# ============================================================
# CONVERSATION HISTORY
# ============================================================
class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<ConversationHistory(session='{self.session_id}', role='{self.role}')>"


# ============================================================
# USER (authentication)
# ============================================================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(300), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="student")
    student_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ============================================================
# ROBOT SESSION (Temporary QR Token)
# ============================================================
class RobotSession(Base):
    """
    Temporary session token generated by the robot and embedded in a QR Code.
    The student scans the QR → frontend sends the token to /robot/verify-session
    → a full JWT is issued without requiring a password.
    """
    __tablename__ = "robot_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # UUID token embedded in the QR code
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    # The student this session is pre-assigned to (Option A: robot passes student_id)
    student_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )

    # The user account resolved at verify time (filled in after verification)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Token state
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_robot_sessions_token", "token"),
        Index("idx_robot_sessions_expires", "expires_at"),
    )

    # Relationships
    student: Mapped[Optional["Student"]] = relationship()
    user: Mapped[Optional["User"]] = relationship()

    def __repr__(self) -> str:
        return f"<RobotSession(token='{self.token[:8]}...', used={self.is_used})>"
