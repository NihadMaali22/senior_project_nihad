# ============================================================
# SQL Agent Tests
# ============================================================
"""
Tests for the SQL Agent query classification and execution.
"""

from __future__ import annotations

import pytest

from app.sql_agent.agent import classify_query_type, extract_course_code


class TestExtractCourseCode:
    """Test course code extraction from natural language."""

    def test_extract_direct_code(self):
        assert extract_course_code("Can I take CS201?") == "CS201"

    def test_extract_math_code(self):
        assert extract_course_code("What are the prerequisites for MATH101?") == "MATH101"

    def test_extract_internship_1(self):
        assert extract_course_code("Can I register for Internship 1?") == "CS490"

    def test_extract_internship_2(self):
        assert extract_course_code("Can I take Internship 2?") == "CS491"

    def test_extract_capstone(self):
        assert extract_course_code("Am I eligible for the capstone project?") == "CS499"

    def test_extract_data_structures(self):
        assert extract_course_code("Can I take data structures?") == "CS201"

    def test_no_course_code(self):
        assert extract_course_code("What is my GPA?") is None

    def test_extract_case_insensitive(self):
        assert extract_course_code("Tell me about cs301") == "CS301"


class TestClassifyQueryType:
    """Test query type classification."""

    def test_gpa_is_sql(self):
        assert classify_query_type("What is my GPA?") == "get_gpa"

    def test_courses_is_sql(self):
        assert classify_query_type("Show me my completed courses") == "get_completed_courses"

    def test_current_is_sql(self):
        assert classify_query_type("What am I enrolled in this semester?") == "get_current_enrollments"

    def test_warnings_is_sql(self):
        assert classify_query_type("Do I have any academic warnings?") == "get_warnings"

    def test_graduation_is_sql(self):
        assert classify_query_type("What are my graduation requirements?") == "get_graduation_requirements"

    def test_can_register_is_eligibility(self):
        assert classify_query_type("Can I register for CS301?") == "check_eligibility"

    def test_prerequisites_is_prereq(self):
        assert classify_query_type("What are the prerequisites for CS202?") == "get_prerequisites"

    def test_failed_courses(self):
        assert classify_query_type("What courses did I fail?") == "get_failed_courses"
