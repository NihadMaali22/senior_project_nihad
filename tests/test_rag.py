# ============================================================
# RAG Pipeline Tests
# ============================================================
"""
Tests for the RAG retrieval and citation functionality.
"""

from __future__ import annotations

import pytest

from app.citation.generator import _clean_excerpt, _extract_section_reference


class TestSectionExtraction:
    """Test section reference extraction from document content."""

    def test_extract_article(self):
        content = "According to Article 12.3, students must complete internship."
        assert _extract_section_reference(content) == "Article 12.3"

    def test_extract_section(self):
        content = "As stated in Section 5.1, registration requires..."
        assert _extract_section_reference(content) == "Section 5.1"

    def test_extract_chapter(self):
        content = "Chapter 3 covers graduation requirements."
        assert _extract_section_reference(content) == "Chapter 3"

    def test_no_section(self):
        content = "Students must maintain good standing."
        assert _extract_section_reference(content) is None

    def test_empty_content(self):
        assert _extract_section_reference("") is None
        assert _extract_section_reference(None) is None


class TestCleanExcerpt:
    """Test excerpt cleaning and truncation."""

    def test_short_content(self):
        content = "This is a short text."
        assert _clean_excerpt(content) == "This is a short text."

    def test_long_content_breaks_at_sentence(self):
        content = "First sentence. " * 20
        excerpt = _clean_excerpt(content, max_length=100)
        assert excerpt.endswith(".")
        assert len(excerpt) <= 100

    def test_empty_content(self):
        assert _clean_excerpt("") == ""
