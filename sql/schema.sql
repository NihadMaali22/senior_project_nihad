-- ============================================================
-- Decision-Making Academic Assistant — Database Schema
-- PostgreSQL 16+
-- ============================================================
-- This schema defines the complete university academic database
-- including students, courses, prerequisites, enrollments,
-- grades, warnings, graduation requirements, and auth users.
-- ============================================================

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. DEPARTMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(10) NOT NULL UNIQUE,
    description     TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 2. INSTRUCTORS
-- ============================================================
CREATE TABLE IF NOT EXISTS instructors (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    email           VARCHAR(200) UNIQUE NOT NULL,
    department_id   INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    title           VARCHAR(100),          -- e.g., "Professor", "Assistant Professor"
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 3. COURSES
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) NOT NULL UNIQUE,
    name            VARCHAR(300) NOT NULL,
    credits         INTEGER NOT NULL CHECK (credits > 0),
    department_id   INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    description     TEXT,
    course_type     VARCHAR(50) DEFAULT 'required',   -- required, elective, internship, capstone
    min_gpa         NUMERIC(3,2) DEFAULT 0.0,         -- minimum GPA to register
    min_credits     INTEGER DEFAULT 0,                 -- minimum completed credits to register
    max_capacity    INTEGER DEFAULT 40,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 4. PREREQUISITES
-- ============================================================
CREATE TABLE IF NOT EXISTS prerequisites (
    id                  SERIAL PRIMARY KEY,
    course_id           INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    prerequisite_id     INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    min_grade           VARCHAR(5) DEFAULT 'D',   -- Minimum passing grade required
    is_mandatory        BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(course_id, prerequisite_id),
    CHECK (course_id != prerequisite_id)
);

-- ============================================================
-- 5. STUDENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id                  SERIAL PRIMARY KEY,
    student_number      VARCHAR(20) NOT NULL UNIQUE,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(200) UNIQUE NOT NULL,
    department_id       INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    enrollment_year     INTEGER NOT NULL,
    total_credits       INTEGER DEFAULT 0,             -- Total earned credit hours
    gpa                 NUMERIC(4,3) DEFAULT 0.000,    -- Cumulative GPA (0.000 - 4.000)
    status              VARCHAR(30) DEFAULT 'active',   -- active, graduated, suspended, withdrawn
    academic_standing   VARCHAR(30) DEFAULT 'good',     -- good, probation, warning, dismissal
    advisor_id          INTEGER REFERENCES instructors(id) ON DELETE SET NULL,
    phone               VARCHAR(30),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 6. ENROLLMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS enrollments (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id       INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    instructor_id   INTEGER REFERENCES instructors(id) ON DELETE SET NULL,
    semester        VARCHAR(20) NOT NULL,    -- 'Fall', 'Spring', 'Summer'
    academic_year   INTEGER NOT NULL,        -- e.g., 2024
    status          VARCHAR(20) DEFAULT 'enrolled',  -- enrolled, completed, failed, withdrawn, in_progress
    grade           VARCHAR(5),              -- A, B+, B, C+, C, D+, D, F, W, I
    grade_points    NUMERIC(3,2),            -- 4.00, 3.50, 3.00, etc.
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(student_id, course_id, semester, academic_year)
);

-- ============================================================
-- 7. GRADUATION REQUIREMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS graduation_requirements (
    id                  SERIAL PRIMARY KEY,
    department_id       INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    min_total_credits   INTEGER NOT NULL DEFAULT 132,
    min_gpa             NUMERIC(3,2) NOT NULL DEFAULT 2.00,
    min_major_credits   INTEGER DEFAULT 90,
    max_years           INTEGER DEFAULT 7,
    requires_internship BOOLEAN DEFAULT TRUE,
    requires_capstone   BOOLEAN DEFAULT TRUE,
    description         TEXT,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 8. REQUIRED COURSES FOR GRADUATION
-- ============================================================
CREATE TABLE IF NOT EXISTS required_courses (
    id                      SERIAL PRIMARY KEY,
    graduation_req_id       INTEGER NOT NULL REFERENCES graduation_requirements(id) ON DELETE CASCADE,
    course_id               INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    is_core                 BOOLEAN DEFAULT TRUE,    -- core vs elective
    UNIQUE(graduation_req_id, course_id)
);

-- ============================================================
-- 9. ACADEMIC WARNINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS warnings (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    warning_type    VARCHAR(50) NOT NULL,     -- gpa_warning, gpa_probation, attendance, academic_integrity
    description     TEXT NOT NULL,
    semester        VARCHAR(20) NOT NULL,
    academic_year   INTEGER NOT NULL,
    is_resolved     BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 10. CONVERSATION HISTORY (for memory)
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_history (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER,
    session_id      VARCHAR(100) NOT NULL,
    role            VARCHAR(20) NOT NULL,      -- 'user', 'assistant', 'system'
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 11. USERS (authentication)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) NOT NULL UNIQUE,
    hashed_password VARCHAR(300) NOT NULL,
    email           VARCHAR(200),
    full_name       VARCHAR(200),
    role            VARCHAR(30) DEFAULT 'student',    -- admin, student, advisor
    student_id      INTEGER REFERENCES students(id) ON DELETE SET NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- INDEXES for query performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_students_student_number ON students(student_number);
CREATE INDEX IF NOT EXISTS idx_students_department ON students(department_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_status ON enrollments(status);
CREATE INDEX IF NOT EXISTS idx_enrollments_semester ON enrollments(semester, academic_year);
CREATE INDEX IF NOT EXISTS idx_prerequisites_course ON prerequisites(course_id);
CREATE INDEX IF NOT EXISTS idx_warnings_student ON warnings(student_id);
CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_history(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
