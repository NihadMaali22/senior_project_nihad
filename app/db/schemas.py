# ============================================================
# Pydantic Schemas — Request/Response Models
# ============================================================
"""
Pydantic models for API serialization and validation.
These schemas define the data contracts between the API and clients.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================
class StudentStatus(str, Enum):
    ACTIVE = "active"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class AcademicStanding(str, Enum):
    GOOD = "good"
    PROBATION = "probation"
    WARNING = "warning"
    DISMISSAL = "dismissal"


class EnrollmentStatus(str, Enum):
    ENROLLED = "enrolled"
    COMPLETED = "completed"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
    IN_PROGRESS = "in_progress"


class QueryType(str, Enum):
    SQL_ONLY = "SQL_ONLY"
    RAG_ONLY = "RAG_ONLY"
    HYBRID = "HYBRID"
    OFF_TOPIC = "OFF_TOPIC"


class DecisionOutcome(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CONDITIONAL = "CONDITIONAL"
    INFO = "INFO"


class UserRole(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"
    ADVISOR = "advisor"


# ============================================================
# Department Schemas
# ============================================================
class DepartmentBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# Course Schemas
# ============================================================
class CourseBase(BaseModel):
    code: str
    name: str
    credits: int
    description: Optional[str] = None
    course_type: str = "required"


class CourseResponse(CourseBase):
    id: int
    department_id: Optional[int] = None
    min_gpa: float = 0.0
    min_credits: int = 0
    is_active: bool = True

    model_config = {"from_attributes": True}


# ============================================================
# Student Schemas
# ============================================================
class StudentBase(BaseModel):
    student_number: str
    first_name: str
    last_name: str
    email: str


class StudentResponse(StudentBase):
    id: int
    department_id: Optional[int] = None
    enrollment_year: int
    total_credits: int = 0
    gpa: float = 0.0
    status: str = "active"
    academic_standing: str = "good"
    phone: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StudentSummary(BaseModel):
    """Compact student data used in decision-making."""
    id: int
    student_number: str
    full_name: str
    gpa: float
    total_credits: int
    status: str
    academic_standing: str
    department: Optional[str] = None
    enrollment_year: int


# ============================================================
# Enrollment Schemas
# ============================================================
class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    semester: str
    academic_year: int
    status: str
    grade: Optional[str] = None
    grade_points: Optional[float] = None

    model_config = {"from_attributes": True}


# ============================================================
# Warning Schemas
# ============================================================
class WarningResponse(BaseModel):
    id: int
    student_id: int
    warning_type: str
    description: str
    semester: str
    academic_year: int
    is_resolved: bool

    model_config = {"from_attributes": True}


# ============================================================
# Graduation Requirement Schemas
# ============================================================
class GraduationRequirementResponse(BaseModel):
    id: int
    department_id: int
    min_total_credits: int
    min_gpa: float
    min_major_credits: int
    max_years: int
    requires_internship: bool
    requires_capstone: bool
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ============================================================
# Assistant / Chat Schemas
# ============================================================
class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""
    question: str = Field(..., min_length=3, max_length=2000, description="The academic question")
    student_id: Optional[int] = Field(None, description="Student ID (auto-filled from JWT if omitted)")
    session_id: Optional[str] = Field(None, description="Conversation session ID for continuity")


class Citation(BaseModel):
    """A single citation from a regulation document."""
    source: str = Field(..., description="Document/regulation name")
    section: Optional[str] = Field(None, description="Section number or heading")
    text: str = Field(..., description="Relevant excerpt from the regulation")
    score: Optional[float] = Field(None, description="Relevance score")


class AskResponse(BaseModel):
    """Response from the /ask endpoint."""
    answer: str = Field(..., description="The generated answer")
    decision: Optional[DecisionOutcome] = Field(None, description="Decision outcome if applicable")
    reasoning: List[str] = Field(default_factory=list, description="Step-by-step reasoning")
    student_data: Optional[Dict[str, Any]] = Field(None, description="Relevant student data used")
    citations: List[Citation] = Field(default_factory=list, description="Regulation citations")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    query_type: QueryType = Field(..., description="How the query was classified")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


# ============================================================
# Document Ingestion Schemas
# ============================================================
class DocumentIngestRequest(BaseModel):
    """Request to ingest a regulation document."""
    title: str = Field(..., description="Document title")
    content: Optional[str] = Field(None, description="Raw text content (if not uploading a file)")
    source: str = Field(default="manual", description="Source identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentIngestResponse(BaseModel):
    """Response after document ingestion."""
    message: str
    documents_ingested: int
    chunks_created: int


class DocumentListResponse(BaseModel):
    """A document in the vector store."""
    id: str
    title: str
    source: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[str] = None


# ============================================================
# Admin Schemas
# ============================================================
class SystemStats(BaseModel):
    """System statistics for admin dashboard."""
    total_students: int
    total_courses: int
    total_enrollments: int
    total_documents: int
    total_conversations: int
    active_warnings: int
