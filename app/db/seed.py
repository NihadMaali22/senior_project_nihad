# ============================================================
# Database Seed Script
# ============================================================
"""
Populates the database with realistic university data including:
- 4 departments
- 8 instructors
- 25+ courses with prerequisites
- 12 students with varied academic profiles
- Enrollment records across multiple semesters
- Graduation requirements per department
- Academic warnings
- Default admin and student user accounts

Usage:
    python -m app.db.seed
"""

from __future__ import annotations

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_factory, engine, init_db
from app.db.models import (
    Base,
    Course,
    Department,
    Enrollment,
    GraduationRequirement,
    Instructor,
    Prerequisite,
    RequiredCourse,
    Student,
    User,
    Warning,
)

logger = logging.getLogger(__name__)


# ============================================================
# Grade point mapping
# ============================================================
GRADE_POINTS = {
    "A": Decimal("4.00"),
    "A-": Decimal("3.70"),
    "B+": Decimal("3.30"),
    "B": Decimal("3.00"),
    "B-": Decimal("2.70"),
    "C+": Decimal("2.30"),
    "C": Decimal("2.00"),
    "C-": Decimal("1.70"),
    "D+": Decimal("1.30"),
    "D": Decimal("1.00"),
    "F": Decimal("0.00"),
}


async def seed_departments(session: AsyncSession) -> dict[str, int]:
    """Seed 4 university departments."""
    departments = [
        Department(
            name="Computer Science", code="CS",
            description="Department of Computer Science covering software engineering, AI, and systems."
        ),
        Department(
            name="Information Technology", code="IT",
            description="Department of Information Technology covering networks, security, and web systems."
        ),
        Department(
            name="Electrical Engineering", code="EE",
            description="Department of Electrical Engineering covering circuits, signals, and power systems."
        ),
        Department(
            name="Business Administration", code="BA",
            description="Department of Business Administration covering management, marketing, and finance."
        ),
    ]
    session.add_all(departments)
    await session.flush()
    return {d.code: d.id for d in departments}


async def seed_instructors(session: AsyncSession, dept_ids: dict[str, int]) -> dict[str, int]:
    """Seed 8 instructors across departments."""
    instructors = [
        Instructor(name="Dr. Ahmad Al-Rashid", email="ahmad.rashid@university.edu",
                    department_id=dept_ids["CS"], title="Professor"),
        Instructor(name="Dr. Sarah Mitchell", email="sarah.mitchell@university.edu",
                    department_id=dept_ids["CS"], title="Associate Professor"),
        Instructor(name="Dr. Omar Hassan", email="omar.hassan@university.edu",
                    department_id=dept_ids["IT"], title="Assistant Professor"),
        Instructor(name="Dr. Layla Mahmoud", email="layla.mahmoud@university.edu",
                    department_id=dept_ids["IT"], title="Professor"),
        Instructor(name="Dr. James Wilson", email="james.wilson@university.edu",
                    department_id=dept_ids["EE"], title="Professor"),
        Instructor(name="Dr. Fatima Al-Zahra", email="fatima.zahra@university.edu",
                    department_id=dept_ids["EE"], title="Associate Professor"),
        Instructor(name="Dr. Michael Chen", email="michael.chen@university.edu",
                    department_id=dept_ids["BA"], title="Associate Professor"),
        Instructor(name="Dr. Nour Khalil", email="nour.khalil@university.edu",
                    department_id=dept_ids["BA"], title="Assistant Professor"),
    ]
    session.add_all(instructors)
    await session.flush()
    return {i.email.split("@")[0].replace(".", "_"): i.id for i in instructors}


async def seed_courses(session: AsyncSession, dept_ids: dict[str, int]) -> dict[str, int]:
    """Seed 28 courses across departments with realistic attributes."""
    courses = [
        # ---- Computer Science (CS) ----
        Course(code="CS101", name="Introduction to Programming", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Fundamentals of programming using Python."),
        Course(code="CS102", name="Object-Oriented Programming", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="OOP principles using Java."),
        Course(code="CS201", name="Data Structures", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Arrays, linked lists, trees, graphs, and hash tables."),
        Course(code="CS202", name="Algorithms", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Algorithm design, analysis, sorting, searching, and graph algorithms."),
        Course(code="CS301", name="Database Systems", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Relational databases, SQL, normalization, and transactions."),
        Course(code="CS302", name="Operating Systems", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Process management, memory, file systems, and concurrency."),
        Course(code="CS310", name="Software Engineering", credits=3,
               department_id=dept_ids["CS"], course_type="required",
               description="Software development life cycle, Agile, and project management."),
        Course(code="CS350", name="Artificial Intelligence", credits=3,
               department_id=dept_ids["CS"], course_type="elective",
               description="Search, knowledge representation, machine learning basics."),
        Course(code="CS490", name="Internship 1", credits=3,
               department_id=dept_ids["CS"], course_type="internship",
               description="Supervised field training at an approved organization.",
               min_credits=60, min_gpa=Decimal("2.00")),
        Course(code="CS491", name="Internship 2", credits=3,
               department_id=dept_ids["CS"], course_type="internship",
               description="Advanced field training building on Internship 1.",
               min_credits=90, min_gpa=Decimal("2.00")),
        Course(code="CS499", name="Capstone Project", credits=6,
               department_id=dept_ids["CS"], course_type="capstone",
               description="Senior design project demonstrating comprehensive skills.",
               min_credits=110, min_gpa=Decimal("2.00")),

        # ---- Information Technology (IT) ----
        Course(code="IT101", name="IT Fundamentals", credits=3,
               department_id=dept_ids["IT"], course_type="required",
               description="Overview of information technology concepts."),
        Course(code="IT201", name="Networking Fundamentals", credits=3,
               department_id=dept_ids["IT"], course_type="required",
               description="TCP/IP, routing, switching, and network design."),
        Course(code="IT301", name="Cybersecurity", credits=3,
               department_id=dept_ids["IT"], course_type="required",
               description="Security principles, cryptography, and threat analysis."),
        Course(code="IT302", name="Web Development", credits=3,
               department_id=dept_ids["IT"], course_type="required",
               description="Frontend and backend web technologies."),
        Course(code="IT490", name="IT Internship", credits=3,
               department_id=dept_ids["IT"], course_type="internship",
               min_credits=60, min_gpa=Decimal("2.00")),

        # ---- General / University Requirements ----
        Course(code="MATH101", name="Calculus I", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="Limits, derivatives, and integrals."),
        Course(code="MATH201", name="Linear Algebra", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="Vectors, matrices, determinants, and eigenvalues."),
        Course(code="MATH202", name="Probability & Statistics", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="Probability distributions, hypothesis testing, regression."),
        Course(code="PHYS101", name="Physics I", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="Mechanics, waves, and thermodynamics."),
        Course(code="ENG101", name="English Composition", credits=3,
               department_id=dept_ids["BA"], course_type="required",
               description="Academic writing and communication skills."),
        Course(code="ENG201", name="Technical Writing", credits=3,
               department_id=dept_ids["BA"], course_type="required",
               description="Writing for technical and professional audiences."),

        # ---- Electrical Engineering ----
        Course(code="EE201", name="Circuit Analysis", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="DC and AC circuit analysis techniques."),
        Course(code="EE301", name="Digital Logic Design", credits=3,
               department_id=dept_ids["EE"], course_type="required",
               description="Boolean algebra, combinational and sequential circuits."),

        # ---- Business ----
        Course(code="BA101", name="Principles of Management", credits=3,
               department_id=dept_ids["BA"], course_type="required",
               description="Planning, organizing, leading, and controlling."),
        Course(code="BA201", name="Marketing Fundamentals", credits=3,
               department_id=dept_ids["BA"], course_type="elective",
               description="Marketing mix, consumer behavior, and digital marketing."),
        Course(code="BA301", name="Financial Accounting", credits=3,
               department_id=dept_ids["BA"], course_type="required",
               description="Financial statements, bookkeeping, and GAAP."),
        Course(code="BA302", name="Business Ethics", credits=3,
               department_id=dept_ids["BA"], course_type="elective",
               description="Ethical frameworks and corporate social responsibility."),
    ]
    session.add_all(courses)
    await session.flush()
    return {c.code: c.id for c in courses}


async def seed_prerequisites(session: AsyncSession, course_ids: dict[str, int]) -> None:
    """Seed prerequisite chains for courses."""
    prereqs = [
        # CS chain
        Prerequisite(course_id=course_ids["CS102"], prerequisite_id=course_ids["CS101"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS201"], prerequisite_id=course_ids["CS102"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS202"], prerequisite_id=course_ids["CS201"], min_grade="C"),
        Prerequisite(course_id=course_ids["CS301"], prerequisite_id=course_ids["CS201"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS302"], prerequisite_id=course_ids["CS201"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS310"], prerequisite_id=course_ids["CS202"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS350"], prerequisite_id=course_ids["CS202"], min_grade="C"),
        Prerequisite(course_id=course_ids["CS350"], prerequisite_id=course_ids["MATH202"], min_grade="D"),
        # Internship prerequisites
        Prerequisite(course_id=course_ids["CS491"], prerequisite_id=course_ids["CS490"], min_grade="D"),
        # Capstone
        Prerequisite(course_id=course_ids["CS499"], prerequisite_id=course_ids["CS310"], min_grade="C"),
        Prerequisite(course_id=course_ids["CS499"], prerequisite_id=course_ids["CS301"], min_grade="C"),
        # IT chain
        Prerequisite(course_id=course_ids["IT201"], prerequisite_id=course_ids["IT101"], min_grade="D"),
        Prerequisite(course_id=course_ids["IT301"], prerequisite_id=course_ids["IT201"], min_grade="D"),
        Prerequisite(course_id=course_ids["IT302"], prerequisite_id=course_ids["CS101"], min_grade="D"),
        # Math chain
        Prerequisite(course_id=course_ids["MATH201"], prerequisite_id=course_ids["MATH101"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH202"], prerequisite_id=course_ids["MATH101"], min_grade="D"),
        # Engineering
        Prerequisite(course_id=course_ids["EE201"], prerequisite_id=course_ids["PHYS101"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE301"], prerequisite_id=course_ids["EE201"], min_grade="D"),
        # English
        Prerequisite(course_id=course_ids["ENG201"], prerequisite_id=course_ids["ENG101"], min_grade="C"),
    ]
    session.add_all(prereqs)
    await session.flush()


async def seed_students(
    session: AsyncSession,
    dept_ids: dict[str, int],
    instructor_ids: dict[str, int],
) -> dict[str, int]:
    """
    Seed 12 students with varied academic profiles.
    Some are high-performing, some are on probation, some near graduation.
    """
    students = [
        # --- High-performing senior, near graduation ---
        Student(
            student_number="2020-CS-001", first_name="Khalid", last_name="Al-Mansoor",
            email="khalid.mansoor@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2020, total_credits=118, gpa=Decimal("3.650"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("ahmad_rashid"),
        ),
        # --- Good student, mid-program ---
        Student(
            student_number="2021-CS-002", first_name="Noor", last_name="Abdullah",
            email="noor.abdullah@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2021, total_credits=85, gpa=Decimal("3.200"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("sarah_mitchell"),
        ),
        # --- Student on academic probation (low GPA) ---
        Student(
            student_number="2021-CS-003", first_name="Tariq", last_name="Hassan",
            email="tariq.hassan@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2021, total_credits=72, gpa=Decimal("1.850"),
            status="active", academic_standing="probation",
            advisor_id=instructor_ids.get("ahmad_rashid"),
        ),
        # --- Freshman, just started ---
        Student(
            student_number="2024-CS-004", first_name="Lina", last_name="Saeed",
            email="lina.saeed@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2024, total_credits=15, gpa=Decimal("3.800"),
            status="active", academic_standing="good",
        ),
        # --- IT student, steady progress ---
        Student(
            student_number="2022-IT-005", first_name="Mohammed", last_name="Farouk",
            email="mohammed.farouk@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2022, total_credits=65, gpa=Decimal("2.750"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("omar_hassan"),
        ),
        # --- IT student with warnings ---
        Student(
            student_number="2022-IT-006", first_name="Aya", last_name="Ibrahim",
            email="aya.ibrahim@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2022, total_credits=55, gpa=Decimal("2.100"),
            status="active", academic_standing="warning",
            advisor_id=instructor_ids.get("layla_mahmoud"),
        ),
        # --- EE student ---
        Student(
            student_number="2021-EE-007", first_name="Yousef", last_name="Nasser",
            email="yousef.nasser@students.edu", department_id=dept_ids["EE"],
            enrollment_year=2021, total_credits=92, gpa=Decimal("3.100"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("james_wilson"),
        ),
        # --- BA student ---
        Student(
            student_number="2023-BA-008", first_name="Rania", last_name="Othman",
            email="rania.othman@students.edu", department_id=dept_ids["BA"],
            enrollment_year=2023, total_credits=35, gpa=Decimal("3.400"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("michael_chen"),
        ),
        # --- Graduated student ---
        Student(
            student_number="2019-CS-009", first_name="Omar", last_name="Jaber",
            email="omar.jaber@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2019, total_credits=135, gpa=Decimal("3.500"),
            status="graduated", academic_standing="good",
        ),
        # --- Suspended student ---
        Student(
            student_number="2020-IT-010", first_name="Salma", last_name="Khoury",
            email="salma.khoury@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2020, total_credits=40, gpa=Decimal("1.200"),
            status="suspended", academic_standing="dismissal",
        ),
        # --- Student who can attempt internship 2 ---
        Student(
            student_number="2020-CS-011", first_name="Hassan", last_name="Darwish",
            email="hassan.darwish@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2020, total_credits=95, gpa=Decimal("2.900"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("sarah_mitchell"),
        ),
        # --- Student barely above probation threshold ---
        Student(
            student_number="2022-CS-012", first_name="Dana", last_name="Zaydan",
            email="dana.zaydan@students.edu", department_id=dept_ids["CS"],
            enrollment_year=2022, total_credits=60, gpa=Decimal("2.050"),
            status="active", academic_standing="good",
            advisor_id=instructor_ids.get("ahmad_rashid"),
        ),
    ]
    session.add_all(students)
    await session.flush()
    return {s.student_number: s.id for s in students}


async def seed_enrollments(
    session: AsyncSession,
    student_ids: dict[str, int],
    course_ids: dict[str, int],
) -> None:
    """Seed enrollment records across multiple semesters."""
    enrollments = [
        # ====== Khalid (2020-CS-001) — Senior, near graduation ======
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2020, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2020, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["ENG101"],
                   semester="Fall", academic_year=2020, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2020, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["MATH201"],
                   semester="Spring", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS201"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["MATH202"],
                   semester="Fall", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS202"],
                   semester="Spring", academic_year=2022, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS301"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["ENG201"],
                   semester="Spring", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS302"],
                   semester="Fall", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS310"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS350"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS490"],
                   semester="Summer", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS491"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["BA101"],
                   semester="Fall", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        # Currently doing capstone
        Enrollment(student_id=student_ids["2020-CS-001"], course_id=course_ids["CS499"],
                   semester="Spring", academic_year=2024, status="in_progress"),

        # ====== Noor (2021-CS-002) — Good student, mid-program ======
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["ENG101"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["MATH201"],
                   semester="Spring", academic_year=2022, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS201"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["MATH202"],
                   semester="Fall", academic_year=2022, status="completed", grade="B-", grade_points=Decimal("2.70")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS202"],
                   semester="Spring", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS301"],
                   semester="Spring", academic_year=2023, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2023, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS302"],
                   semester="Fall", academic_year=2023, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CS-002"], course_id=course_ids["CS490"],
                   semester="Spring", academic_year=2024, status="in_progress"),

        # ====== Tariq (2021-CS-003) — On probation ======
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2021, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2022, status="completed", grade="C-", grade_points=Decimal("1.70")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["ENG101"],
                   semester="Spring", academic_year=2022, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["CS201"],
                   semester="Fall", academic_year=2022, status="completed", grade="D+", grade_points=Decimal("1.30")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2022, status="failed", grade="F", grade_points=Decimal("0.00")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["CS202"],
                   semester="Spring", academic_year=2023, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["MATH201"],
                   semester="Spring", academic_year=2023, status="completed", grade="D+", grade_points=Decimal("1.30")),
        Enrollment(student_id=student_ids["2021-CS-003"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2023, status="completed", grade="D", grade_points=Decimal("1.00")),

        # ====== Hassan (2020-CS-011) — Can attempt internship 2 ======
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2020, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2020, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS201"],
                   semester="Fall", academic_year=2021, status="completed", grade="B-", grade_points=Decimal("2.70")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["MATH201"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS202"],
                   semester="Spring", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS301"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS302"],
                   semester="Fall", academic_year=2022, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS310"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["ENG101"],
                   semester="Spring", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["MATH202"],
                   semester="Spring", academic_year=2023, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["CS490"],
                   semester="Summer", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CS-011"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2023, status="completed", grade="C", grade_points=Decimal("2.00")),

        # ====== Lina (2024-CS-004) — Freshman ======
        Enrollment(student_id=student_ids["2024-CS-004"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CS-004"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2024-CS-004"], course_id=course_ids["ENG101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CS-004"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CS-004"], course_id=course_ids["PHYS101"],
                   semester="Spring", academic_year=2025, status="in_progress"),

        # ====== Dana (2022-CS-012) — Barely above probation ======
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["CS101"],
                   semester="Fall", academic_year=2022, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2022, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["CS102"],
                   semester="Spring", academic_year=2023, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["ENG101"],
                   semester="Spring", academic_year=2023, status="completed", grade="B-", grade_points=Decimal("2.70")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["CS201"],
                   semester="Fall", academic_year=2023, status="completed", grade="D+", grade_points=Decimal("1.30")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["MATH201"],
                   semester="Fall", academic_year=2023, status="failed", grade="F", grade_points=Decimal("0.00")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["MATH201"],
                   semester="Spring", academic_year=2024, status="completed", grade="C-", grade_points=Decimal("1.70")),
        Enrollment(student_id=student_ids["2022-CS-012"], course_id=course_ids["PHYS101"],
                   semester="Spring", academic_year=2024, status="completed", grade="C", grade_points=Decimal("2.00")),
    ]
    session.add_all(enrollments)
    await session.flush()


async def seed_graduation_requirements(
    session: AsyncSession,
    dept_ids: dict[str, int],
    course_ids: dict[str, int],
) -> None:
    """Seed graduation requirements for CS and IT departments."""
    # CS graduation requirements
    cs_req = GraduationRequirement(
        department_id=dept_ids["CS"],
        min_total_credits=132,
        min_gpa=Decimal("2.00"),
        min_major_credits=90,
        max_years=7,
        requires_internship=True,
        requires_capstone=True,
        description="Bachelor of Science in Computer Science graduation requirements.",
    )
    # IT graduation requirements
    it_req = GraduationRequirement(
        department_id=dept_ids["IT"],
        min_total_credits=130,
        min_gpa=Decimal("2.00"),
        min_major_credits=85,
        max_years=7,
        requires_internship=True,
        requires_capstone=False,
        description="Bachelor of Science in Information Technology graduation requirements.",
    )
    session.add_all([cs_req, it_req])
    await session.flush()

    # Required courses for CS graduation
    cs_required = [
        "CS101", "CS102", "CS201", "CS202", "CS301", "CS302",
        "CS310", "CS490", "CS491", "CS499",
        "MATH101", "MATH201", "MATH202", "PHYS101",
        "ENG101", "ENG201",
    ]
    for code in cs_required:
        if code in course_ids:
            session.add(RequiredCourse(
                graduation_req_id=cs_req.id,
                course_id=course_ids[code],
                is_core=code.startswith("CS"),
            ))
    await session.flush()


async def seed_warnings(session: AsyncSession, student_ids: dict[str, int]) -> None:
    """Seed academic warnings for relevant students."""
    warnings = [
        Warning(
            student_id=student_ids["2021-CS-003"],
            warning_type="gpa_probation",
            description="Cumulative GPA has fallen below 2.0 (current: 1.85). Student is placed on academic probation per Article 12.1 of the Academic Regulations.",
            semester="Fall", academic_year=2023, is_resolved=False,
        ),
        Warning(
            student_id=student_ids["2021-CS-003"],
            warning_type="gpa_warning",
            description="GPA dropped below 2.0 for the second consecutive semester. If GPA is not raised above 2.0 by end of next semester, student may face dismissal.",
            semester="Spring", academic_year=2023, is_resolved=False,
        ),
        Warning(
            student_id=student_ids["2022-IT-006"],
            warning_type="gpa_warning",
            description="Cumulative GPA is 2.10, approaching probation threshold of 2.0.",
            semester="Fall", academic_year=2023, is_resolved=False,
        ),
        Warning(
            student_id=student_ids["2020-IT-010"],
            warning_type="gpa_probation",
            description="Cumulative GPA 1.2. Student suspended due to failure to raise GPA above 2.0 after two consecutive probation semesters.",
            semester="Spring", academic_year=2022, is_resolved=True,
        ),
        Warning(
            student_id=student_ids["2022-CS-012"],
            warning_type="gpa_warning",
            description="Cumulative GPA 2.05, very close to probation threshold.",
            semester="Spring", academic_year=2024, is_resolved=False,
        ),
    ]
    session.add_all(warnings)
    await session.flush()


async def seed_users(session: AsyncSession, student_ids: dict[str, int]) -> None:
    """Create default user accounts for authentication."""
    from app.auth.service import hash_password

    users = [
        User(
            username="admin",
            hashed_password=hash_password("admin123"),
            email="admin@university.edu",
            full_name="System Administrator",
            role="admin",
            is_active=True,
        ),
        User(
            username="khalid",
            hashed_password=hash_password("student123"),
            email="khalid.mansoor@students.edu",
            full_name="Khalid Al-Mansoor",
            role="student",
            student_id=student_ids["2020-CS-001"],
            is_active=True,
        ),
        User(
            username="noor",
            hashed_password=hash_password("student123"),
            email="noor.abdullah@students.edu",
            full_name="Noor Abdullah",
            role="student",
            student_id=student_ids["2021-CS-002"],
            is_active=True,
        ),
        User(
            username="tariq",
            hashed_password=hash_password("student123"),
            email="tariq.hassan@students.edu",
            full_name="Tariq Hassan",
            role="student",
            student_id=student_ids["2021-CS-003"],
            is_active=True,
        ),
        User(
            username="hassan",
            hashed_password=hash_password("student123"),
            email="hassan.darwish@students.edu",
            full_name="Hassan Darwish",
            role="student",
            student_id=student_ids["2020-CS-011"],
            is_active=True,
        ),
        User(
            username="lina",
            hashed_password=hash_password("student123"),
            email="lina.saeed@students.edu",
            full_name="Lina Saeed",
            role="student",
            student_id=student_ids["2024-CS-004"],
            is_active=True,
        ),
        User(
            username="advisor",
            hashed_password=hash_password("advisor123"),
            email="ahmad.rashid@university.edu",
            full_name="Dr. Ahmad Al-Rashid",
            role="advisor",
            is_active=True,
        ),
    ]
    session.add_all(users)
    await session.flush()


async def run_seed() -> None:
    """Execute all seed functions in order."""
    logger.info("Starting database seeding...")

    # Initialize tables first
    await init_db()

    async with async_session_factory() as session:
        async with session.begin():
            # Check if data already exists
            result = await session.execute(select(Department).limit(1))
            if result.scalar_one_or_none() is not None:
                logger.info("Database already seeded. Skipping.")
                return

            # Seed in dependency order
            dept_ids = await seed_departments(session)
            logger.info(f"Seeded {len(dept_ids)} departments")

            instructor_ids = await seed_instructors(session, dept_ids)
            logger.info(f"Seeded {len(instructor_ids)} instructors")

            course_ids = await seed_courses(session, dept_ids)
            logger.info(f"Seeded {len(course_ids)} courses")

            await seed_prerequisites(session, course_ids)
            logger.info("Seeded prerequisites")

            student_ids = await seed_students(session, dept_ids, instructor_ids)
            logger.info(f"Seeded {len(student_ids)} students")

            await seed_enrollments(session, student_ids, course_ids)
            logger.info("Seeded enrollments")

            await seed_graduation_requirements(session, dept_ids, course_ids)
            logger.info("Seeded graduation requirements")

            await seed_warnings(session, student_ids)
            logger.info("Seeded warnings")

            await seed_users(session, student_ids)
            logger.info("Seeded users")

    logger.info("Database seeding completed successfully!")


# Allow running directly: python -m app.db.seed
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())
