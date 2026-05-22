# ============================================================
# Decision Engine Tests
# ============================================================
"""
Tests for the decision engine's deterministic policy rules.
"""

from __future__ import annotations

import pytest

from app.decision.rules import (
    check_credit_threshold,
    check_gpa_standing,
    check_prerequisite_results,
    check_student_active,
)


class TestGPAStanding:
    """Test GPA standing checks."""

    def test_good_standing(self):
        result = check_gpa_standing({"gpa": 3.5, "academic_standing": "good"})
        assert result["passed"] is True
        assert result["severity"] == "none"

    def test_probation(self):
        result = check_gpa_standing({"gpa": 1.85, "academic_standing": "probation"})
        assert result["passed"] is False
        assert result["severity"] == "medium"

    def test_severe_probation(self):
        result = check_gpa_standing({"gpa": 1.3, "academic_standing": "probation"})
        assert result["passed"] is False
        assert result["severity"] == "high"

    def test_dismissal_risk(self):
        result = check_gpa_standing({"gpa": 0.8, "academic_standing": "dismissal"})
        assert result["passed"] is False
        assert result["severity"] == "critical"

    def test_exactly_2_0(self):
        result = check_gpa_standing({"gpa": 2.0, "academic_standing": "good"})
        assert result["passed"] is True


class TestCreditThreshold:
    """Test credit threshold checks."""

    def test_credits_met(self):
        result = check_credit_threshold({"total_credits": 95}, required_credits=90)
        assert result["passed"] is True

    def test_credits_not_met(self):
        result = check_credit_threshold({"total_credits": 50}, required_credits=60)
        assert result["passed"] is False

    def test_no_requirement(self):
        result = check_credit_threshold({"total_credits": 30}, required_credits=0)
        assert result["passed"] is True


class TestStudentActive:
    """Test student active status check."""

    def test_active(self):
        result = check_student_active({"status": "active"})
        assert result["passed"] is True

    def test_suspended(self):
        result = check_student_active({"status": "suspended"})
        assert result["passed"] is False

    def test_graduated(self):
        result = check_student_active({"status": "graduated"})
        assert result["passed"] is False


class TestPrerequisiteResults:
    """Test prerequisite check evaluation."""

    def test_all_met(self):
        result = check_prerequisite_results({
            "all_met": True,
            "prerequisites": [
                {"prerequisite_code": "CS101", "met": True},
            ],
        })
        assert result["passed"] is True

    def test_not_met(self):
        result = check_prerequisite_results({
            "all_met": False,
            "prerequisites": [
                {"prerequisite_code": "CS101", "met": True, "status": "MET", "min_grade_required": "D", "grade_achieved": "B"},
                {"prerequisite_code": "CS102", "met": False, "status": "NOT_TAKEN", "min_grade_required": "D", "grade_achieved": None},
            ],
        })
        assert result["passed"] is False
        assert "CS102" in result["detail"]

    def test_error_data(self):
        result = check_prerequisite_results({"error": "Course not found"})
        assert result["passed"] is False

    def test_no_prerequisites(self):
        result = check_prerequisite_results({
            "all_met": True,
            "prerequisites": [],
        })
        assert result["passed"] is True
