# ============================================================
# Query Router — Intelligent Query Classification
# ============================================================
"""
Classifies incoming user questions into one of three categories:
1. SQL_ONLY   — Pure data lookups (GPA, courses, credits)
2. RAG_ONLY   — Pure policy/regulation lookups
3. HYBRID     — Requires both data + policy (decision-making)

Uses the Ollama local LLM for classification, with a keyword-based
fallback if the LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

import httpx

from app.config import get_settings
from app.db.schemas import QueryType

logger = logging.getLogger(__name__)
settings = get_settings()

# ============================================================
# Classification Prompt
# ============================================================
CLASSIFICATION_PROMPT = """You are a query classifier for a university academic assistant system.

Classify the following student question into EXACTLY ONE of these categories:

1. **SQL_ONLY** — The question can be answered purely from the student database.
   Examples: "What is my GPA?", "How many credits do I have?", "What courses did I fail?", "Show my current schedule"

2. **RAG_ONLY** — The question is about university policies, rules, or regulations and does NOT require student-specific data.
   Examples: "What is the withdrawal policy?", "What are the rules for academic probation?", "How many credits needed to graduate?"

3. **HYBRID** — The question requires BOTH student data AND university policies to make a decision or provide a personalized answer.
   Examples: "Can I register for Internship 2?", "Am I eligible to graduate?", "Why am I on academic probation?", "Can I take course X if I failed Y?"

Question: "{question}"

Respond with ONLY a JSON object in this exact format:
{{"category": "SQL_ONLY" | "RAG_ONLY" | "HYBRID", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}
"""


def _keyword_classify(question: str) -> QueryType:
    """
    Fallback keyword-based classification when LLM is unavailable.
    Uses pattern matching to determine query type.
    """
    q = question.lower().strip()

    # SQL-only patterns — pure data lookups
    sql_patterns = [
        r"\bmy gpa\b",
        r"\bwhat is my\b",
        r"\bhow many credits\b",
        r"\bmy courses\b",
        r"\bmy grades\b",
        r"\bmy schedule\b",
        r"\bcurrent.*enroll",
        r"\bcourses.*completed\b",
        r"\bcourses.*failed\b",
        r"\bmy.*warnings?\b",
        r"\bmy profile\b",
        r"\bshow me my\b",
        r"\blist my\b",
    ]

    # RAG-only patterns — policy/regulation lookups
    rag_patterns = [
        r"\bwhat is the.*policy\b",
        r"\bwhat are the.*rules\b",
        r"\bwhat are the.*requirements\b",
        r"\bwithdrawal\b.*\bpolicy\b",
        r"\bprobation\b.*\brules?\b",
        r"\bregulations?\b",
        r"\buniversity\b.*\blaw\b",
        r"\bacademic\b.*\bpolicy\b",
        r"\bwhat happens if\b",
        r"\bwhat is\b.*\bprocedure\b",
        r"\bhow does\b.*\bwork\b",
        r"\bexplain\b.*\bpolicy\b",
    ]

    # Hybrid patterns — decision-making questions
    hybrid_patterns = [
        r"\bcan i\b.*\bregister\b",
        r"\bcan i\b.*\btake\b",
        r"\bcan i\b.*\benroll\b",
        r"\bam i eligible\b",
        r"\bam i allowed\b",
        r"\bwhy am i\b.*\bblocked\b",
        r"\bwhy am i\b.*\bprobation\b",
        r"\bwhy can.t i\b",
        r"\bcan i graduate\b",
        r"\beligible.*graduat",
        r"\binternship\b",
        r"\bcapstone\b",
        r"\bwhat do i need to\b",
        r"\bdo i meet\b.*\brequirements\b",
    ]

    # Check hybrid first (most specific)
    for pattern in hybrid_patterns:
        if re.search(pattern, q):
            return QueryType.HYBRID

    # Then RAG
    for pattern in rag_patterns:
        if re.search(pattern, q):
            return QueryType.RAG_ONLY

    # Then SQL
    for pattern in sql_patterns:
        if re.search(pattern, q):
            return QueryType.SQL_ONLY

    # Default to HYBRID (safest — considers all data sources)
    return QueryType.HYBRID


async def classify_query(question: str) -> dict:
    """
    Classify a user's question using the Ollama LLM.
    Falls back to keyword-based classification if LLM is unavailable.

    Args:
        question: The user's natural language question.

    Returns:
        Dict with 'query_type', 'confidence', and 'reasoning'.
    """
    # Use fast keyword-based classification (skips LLM call to save ~10-30s)
    # The keyword classifier covers all major query patterns reliably.
    # To re-enable LLM classification, uncomment the block below.
    #
    # try:
    #     result = await _llm_classify(question)
    #     if result is not None:
    #         return result
    # except Exception as e:
    #     logger.warning(f"LLM classification failed, using fallback: {e}")

    query_type = _keyword_classify(question)
    return {
        "query_type": query_type,
        "confidence": 0.85,
        "reasoning": f"Classified by keyword matching. Type: {query_type.value}",
        "method": "keyword",
    }


async def _llm_classify(question: str) -> Optional[dict]:
    """
    Use Gemini API to classify the query (acting as a drop-in replacement for Ollama).
    Returns None if classification fails.
    """
    prompt = CLASSIFICATION_PROMPT.format(question=question)

    # --- Ollama Local LLM (Commented Out) ---
    # try:
    #     async with httpx.AsyncClient(timeout=30.0) as client:
    #         response = await client.post(
    #             f"{settings.OLLAMA_URL}/api/generate",
    #             json={
    #                 "model": settings.OLLAMA_MODEL,
    #                 "prompt": prompt,
    #                 "stream": False,
    #                 "options": {
    #                     "temperature": 0.1,   # Low temperature for consistent classification
    #                     "num_predict": 150,    # Short response expected
    #                 },
    #             },
    #         )
    # 
    #     if response.status_code != 200:
    #         logger.warning(f"Ollama returned status {response.status_code}")
    #         return None
    # 
    #     response_text = response.json().get("response", "")
    # ...

    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. Classification will fallback to keywords.")
        return None

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 150
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

        if response.status_code != 200:
            logger.warning(f"Gemini API returned status {response.status_code} during classification")
            return None

        res_json = response.json()
        try:
            response_text = res_json['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            logger.warning(f"Unexpected Gemini classification response: {res_json}")
            return None

        # Parse the JSON response from the LLM
        parsed = _parse_classification_response(response_text)
        if parsed:
            return parsed

        logger.warning(f"Could not parse LLM classification response: {response_text[:200]}")
        return None

    except httpx.TimeoutException:
        logger.warning("Gemini classification timed out")
        return None
    except httpx.ConnectError:
        logger.warning("Could not connect to Gemini API")
        return None


def _parse_classification_response(response_text: str) -> Optional[dict]:
    """
    Parse the LLM's JSON classification response.
    Handles various response formats gracefully.
    """
    # Try to extract JSON from the response
    # The LLM might wrap it in markdown code blocks or add extra text
    json_match = re.search(r'\{[^}]+\}', response_text)
    if not json_match:
        return None

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError:
        return None

    category = data.get("category", "").upper().strip()

    # Map to QueryType enum
    type_map = {
        "SQL_ONLY": QueryType.SQL_ONLY,
        "RAG_ONLY": QueryType.RAG_ONLY,
        "HYBRID": QueryType.HYBRID,
    }

    query_type = type_map.get(category)
    if query_type is None:
        return None

    return {
        "query_type": query_type,
        "confidence": float(data.get("confidence", 0.8)),
        "reasoning": data.get("reasoning", "Classified by LLM"),
        "method": "llm",
    }
