# ============================================================
# Citation Generator — Source Attribution
# ============================================================
"""
Extracts and formats citations from retrieved Haystack documents.
Provides proper source attribution for regulation references
used in the assistant's responses.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from haystack import Document

from app.db.schemas import Citation

logger = logging.getLogger(__name__)


def extract_citations(documents: List[Document]) -> List[Citation]:
    """
    Extract citation information from Haystack documents.

    Each citation includes:
    - source: The regulation document title
    - section: Section/article number if identifiable
    - text: A relevant excerpt from the document
    - score: Relevance score from retrieval

    Args:
        documents: List of Haystack Document objects from retrieval.

    Returns:
        List of Citation objects, deduplicated by source.
    """
    if not documents:
        return []

    citations = []
    seen_sources = set()

    for doc in documents:
        meta = doc.meta or {}
        source_title = meta.get("title", "Unknown Regulation")
        source_file = meta.get("source", "")

        # Create a unique key for deduplication
        source_key = f"{source_title}:{source_file}"
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)

        # Try to extract section/article numbers from the content
        section = _extract_section_reference(doc.content)

        # Get a clean excerpt (first 200 chars)
        excerpt = _clean_excerpt(doc.content, max_length=250)

        citations.append(Citation(
            source=source_title,
            section=section,
            text=excerpt,
            score=round(doc.score, 3) if doc.score else None,
        ))

    logger.info(f"Extracted {len(citations)} citations from {len(documents)} documents")
    return citations


def _extract_section_reference(content: str) -> Optional[str]:
    """
    Try to extract a section, article, or clause reference from document content.

    Patterns recognized:
    - "Article 12.3"
    - "Section 5.1"
    - "Clause 3.2.1"
    - "§ 4.5"
    - "Chapter 3"
    """
    if not content:
        return None

    patterns = [
        r'(Article\s+\d+(?:\.\d+)*)',
        r'(Section\s+\d+(?:\.\d+)*)',
        r'(Clause\s+\d+(?:\.\d+)*)',
        r'(§\s*\d+(?:\.\d+)*)',
        r'(Chapter\s+\d+)',
        r'(Rule\s+\d+(?:\.\d+)*)',
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None


def _clean_excerpt(content: str, max_length: int = 250) -> str:
    """
    Create a clean excerpt from document content.
    Attempts to break at sentence boundaries.
    """
    if not content:
        return ""

    # Clean whitespace
    text = " ".join(content.split())

    if len(text) <= max_length:
        return text

    # Try to break at a sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind(".")
    last_question = truncated.rfind("?")
    last_exclaim = truncated.rfind("!")

    break_point = max(last_period, last_question, last_exclaim)
    if break_point > max_length * 0.5:  # Only break if we keep at least 50%
        return truncated[: break_point + 1]

    return truncated + "..."


def format_citations_markdown(citations: List[Citation]) -> str:
    """
    Format citations as a markdown string for display.
    """
    if not citations:
        return ""

    lines = ["\n**Sources:**"]
    for i, citation in enumerate(citations, 1):
        source_ref = citation.source
        if citation.section:
            source_ref += f", {citation.section}"

        lines.append(f"  [{i}] {source_ref}")
        if citation.text:
            # Show a brief excerpt
            excerpt = citation.text[:150] + "..." if len(citation.text) > 150 else citation.text
            lines.append(f"      _\"{excerpt}\"_")

    return "\n".join(lines)
