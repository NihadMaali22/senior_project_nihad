# ============================================================
# Database Seed Script
# ============================================================
"""
Populates the database with realistic university data including:
- 5 departments (featuring CSE)
- 8 instructors
- 65 Computer Systems Engineering courses with prerequisites
- 12 students with realistic CSE academic profiles
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
    """Seed 5 university departments."""
    departments = [
        Department(
            name="Computer Systems Engineering", code="CSE",
            description="Department of Computer Systems Engineering covering software, hardware, networks, and embedded systems."
        ),
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
                    department_id=dept_ids["CSE"], title="Professor"),
        Instructor(name="Dr. Sarah Mitchell", email="sarah.mitchell@university.edu",
                    department_id=dept_ids["CSE"], title="Associate Professor"),
        Instructor(name="Dr. Omar Hassan", email="omar.hassan@university.edu",
                    department_id=dept_ids["CS"], title="Assistant Professor"),
        Instructor(name="Dr. Layla Mahmoud", email="layla.mahmoud@university.edu",
                    department_id=dept_ids["IT"], title="Professor"),
        Instructor(name="Dr. James Wilson", email="james.wilson@university.edu",
                    department_id=dept_ids["CSE"], title="Professor"),
        Instructor(name="Dr. Fatima Al-Zahra", email="fatima.zahra@university.edu",
                    department_id=dept_ids["CSE"], title="Associate Professor"),
        Instructor(name="Dr. Michael Chen", email="michael.chen@university.edu",
                    department_id=dept_ids["BA"], title="Associate Professor"),
        Instructor(name="Dr. Nour Khalil", email="nour.khalil@university.edu",
                    department_id=dept_ids["BA"], title="Assistant Professor"),
    ]
    session.add_all(instructors)
    await session.flush()
    return {i.email.split("@")[0].replace(".", "_"): i.id for i in instructors}


async def seed_courses(session: AsyncSession, dept_ids: dict[str, int]) -> dict[str, int]:
    """Seed 65 courses from the CSE Program Tree."""
    courses = [
        # YEAR 1 — FIRST SEMESTER
        Course(code="CS111", name="Programming Fundamentals I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Fundamentals of programming, control structures, loops, and functional programming."),
        Course(code="CS111L", name="Programming Fundamentals Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Practical programming assignments in Python/C++ to accompany CS111."),
        Course(code="PHYS101", name="General Physics I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Mechanics, vectors, kinematics, Newton's laws, energy, and momentum."),
        Course(code="PHYS101L", name="General Physics Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Laboratory experiments demonstrating classical mechanics concepts."),
        Course(code="MATH101", name="Calculus I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Limits, derivatives, applications of differentiation, and basic integration."),
        Course(code="CS100", name="Computer Skills", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Introduction to computer components, operating systems, and basic software skills."),
        Course(code="EL101", name="Intermediate English", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Developing English language listening, speaking, reading, and writing skills."),

        # YEAR 1 — SECOND SEMESTER
        Course(code="EE101", name="Engineering Drawing", credits=2,
               department_id=dept_ids["CSE"], course_type="required",
               description="Introduction to technical drawing, projections, and computer-aided design (CAD)."),
        Course(code="EE211", name="Digital Logic Design", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Number systems, Boolean algebra, combinational circuits, decoders, multiplexers, sequential logic, and flip-flops."),
        Course(code="CS112", name="Programming Fundamentals II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Object-oriented programming concepts, classes, inheritance, polymorphism, and basic data structures."),
        Course(code="PHYS102", name="General Physics II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Electricity, electric fields, Gauss's law, magnetism, electromagnetic induction, and basic circuits."),
        Course(code="MATH102", name="Calculus II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Techniques of integration, applications of integrals, sequences, and infinite series."),
        Course(code="EL102", name="Advanced English", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Advanced reading comprehension, essay writing, and academic presentation skills."),

        # YEAR 2 — FIRST SEMESTER
        Course(code="EE201", name="Engineering Workshop I", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Practical training on workshop safety, manual tooling, sheet metal work, and basic carpentry."),
        Course(code="EE211L", name="Digital Logic Design Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Hands-on experiments with logic gates, multiplexers, registers, counters, and digital circuit boards."),
        Course(code="CS211", name="Principles of Object Oriented Programming", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Advanced OOP principles using Java or C#, exceptions, files, generics, and introductory GUI design."),
        Course(code="MATH211", name="Discrete Math", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Mathematical induction, set theory, relations, logic, graphs, trees, and combinatorics."),
        Course(code="MATH201", name="Engineering Math I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="First and second-order ordinary differential equations, systems of linear ODEs, and Laplace transforms."),
        Course(code="EE212", name="Electrical Circuit I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Circuit elements, KCL, KVL, nodal and mesh analysis, network theorems, transient analysis of RL, RC, and RLC circuits."),
        Course(code="UNIV_ELEC1", name="University Elective (1)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="First university elective course from the approved elective list."),

        # YEAR 2 — SECOND SEMESTER
        Course(code="EE202", name="Engineering Workshop II", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="PCB design and manufacturing, soldering, basic electronic circuit assembly, and electronic safety."),
        Course(code="EE221", name="Computer Organization", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="CPU architecture, ALU, control unit, microprogramming, instruction cycles, addressing modes, and memory hierarchy."),
        Course(code="CS212", name="Data Structure", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Implementation of stacks, queues, linked lists, binary search trees, heap structures, sorting, and hashing."),
        Course(code="MATH202", name="Engineering Math II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Fourier series, Fourier transforms, partial differential equations, and complex variables."),
        Course(code="EE222", name="Signals and Systems", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Continuous-time and discrete-time signals, LTI systems, convolution, Fourier transform, and Laplace transform."),
        Course(code="EE213", name="Electrical Circuit II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="AC steady-state analysis, power calculations, three-phase systems, magnetically coupled circuits, and frequency response."),

        # YEAR 3 — FIRST SEMESTER
        Course(code="EE311", name="Advanced Digital Systems Design", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Digital design with VHDL or Verilog, synthesis, simulation, finite state machines, and implementation on FPGA boards."),
        Course(code="CS311", name="Introduction to Database Systems", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Relational database concepts, SQL language, normalization, Entity-Relationship modeling, and database transactions."),
        Course(code="CS311L", name="Database Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Practical lab using PostgreSQL/MySQL to implement queries, schema design, and stored procedures."),
        Course(code="CS312", name="Algorithms Analysis and Design", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Time/space complexity analysis, divide-and-conquer, greedy, dynamic programming, and search algorithms."),
        Course(code="EE312", name="Electronics I", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Semiconductor diodes, BJT and MOSFET physical characteristics, DC biasing, and small-signal AC models."),
        Course(code="EE212L", name="Electrical Circuit Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Laboratory experiments covering Ohm's law, superposition, Thevenin/Norton, and transient circuits."),
        Course(code="UNIV101", name="Palestinian Studies", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Overview of Palestine's history, geographical features, culture, and political developments."),

        # YEAR 3 — SECOND SEMESTER
        Course(code="EE321", name="Data & Computer Networks", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="OSI model layers, TCP/IP, IP addressing, subnetting, routing, switching, and transport layer protocols."),
        Course(code="EE322", name="Microprocessor Systems & Applications", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Microprocessor architecture, instruction set, assembly language programming, interrupts, and I/O interfacing."),
        Course(code="CS321", name="Operating Systems", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Process management, threads, scheduling, CPU allocation, memory management, virtual memory, and file systems."),
        Course(code="MATH301", name="Numerical Methods", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Numerical solutions of non-linear equations, interpolation, numerical integration, and numerical methods for ODEs."),
        Course(code="EE313", name="Electronics II", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Multistage amplifiers, frequency response of BJTs/FETs, feedback amplifiers, oscillators, and operational amplifiers."),
        Course(code="UNIV102", name="Arabic Language", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Syntactical structures of Arabic, grammar, spelling, and literary textual analysis."),

        # YEAR 4 — FIRST SEMESTER
        Course(code="EE322L", name="Assembly Programming Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Practical laboratory writing assembly code for x86/ARM and executing programs on simulator boards."),
        Course(code="CS322", name="Web Programming", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Frontend technologies (HTML5, CSS3, JS) and backend APIs, RESTful architectures, and database integration."),
        Course(code="CS323", name="Software Engineering", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Software development lifecycle, requirements engineering, software architecture, UML modeling, and agile processes."),
        Course(code="DEPT_ELEC1", name="Department Elective (1)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="First CSE department elective course."),
        Course(code="MATH302", name="Probability and Random Variables", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Probability theory, random variables, cumulative distribution functions, expectations, joint distribution, and random processes."),
        Course(code="EE312L", name="Electronics Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Laboratory experiments on diodes, rectifiers, transistors (BJT/FET), and basic operational amplifier applications."),
        Course(code="EL201", name="Technical Writing", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Report structures, drafting technical manuals, research proposals, summaries, and professional emails."),

        # YEAR 4 — SECOND SEMESTER
        Course(code="EE321L", name="Computer Network Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Router configurations, Cisco iOS, routing protocols (RIP, OSPF), VLANs, and network diagnostics using Wireshark."),
        Course(code="EE322L2", name="Microprocessor Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Interfacing microprocessors with peripheral chips, DAC/ADC converters, LCD displays, stepper motors, and sensors."),
        Course(code="EE411", name="Embedded Systems", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Microcontroller architectures, interrupt handling, timers, GPIO, serial communication, and real-time operating systems (RTOS)."),
        Course(code="DEPT_ELEC2", name="Department Elective (2)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Second CSE department elective course."),
        Course(code="CS411", name="Artificial Intelligence", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Heuristic search, logic and knowledge representation, machine learning algorithms, clustering, classification, and neural networks."),
        Course(code="UNIV_ELEC2", name="University Elective (2)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Second university elective course from the approved elective list."),
        Course(code="UNIV201", name="Fundamentals of Research Methods", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Techniques for choosing research topics, writing literature reviews, experimental design, and formatting research outputs."),

        # YEAR 5 — FIRST SEMESTER
        Course(code="EE411L", name="Embedded Systems Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Programming ARM Cortex microcontrollers in C to control hardware peripherals and interface with various sensors."),
        Course(code="CS412L", name="Linux Lab", credits=1,
               department_id=dept_ids["CSE"], course_type="required",
               description="Linux command line, script writing, system administration, package management, and basic server setups."),
        Course(code="DEPT_ELEC3", name="Department Elective (3)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Third CSE department elective course."),
        Course(code="PHYS201", name="Classical Mechanics", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Kinematics, dynamics, system of particles, rigid body rotation, Lagrange's equations, and central force motion."),
        Course(code="EE401", name="Engineering Project Management", credits=3,
               department_id=dept_ids["CSE"], course_type="required",
               description="Project scheduling (PERT/CPM), cost estimation, quality assurance, team management, and engineering ethics."),
        Course(code="CSE499A", name="Senior Project I", credits=3,
               department_id=dept_ids["CSE"], course_type="capstone",
               description="Initial research, design, and hardware-software architectural specifications of the graduation project.",
               min_credits=110, min_gpa=Decimal("2.00")),
        Course(code="FREE_ELEC1", name="Free Elective (1)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="First free elective from any university offerings."),

        # YEAR 5 — SECOND SEMESTER
        Course(code="DEPT_ELEC4", name="Department Elective (4)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Fourth CSE department elective course."),
        Course(code="UNIV_ELEC3", name="University Elective (3)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Third university elective course."),
        Course(code="UNIV_ELEC4", name="University Elective (4)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Fourth university elective course."),
        Course(code="CSE499B", name="Senior Project II", credits=3,
               department_id=dept_ids["CSE"], course_type="capstone",
               description="Implementation, testing, hardware-software integration, project defense, and writing final documentation.",
               min_credits=110, min_gpa=Decimal("2.00")),
        Course(code="CS490", name="Internship I", credits=3,
               department_id=dept_ids["CSE"], course_type="internship",
               description="Practical field training in an approved engineering or IT company.",
               min_credits=90, min_gpa=Decimal("2.00")),
        Course(code="FREE_ELEC2", name="Free Elective (2)", credits=3,
               department_id=dept_ids["CSE"], course_type="elective",
               description="Second free elective from any university offerings."),
    ]
    session.add_all(courses)
    await session.flush()
    return {c.code: c.id for c in courses}


async def seed_prerequisites(session: AsyncSession, course_ids: dict[str, int]) -> None:
    """Seed prerequisite chains matching cse_program_tree.txt."""
    prereqs = [
        # Year 1 -> Year 2
        Prerequisite(course_id=course_ids["CS112"], prerequisite_id=course_ids["CS111"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE211"], prerequisite_id=course_ids["CS111"], min_grade="D"),
        Prerequisite(course_id=course_ids["PHYS102"], prerequisite_id=course_ids["PHYS101"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH102"], prerequisite_id=course_ids["MATH101"], min_grade="D"),
        Prerequisite(course_id=course_ids["EL102"], prerequisite_id=course_ids["EL101"], min_grade="D"),
        
        # Year 2 -> Semester 1 & 2
        Prerequisite(course_id=course_ids["EE201"], prerequisite_id=course_ids["EE101"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS211"], prerequisite_id=course_ids["CS112"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH211"], prerequisite_id=course_ids["CS112"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH201"], prerequisite_id=course_ids["MATH102"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH201"], prerequisite_id=course_ids["PHYS102"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE212"], prerequisite_id=course_ids["PHYS102"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE212"], prerequisite_id=course_ids["MATH102"], min_grade="D"),
        
        Prerequisite(course_id=course_ids["EE202"], prerequisite_id=course_ids["EE201"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE221"], prerequisite_id=course_ids["EE211"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS212"], prerequisite_id=course_ids["CS211"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH202"], prerequisite_id=course_ids["MATH201"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE222"], prerequisite_id=course_ids["MATH201"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE222"], prerequisite_id=course_ids["EE212"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE213"], prerequisite_id=course_ids["EE212"], min_grade="D"),
        
        # Year 3
        Prerequisite(course_id=course_ids["EE311"], prerequisite_id=course_ids["EE221"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS311"], prerequisite_id=course_ids["CS212"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS312"], prerequisite_id=course_ids["CS212"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE312"], prerequisite_id=course_ids["EE213"], min_grade="D"),
        
        Prerequisite(course_id=course_ids["EE321"], prerequisite_id=course_ids["EE311"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE322"], prerequisite_id=course_ids["EE311"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE322"], prerequisite_id=course_ids["EE221"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS321"], prerequisite_id=course_ids["EE311"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH301"], prerequisite_id=course_ids["CS312"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH301"], prerequisite_id=course_ids["MATH202"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE313"], prerequisite_id=course_ids["EE312"], min_grade="D"),
        
        # Year 4
        Prerequisite(course_id=course_ids["EE322L"], prerequisite_id=course_ids["EE322"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS322"], prerequisite_id=course_ids["CS311"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS323"], prerequisite_id=course_ids["CS311"], min_grade="D"),
        Prerequisite(course_id=course_ids["MATH302"], prerequisite_id=course_ids["MATH301"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE312L"], prerequisite_id=course_ids["EE313"], min_grade="D"),
        
        Prerequisite(course_id=course_ids["EE411"], prerequisite_id=course_ids["EE322"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS411"], prerequisite_id=course_ids["CS312"], min_grade="D"),
        
        # Year 5
        Prerequisite(course_id=course_ids["EE411L"], prerequisite_id=course_ids["EE411"], min_grade="D"),
        Prerequisite(course_id=course_ids["CS412L"], prerequisite_id=course_ids["CS321"], min_grade="D"),
        Prerequisite(course_id=course_ids["PHYS201"], prerequisite_id=course_ids["PHYS102"], min_grade="D"),
        Prerequisite(course_id=course_ids["PHYS201"], prerequisite_id=course_ids["MATH202"], min_grade="D"),
        Prerequisite(course_id=course_ids["EE401"], prerequisite_id=course_ids["CS323"], min_grade="D"),
        
        # Senior Projects
        Prerequisite(course_id=course_ids["CSE499A"], prerequisite_id=course_ids["CS323"], min_grade="D"),
        Prerequisite(course_id=course_ids["CSE499B"], prerequisite_id=course_ids["CSE499A"], min_grade="D"),
    ]
    session.add_all(prereqs)
    await session.flush()


async def seed_students(
    session: AsyncSession,
    dept_ids: dict[str, int],
    instructor_ids: dict[str, int],
) -> dict[str, int]:
    """Seed 12 students with realistic Computer Systems Engineering (CSE) profiles."""
    students = [
        # --- High-performing senior, near graduation ---
        Student(
            student_number="2020-CSE-001", first_name="Khalid", last_name="Al-Mansoor",
            email="khalid.mansoor@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2020, total_credits=114, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("ahmad_rashid"),
        ),
        # --- Good student, mid-program ---
        Student(
            student_number="2021-CSE-002", first_name="Noor", last_name="Abdullah",
            email="noor.abdullah@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2021, total_credits=84, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("sarah_mitchell"),
        ),
        # --- Student on academic probation (low GPA) ---
        Student(
            student_number="2021-CSE-003", first_name="Tariq", last_name="Hassan",
            email="tariq.hassan@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2021, total_credits=49, status="active", academic_standing="probation",
            advisor_id=instructor_ids.get("ahmad_rashid"),
        ),
        # --- Freshman, just started ---
        Student(
            student_number="2024-CSE-004", first_name="Lina", last_name="Saeed",
            email="lina.saeed@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2024, total_credits=17, status="active", academic_standing="good",
        ),
        # --- IT student, steady progress ---
        Student(
            student_number="2022-IT-005", first_name="Mohammed", last_name="Farouk",
            email="mohammed.farouk@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2022, total_credits=65, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("omar_hassan"),
        ),
        # --- IT student with warnings ---
        Student(
            student_number="2022-IT-006", first_name="Aya", last_name="Ibrahim",
            email="aya.ibrahim@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2022, total_credits=55, status="active", academic_standing="warning",
            advisor_id=instructor_ids.get("layla_mahmoud"),
        ),
        # --- EE student ---
        Student(
            student_number="2021-EE-007", first_name="Yousef", last_name="Nasser",
            email="yousef.nasser@students.edu", department_id=dept_ids["EE"],
            enrollment_year=2021, total_credits=92, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("james_wilson"),
        ),
        # --- BA student ---
        Student(
            student_number="2023-BA-008", first_name="Rania", last_name="Othman",
            email="rania.othman@students.edu", department_id=dept_ids["BA"],
            enrollment_year=2023, total_credits=35, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("michael_chen"),
        ),
        # --- Graduated student ---
        Student(
            student_number="2019-CSE-009", first_name="Omar", last_name="Jaber",
            email="omar.jaber@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2019, total_credits=163, status="graduated", academic_standing="good",
        ),
        # --- Suspended student ---
        Student(
            student_number="2020-IT-010", first_name="Salma", last_name="Khoury",
            email="salma.khoury@students.edu", department_id=dept_ids["IT"],
            enrollment_year=2020, total_credits=40, status="suspended", academic_standing="dismissal",
        ),
        # --- Student who can attempt internship 2 ---
        Student(
            student_number="2020-CSE-011", first_name="Hassan", last_name="Darwish",
            email="hassan.darwish@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2020, total_credits=95, status="active", academic_standing="good",
            advisor_id=instructor_ids.get("sarah_mitchell"),
        ),
        # --- Student barely above probation threshold ---
        Student(
            student_number="2022-CSE-012", first_name="Dana", last_name="Zaydan",
            email="dana.zaydan@students.edu", department_id=dept_ids["CSE"],
            enrollment_year=2022, total_credits=60, status="active", academic_standing="good",
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
    """Seed enrollment records across multiple semesters, matching CSE courses and prerequisites."""
    enrollments = [
        # ====== Khalid (2020-CSE-001) — Senior, near graduation ======
        # Fall 2020 (17 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS111"],
                   semester="Fall", academic_year=2020, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS111L"],
                   semester="Fall", academic_year=2020, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2020, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["PHYS101L"],
                   semester="Fall", academic_year=2020, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2020, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS100"],
                   semester="Fall", academic_year=2020, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EL101"],
                   semester="Fall", academic_year=2020, status="completed", grade="B+", grade_points=Decimal("3.30")),

        # Spring 2021 (17 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE101"],
                   semester="Spring", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE211"],
                   semester="Spring", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS112"],
                   semester="Spring", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["PHYS102"],
                   semester="Spring", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH102"],
                   semester="Spring", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EL102"],
                   semester="Spring", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Fall 2021 (17 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE201"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE211L"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS211"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH211"],
                   semester="Fall", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH201"],
                   semester="Fall", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE212"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["UNIV_ELEC1"],
                   semester="Fall", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),

        # Spring 2022 (16 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE202"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE221"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS212"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH202"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE222"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE213"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Fall 2022 (17 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE311"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS311"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS311L"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS312"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE312"],
                   semester="Fall", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE212L"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["UNIV101"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),

        # Spring 2023 (18 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE321"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE322"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS321"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH301"],
                   semester="Spring", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE313"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["UNIV102"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Summer 2023 (1 credit)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE322L"],
                   semester="Summer", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Fall 2023 (11 credits)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS322"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CS323"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["MATH302"],
                   semester="Fall", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE312L"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EL201"],
                   semester="Fall", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),

        # Spring 2024 (In Progress)
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["CSE499A"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE321L"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE322L2"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2020-CSE-001"], course_id=course_ids["EE411"],
                   semester="Spring", academic_year=2024, status="in_progress"),


        # ====== Noor (2021-CSE-002) — Good student, mid-program ======
        # Fall 2021 (17 credits)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS111"],
                   semester="Fall", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS111L"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["PHYS101L"],
                   semester="Fall", academic_year=2021, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2021, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS100"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EL101"],
                   semester="Fall", academic_year=2021, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Spring 2022 (17 credits)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE101"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE211"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS112"],
                   semester="Spring", academic_year=2022, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["PHYS102"],
                   semester="Spring", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["MATH102"],
                   semester="Spring", academic_year=2022, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EL102"],
                   semester="Spring", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Fall 2022 (17 credits)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE201"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE211L"],
                   semester="Fall", academic_year=2022, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS211"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["MATH211"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["MATH201"],
                   semester="Fall", academic_year=2022, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE212"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["UNIV_ELEC1"],
                   semester="Fall", academic_year=2022, status="completed", grade="B", grade_points=Decimal("3.00")),

        # Spring 2023 (16 credits)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE202"],
                   semester="Spring", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE221"],
                   semester="Spring", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS212"],
                   semester="Spring", academic_year=2023, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["MATH202"],
                   semester="Spring", academic_year=2023, status="completed", grade="B-", grade_points=Decimal("2.70")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE222"],
                   semester="Spring", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE213"],
                   semester="Spring", academic_year=2023, status="completed", grade="B", grade_points=Decimal("3.00")),

        # Fall 2023 (17 credits)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE311"],
                   semester="Fall", academic_year=2023, status="completed", grade="B+", grade_points=Decimal("3.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS311"],
                   semester="Fall", academic_year=2023, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS311L"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS312"],
                   semester="Fall", academic_year=2023, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE312"],
                   semester="Fall", academic_year=2023, status="completed", grade="C+", grade_points=Decimal("2.30")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE212L"],
                   semester="Fall", academic_year=2023, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["UNIV101"],
                   semester="Fall", academic_year=2023, status="completed", grade="B-", grade_points=Decimal("2.70")),

        # Spring 2024 (In Progress)
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE321"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["EE322"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2021-CSE-002"], course_id=course_ids["CS321"],
                   semester="Spring", academic_year=2024, status="in_progress"),


        # ====== Tariq (2021-CSE-003) — On probation ======
        # Fall 2021 (17 credits)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS111"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS111L"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2021, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["PHYS101L"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2021, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS100"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EL101"],
                   semester="Fall", academic_year=2021, status="completed", grade="C", grade_points=Decimal("2.00")),

        # Spring 2022 (11 credits completed, 6 failed)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE101"],
                   semester="Spring", academic_year=2022, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE211"],
                   semester="Spring", academic_year=2022, status="completed", grade="C-", grade_points=Decimal("1.70")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS112"],
                   semester="Spring", academic_year=2022, status="completed", grade="C-", grade_points=Decimal("1.70")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["PHYS102"],
                   semester="Spring", academic_year=2022, status="failed", grade="F", grade_points=Decimal("0.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH102"],
                   semester="Spring", academic_year=2022, status="failed", grade="F", grade_points=Decimal("0.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EL102"],
                   semester="Spring", academic_year=2022, status="completed", grade="C", grade_points=Decimal("2.00")),

        # Fall 2022 (8 credits)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE201"],
                   semester="Fall", academic_year=2022, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE211L"],
                   semester="Fall", academic_year=2022, status="completed", grade="C", grade_points=Decimal("2.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS211"],
                   semester="Fall", academic_year=2022, status="completed", grade="D+", grade_points=Decimal("1.30")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH211"],
                   semester="Fall", academic_year=2022, status="completed", grade="D+", grade_points=Decimal("1.30")),

        # Spring 2023 (6 credits)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["PHYS102"],
                   semester="Spring", academic_year=2023, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH102"],
                   semester="Spring", academic_year=2023, status="completed", grade="D", grade_points=Decimal("1.00")),

        # Fall 2023 (7 credits completed, 3 failed)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH201"],
                   semester="Fall", academic_year=2023, status="completed", grade="D+", grade_points=Decimal("1.30")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE212"],
                   semester="Fall", academic_year=2023, status="completed", grade="D", grade_points=Decimal("1.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE202"],
                   semester="Fall", academic_year=2023, status="completed", grade="B", grade_points=Decimal("3.00")),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE221"],
                   semester="Fall", academic_year=2023, status="failed", grade="F", grade_points=Decimal("0.00")),

        # Spring 2024 (In Progress)
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["EE221"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["CS212"],
                   semester="Spring", academic_year=2024, status="in_progress"),
        Enrollment(student_id=student_ids["2021-CSE-003"], course_id=course_ids["MATH202"],
                   semester="Spring", academic_year=2024, status="in_progress"),


        # ====== Omar (2019-CSE-009) — Graduated ======
        Enrollment(student_id=student_ids["2019-CSE-009"], course_id=course_ids["CS111"],
                   semester="Fall", academic_year=2019, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2019-CSE-009"], course_id=course_ids["CSE499B"],
                   semester="Spring", academic_year=2023, status="completed", grade="A-", grade_points=Decimal("3.70")),

        # ====== Lina (2024-CSE-004) — Freshman ======
        # Fall 2024 (17 credits)
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["CS111"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["CS111L"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["PHYS101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["PHYS101L"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["MATH101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A-", grade_points=Decimal("3.70")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["CS100"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["EL101"],
                   semester="Fall", academic_year=2024, status="completed", grade="A", grade_points=Decimal("4.00")),

        # Spring 2025 (In Progress)
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["CS112"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["EE101"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["EE211"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["PHYS102"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["MATH102"],
                   semester="Spring", academic_year=2025, status="in_progress"),
        Enrollment(student_id=student_ids["2024-CSE-004"], course_id=course_ids["EL102"],
                   semester="Spring", academic_year=2025, status="in_progress"),
    ]
    session.add_all(enrollments)
    await session.flush()


async def seed_graduation_requirements(
    session: AsyncSession,
    dept_ids: dict[str, int],
    course_ids: dict[str, int],
) -> None:
    """Seed graduation requirements for CSE and other departments."""
    # CSE graduation requirements
    cse_req = GraduationRequirement(
        department_id=dept_ids["CSE"],
        min_total_credits=163,
        min_gpa=Decimal("2.00"),
        min_major_credits=87,
        max_years=10,
        requires_internship=True,
        requires_capstone=True,
        description="Bachelor of Science in Computer Systems Engineering graduation requirements.",
    )
    session.add(cse_req)
    await session.flush()

    # Core required courses for CSE graduation
    cse_required = [
        "CS111", "CS111L", "PHYS101", "PHYS101L", "MATH101", "CS100", "EL101",
        "EE101", "EE211", "CS112", "PHYS102", "MATH102", "EL102",
        "EE201", "EE211L", "CS211", "MATH211", "MATH201", "EE212",
        "EE202", "EE221", "CS212", "MATH202", "EE222", "EE213",
        "EE311", "CS311", "CS311L", "CS312", "EE312", "EE212L", "UNIV101",
        "EE321", "EE322", "CS321", "MATH301", "EE313", "UNIV102",
        "EE322L", "CS322", "CS323", "MATH302", "EE312L", "EL201",
        "EE321L", "EE322L2", "EE411", "CS411", "UNIV201",
        "EE411L", "CS412L", "PHYS201", "EE401", "CS490", "CSE499A",
        "CSE499B",
    ]
    for code in cse_required:
        if code in course_ids:
            session.add(RequiredCourse(
                graduation_req_id=cse_req.id,
                course_id=course_ids[code],
                is_core=not code.startswith("UNIV") and not code.startswith("EL"),
            ))
    await session.flush()


async def seed_warnings(session: AsyncSession, student_ids: dict[str, int]) -> None:
    """Seed academic warnings for relevant students."""
    warnings = [
        Warning(
            student_id=student_ids["2021-CSE-003"],
            warning_type="gpa_probation",
            description="Cumulative GPA has fallen below 2.0 (current: 1.85). Student is placed on academic probation per Article 19.3 of the CSE Academic Regulations.",
            semester="Fall", academic_year=2023, is_resolved=False,
        ),
        Warning(
            student_id=student_ids["2021-CSE-003"],
            warning_type="gpa_warning",
            description="GPA dropped below 2.0 for the second consecutive semester. If GPA is not raised above 2.0 by end of next semester, student may face dismissal.",
            semester="Spring", academic_year=2023, is_resolved=False,
        ),
        Warning(
            student_id=student_ids["2022-CSE-012"],
            warning_type="gpa_warning",
            description="Cumulative GPA is 2.05, very close to the CSE probation threshold of 2.00.",
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
            student_id=student_ids["2020-CSE-001"],
            is_active=True,
        ),
        User(
            username="noor",
            hashed_password=hash_password("student123"),
            email="noor.abdullah@students.edu",
            full_name="Noor Abdullah",
            role="student",
            student_id=student_ids["2021-CSE-002"],
            is_active=True,
        ),
        User(
            username="tariq",
            hashed_password=hash_password("student123"),
            email="tariq.hassan@students.edu",
            full_name="Tariq Hassan",
            role="student",
            student_id=student_ids["2021-CSE-003"],
            is_active=True,
        ),
        User(
            username="hassan",
            hashed_password=hash_password("student123"),
            email="hassan.darwish@students.edu",
            full_name="Hassan Darwish",
            role="student",
            student_id=student_ids["2020-CSE-011"],
            is_active=True,
        ),
        User(
            username="lina",
            hashed_password=hash_password("student123"),
            email="lina.saeed@students.edu",
            full_name="Lina Saeed",
            role="student",
            student_id=student_ids["2024-CSE-004"],
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
    """Execute all seed functions in order, resetting the tables first."""
    logger.info("Resetting database and starting database seeding...")

    # Drop and recreate all tables for a clean reset
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables reset successfully")

    async with async_session_factory() as session:
        async with session.begin():
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



