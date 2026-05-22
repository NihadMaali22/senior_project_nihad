# ============================================================
# Decision Engine — Deterministic Policy Rules
# ============================================================
"""
Pre-defined policy rules that provide deterministic checks
BEFORE the LLM does its reasoning. These act as guardrails
and supplements to the LLM's analysis.

Each rule function returns a dict with:
- rule_name: identifier
- passed: bool
- detail: explanation string
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def check_gpa_standing(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check GPA thresholds against university policy.

    Policy rules:
    - GPA < 1.0  → Academic dismissal risk
    - GPA < 1.5  → Severe probation
    - GPA < 2.0  → Academic probation
    - GPA >= 2.0 → Good standing
    """
    gpa = student_data.get("gpa", 0.0)
    standing = student_data.get("academic_standing", "unknown")

    if gpa < 1.0:
        return {
            "rule_name": "gpa_standing",
            "passed": False,
            "severity": "critical",
            "detail": (
                f"GPA is {gpa:.3f}, which is below 1.0. "
                f"Per university regulations, the student faces academic dismissal. "
                f"Current standing: {standing}."
            ),
        }
    elif gpa < 1.5:
        return {
            "rule_name": "gpa_standing",
            "passed": False,
            "severity": "high",
            "detail": (
                f"GPA is {gpa:.3f}, which is below 1.5. "
                f"Student is on severe academic probation. Registration may be restricted. "
                f"Current standing: {standing}."
            ),
        }
    elif gpa < 2.0:
        return {
            "rule_name": "gpa_standing",
            "passed": False,
            "severity": "medium",
            "detail": (
                f"GPA is {gpa:.3f}, which is below the 2.0 minimum. "
                f"Student is on academic probation. Some courses may have GPA restrictions. "
                f"Current standing: {standing}."
            ),
        }
    else:
        return {
            "rule_name": "gpa_standing",
            "passed": True,
            "severity": "none",
            "detail": f"GPA is {gpa:.3f}. Academic standing: {standing}. No GPA issues.",
        }


def check_credit_threshold(
    student_data: Dict[str, Any],
    required_credits: int = 0,
    context: str = "",
) -> Dict[str, Any]:
    """
    Check if the student has enough completed credits.

    Used for:
    - Internship registration (requires 60-90 credits)
    - Capstone project (requires 110+ credits)
    - Graduation eligibility
    """
    total_credits = student_data.get("total_credits", 0)

    if required_credits > 0 and total_credits < required_credits:
        return {
            "rule_name": "credit_threshold",
            "passed": False,
            "detail": (
                f"Student has {total_credits} completed credits. "
                f"{context + ' r' if context else 'R'}equires {required_credits} credits. "
                f"Shortfall: {required_credits - total_credits} credits."
            ),
        }
    else:
        return {
            "rule_name": "credit_threshold",
            "passed": True,
            "detail": (
                f"Student has {total_credits} completed credits"
                + (f" (≥ {required_credits} required)." if required_credits > 0 else ".")
            ),
        }


def check_student_active(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check if the student's enrollment status allows academic activities."""
    status = student_data.get("status", "unknown")

    if status != "active":
        return {
            "rule_name": "student_active",
            "passed": False,
            "detail": (
                f"Student status is '{status}'. "
                f"Only 'active' students can register for courses or perform academic activities."
            ),
        }
    return {
        "rule_name": "student_active",
        "passed": True,
        "detail": "Student status is 'active'. Eligible for academic activities.",
    }


def check_prerequisite_results(
    prereq_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate prerequisite check results from the SQL agent.
    """
    if not prereq_data or "error" in prereq_data:
        return {
            "rule_name": "prerequisites",
            "passed": False,
            "detail": prereq_data.get("error", "Could not verify prerequisites."),
        }

    all_met = prereq_data.get("all_met", False)
    prerequisites = prereq_data.get("prerequisites", [])

    if all_met:
        met_list = ", ".join([p["prerequisite_code"] for p in prerequisites])
        return {
            "rule_name": "prerequisites",
            "passed": True,
            "detail": f"All prerequisites met: {met_list}." if met_list else "No prerequisites required.",
        }
    else:
        unmet = [p for p in prerequisites if not p.get("met", False)]
        unmet_details = []
        for p in unmet:
            if p["status"] == "NOT_TAKEN":
                unmet_details.append(f"{p['prerequisite_code']} (not taken)")
            else:
                unmet_details.append(
                    f"{p['prerequisite_code']} (got {p.get('grade_achieved', '?')}, "
                    f"need {p['min_grade_required']})"
                )
        return {
            "rule_name": "prerequisites",
            "passed": False,
            "detail": f"Unmet prerequisites: {'; '.join(unmet_details)}.",
        }


def check_graduation_eligibility(
    grad_data: Dict[str, Any],
    student_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Comprehensive graduation eligibility check.
    Returns a list of rule check results.
    """
    results = []

    if not grad_data or "error" in grad_data:
        results.append({
            "rule_name": "graduation_data",
            "passed": False,
            "detail": grad_data.get("error", "Could not retrieve graduation requirements."),
        })
        return results

    # Credit check
    credits_remaining = grad_data.get("credits_remaining", 0)
    min_credits = grad_data.get("min_total_credits", 132)
    student_credits = student_data.get("total_credits", 0)

    results.append({
        "rule_name": "graduation_credits",
        "passed": credits_remaining == 0,
        "detail": (
            f"Credits: {student_credits}/{min_credits}. "
            + (f"Still need {credits_remaining} credits." if credits_remaining > 0 else "Credit requirement met.")
        ),
    })

    # GPA check
    gpa_met = grad_data.get("gpa_met", False)
    min_gpa = grad_data.get("min_gpa", 2.0)
    student_gpa = student_data.get("gpa", 0.0)

    results.append({
        "rule_name": "graduation_gpa",
        "passed": gpa_met,
        "detail": (
            f"GPA: {student_gpa:.3f} (minimum: {min_gpa}). "
            + ("GPA requirement met." if gpa_met else "GPA is below the minimum for graduation.")
        ),
    })

    # Required courses check
    completed = grad_data.get("required_courses_completed", 0)
    total = grad_data.get("required_courses_total", 0)
    all_done = completed >= total

    results.append({
        "rule_name": "graduation_courses",
        "passed": all_done,
        "detail": (
            f"Required courses: {completed}/{total} completed. "
            + ("All required courses completed." if all_done else f"Still need {total - completed} required courses.")
        ),
    })

    # Internship check
    if grad_data.get("requires_internship", False):
        # Check from required courses if internship courses are completed
        internship_courses = [
            c for c in grad_data.get("required_courses", [])
            if "intern" in c.get("course_code", "").lower() or "490" in c.get("course_code", "") or "491" in c.get("course_code", "")
        ]
        internship_done = all(c.get("completed", False) for c in internship_courses) if internship_courses else False

        results.append({
            "rule_name": "graduation_internship",
            "passed": internship_done,
            "detail": (
                "Internship requirement: "
                + ("Completed." if internship_done else "Internship not yet completed.")
            ),
        })

    # Capstone check
    if grad_data.get("requires_capstone", False):
        capstone_courses = [
            c for c in grad_data.get("required_courses", [])
            if "capstone" in c.get("course_name", "").lower() or "499" in c.get("course_code", "")
        ]
        capstone_done = all(c.get("completed", False) for c in capstone_courses) if capstone_courses else False

        results.append({
            "rule_name": "graduation_capstone",
            "passed": capstone_done,
            "detail": (
                "Capstone requirement: "
                + ("Completed." if capstone_done else "Capstone project not yet completed.")
            ),
        })

    return results


def run_all_checks(
    student_data: Dict[str, Any],
    prereq_data: Dict[str, Any] = None,
    grad_data: Dict[str, Any] = None,
    course_data: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """
    Run all applicable deterministic rule checks.

    Returns:
        List of rule check results.
    """
    results = []

    # Always check student status and GPA
    results.append(check_student_active(student_data))
    results.append(check_gpa_standing(student_data))

    # Check credit threshold if course data specifies a minimum
    if course_data:
        min_credits = course_data.get("min_credits", 0)
        if min_credits > 0:
            results.append(check_credit_threshold(
                student_data, min_credits,
                context=f"Course {course_data.get('code', '')}",
            ))

    # Check prerequisites if data is available
    if prereq_data:
        results.append(check_prerequisite_results(prereq_data))

    # Check graduation if data is available
    if grad_data:
        results.extend(check_graduation_eligibility(grad_data, student_data))

    return results


def format_checks_for_prompt(checks: List[Dict[str, Any]]) -> str:
    """Format rule check results for inclusion in the LLM prompt."""
    if not checks:
        return "No pre-computed checks available."

    lines = []
    for check in checks:
        status = "✅ PASS" if check["passed"] else "❌ FAIL"
        lines.append(f"  {status} | {check['rule_name']}: {check['detail']}")

    return "\n".join(lines)
