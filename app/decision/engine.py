# ============================================================
# Decision Engine — Core Orchestrator
# ============================================================
"""
The Decision Engine is the most critical component of the system.
It orchestrates the full decision-making flow:

1. Receive classified query from the Router
2. Execute relevant SQL queries (student data)
3. Retrieve relevant regulations (RAG)
4. Run deterministic policy checks (rules)
5. Compose a structured prompt with all context
6. Call the local LLM (Ollama) for reasoning
7. Parse the response into a structured decision
8. Extract citations

This module handles all three query types:
- SQL_ONLY: SQL data → LLM formatting
- RAG_ONLY: RAG retrieval → LLM answer
- HYBRID: SQL + RAG + Rules → LLM decision
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.citation.generator import extract_citations
from app.config import get_settings
from app.db.schemas import AskResponse, Citation, DecisionOutcome, QueryType
from app.decision.prompts import DECISION_PROMPT, RAG_RESPONSE_PROMPT, SQL_RESPONSE_PROMPT
from app.decision.rules import format_checks_for_prompt, run_all_checks
from app.memory.conversation import get_conversation_context, save_message
from app.rag.retrieval import format_context_for_llm, retrieve_documents
from app.sql_agent.agent import execute_sql_query, extract_course_code

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level fallback client (used when app.state is unavailable, e.g. in tests)
_fallback_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    """
    Return the shared httpx.AsyncClient stored on app.state.
    Falls back to a lazily-created module-level client when the
    FastAPI application context is not available (unit tests, CLI).
    """
    try:
        # Import here to avoid circular imports at module load time
        from app.main import app  # noqa: PLC0415
        client = getattr(app.state, "http_client", None)
        if client is not None:
            return client
    except Exception:
        pass

    # Fallback: create a reusable module-level client
    global _fallback_http_client
    if _fallback_http_client is None or _fallback_http_client.is_closed:
        _fallback_http_client = httpx.AsyncClient(
            timeout=float(settings.OLLAMA_TIMEOUT),
        )
    return _fallback_http_client



async def process_query(
    question: str,
    query_type: QueryType,
    student_id: Optional[int],
    session: AsyncSession,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> AskResponse:
    """
    Main entry point for the Decision Engine.
    Routes to the appropriate handler based on query type.

    Args:
        question: The user's natural language question.
        query_type: Classified query type (SQL_ONLY, RAG_ONLY, HYBRID).
        student_id: The student's database ID (from JWT or request).
        session: Async database session.
        session_id: Conversation session ID for memory.
        user_id: Authenticated user ID.

    Returns:
        AskResponse with answer, decision, reasoning, citations.
    """
    logger.info(
        f"Decision Engine processing: type={query_type.value}, "
        f"student_id={student_id}, question='{question[:60]}...'"
    )

    # Save the user's question to conversation history
    if session_id:
        await save_message(session, session_id, "user", question, user_id)

    # Get conversation history for context
    conversation_history = ""
    if session_id:
        conversation_history = await get_conversation_context(session, session_id)

    try:
        if query_type == QueryType.SQL_ONLY:
            response = await _handle_sql_query(
                question, student_id, session, conversation_history
            )
        elif query_type == QueryType.RAG_ONLY:
            response = await _handle_rag_query(
                question, conversation_history
            )
        elif query_type == QueryType.HYBRID:
            response = await _handle_hybrid_query(
                question, student_id, session, conversation_history
            )
        else:
            response = AskResponse(
                answer="I'm not sure how to handle this question. Could you rephrase it?",
                query_type=query_type,
                session_id=session_id,
            )

        # Save the assistant's response to conversation history
        if session_id:
            await save_message(
                session, session_id, "assistant", response.answer, user_id,
                metadata={"query_type": query_type.value, "decision": response.decision.value if response.decision else None},
            )

        response.session_id = session_id
        return response

    except Exception as e:
        logger.error(f"Decision Engine error: {e}", exc_info=True)
        return AskResponse(
            answer=f"I encountered an error while processing your question. Please try again. Error: {str(e)}",
            query_type=query_type,
            session_id=session_id,
        )


# ============================================================
# SQL-Only Handler
# ============================================================
async def _handle_sql_query(
    question: str,
    student_id: Optional[int],
    session: AsyncSession,
    conversation_history: str,
) -> AskResponse:
    """Handle pure SQL data lookup questions."""
    # Execute SQL query
    sql_result = await execute_sql_query(session, question, student_id)

    student_data_str = json.dumps(sql_result.get("data", {}), indent=2, default=str)

    # Generate natural language response via LLM
    prompt = SQL_RESPONSE_PROMPT.format(
        student_data=student_data_str,
        question=question,
        conversation_history=conversation_history or "No previous conversation.",
    )

    llm_response = await _call_ollama(prompt)

    return AskResponse(
        answer=llm_response,
        decision=DecisionOutcome.INFO,
        reasoning=[f"Query type: SQL data lookup ({sql_result.get('query_type', 'unknown')})"],
        student_data=sql_result.get("data"),
        citations=[],
        confidence=0.9,
        query_type=QueryType.SQL_ONLY,
    )


# ============================================================
# RAG-Only Handler
# ============================================================
async def _handle_rag_query(
    question: str,
    conversation_history: str,
) -> AskResponse:
    """Handle pure regulation/policy lookup questions."""
    # Retrieve relevant documents
    documents = await retrieve_documents(question)

    if not documents:
        return AskResponse(
            answer="I couldn't find relevant regulations for your question. Please rephrase or contact the academic affairs office.",
            query_type=QueryType.RAG_ONLY,
            decision=DecisionOutcome.INFO,
        )

    # Format context for LLM
    regulations_context = format_context_for_llm(documents)

    # Generate response
    prompt = RAG_RESPONSE_PROMPT.format(
        regulations=regulations_context,
        question=question,
        conversation_history=conversation_history or "No previous conversation.",
    )

    llm_response = await _call_ollama(prompt)

    # Extract citations from documents
    citations = extract_citations(documents)

    return AskResponse(
        answer=llm_response,
        decision=DecisionOutcome.INFO,
        reasoning=["Query type: Regulation/policy lookup via RAG"],
        citations=citations,
        confidence=_calculate_confidence(documents),
        query_type=QueryType.RAG_ONLY,
    )


# ============================================================
# Hybrid Handler (SQL + RAG + Decision)
# ============================================================
async def _handle_hybrid_query(
    question: str,
    student_id: Optional[int],
    session: AsyncSession,
    conversation_history: str,
) -> AskResponse:
    """
    Handle hybrid decision-making questions that require both
    student data and regulation retrieval.

    This is the most complex flow:
    1. Get student data via SQL
    2. Get relevant regulations via RAG
    3. Run deterministic policy checks
    4. Compose full context prompt
    5. LLM generates reasoned decision
    6. Parse response into structured output
    """
    # Step 1 & 2: Run SQL queries and RAG retrieval IN PARALLEL
    async def _fetch_student_data():
        """Fetch all student data from SQL."""
        _student_data = {}
        _prereq_data = {}
        _eligibility_data = {}
        _grad_data = {}

        if not student_id:
            return _student_data, _prereq_data, _eligibility_data, _grad_data

        from app.sql_agent import queries
        _student_data = await queries.get_student_info(session, student_id) or {}

        # Get completed courses
        completed = await queries.get_completed_courses(session, student_id)
        _student_data["completed_courses"] = completed
        _student_data["completed_course_codes"] = [c["course_code"] for c in completed]

        # Check if question involves a specific course
        course_code = extract_course_code(question)
        if course_code:
            course_info = await queries.get_course_info(session, course_code)
            _prereq_data = await queries.check_prerequisites_met(session, student_id, course_code)
            _eligibility_data = await queries.check_course_eligibility(session, student_id, course_code)
            _student_data["target_course"] = course_info
            _student_data["prerequisite_check"] = _prereq_data
            _student_data["eligibility_check"] = _eligibility_data

        # Check for graduation-related questions
        q_lower = question.lower()
        if any(kw in q_lower for kw in ["graduat", "degree", "requirements", "hours"]):
            _grad_data = await queries.get_graduation_requirements(session, student_id) or {}
            _student_data["graduation_progress"] = _grad_data

        # Get warnings
        warnings = await queries.get_student_warnings(session, student_id)
        _student_data["active_warnings"] = warnings

        return _student_data, _prereq_data, _eligibility_data, _grad_data

    # Run SQL and RAG in parallel using asyncio.gather
    (student_data, prereq_data, eligibility_data, grad_data), documents = await asyncio.gather(
        _fetch_student_data(),
        retrieve_documents(question),
    )

    regulations_context = format_context_for_llm(documents)

    # Step 3: Run deterministic policy checks
    course_data = student_data.get("target_course", {})
    rule_checks = run_all_checks(
        student_data=student_data,
        prereq_data=prereq_data if prereq_data else None,
        grad_data=grad_data if grad_data else None,
        course_data=course_data if course_data else None,
    )
    rule_checks_str = format_checks_for_prompt(rule_checks)

    # Step 4: Compose the full decision prompt
    student_data_str = json.dumps(
        {k: v for k, v in student_data.items() if k != "completed_courses"},
        indent=2,
        default=str,
    )
    # Add a summary of completed courses instead of full list
    completed_summary = ", ".join(student_data.get("completed_course_codes", []))
    student_data_str += f"\n\nCompleted Courses: {completed_summary}"

    prompt = DECISION_PROMPT.format(
        student_data=student_data_str,
        regulations=regulations_context,
        rule_checks=rule_checks_str,
        question=question,
        conversation_history=conversation_history or "No previous conversation.",
    )

    # Step 5: Call LLM
    llm_response = await _call_ollama(prompt)

    # Step 6: Parse the structured response
    parsed = _parse_decision_response(llm_response)

    # Step 7: Extract citations
    citations = extract_citations(documents)

    # Build the reasoning list from rule checks + LLM reasoning
    reasoning = []
    for check in rule_checks:
        status = "✅" if check["passed"] else "❌"
        reasoning.append(f"{status} {check['detail']}")
    reasoning.extend(parsed.get("reasoning", []))

    return AskResponse(
        answer=parsed.get("answer", llm_response),
        decision=parsed.get("decision", DecisionOutcome.INFO),
        reasoning=reasoning,
        student_data={k: v for k, v in student_data.items()
                      if k in ["id", "student_number", "full_name", "gpa", "total_credits",
                               "status", "academic_standing", "department",
                               "eligibility_check", "active_warnings"]},
        citations=citations,
        confidence=_calculate_confidence(documents, rule_checks),
        query_type=QueryType.HYBRID,
    )


# ============================================================
# LLM Communication (Ollama)
# ============================================================
async def _call_ollama(prompt: str) -> str:
    """
    Send a prompt to the Ollama local LLM and return the full response.
    Uses the shared httpx.AsyncClient from app.state for connection reuse.
    Falls back to a basic response if Ollama is unavailable.
    """
    try:
        client = _get_http_client()
        response = await client.post(
            "/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 512,
                },
            },
        )

        if response.status_code == 200:
            return response.json().get("response", "No response generated.")
        else:
            logger.error(f"Ollama returned status {response.status_code}: {response.text[:200]}")
            return _fallback_response(prompt)

    except httpx.TimeoutException:
        logger.error("Ollama request timed out")
        return _fallback_response(prompt)
    except httpx.ConnectError:
        logger.error("Could not connect to Ollama. Is it running?")
        return _fallback_response(prompt)
    except Exception as e:
        logger.error(f"Ollama error: {e}", exc_info=True)
        return _fallback_response(prompt)



async def _call_ollama_stream(prompt: str):
    """
    Stream tokens from Ollama as they are generated.
    Uses the shared httpx.AsyncClient from app.state for connection reuse.
    Yields each token string as it arrives.
    Falls back to yielding the full fallback response if Ollama is unavailable.
    """
    try:
        client = _get_http_client()
        async with client.stream(
            "POST",
            "/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 512,
                },
            },
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Ollama stream error: {response.status_code} - {error_text[:200]}")
                yield _fallback_response(prompt)
                return

            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

    except httpx.TimeoutException:
        logger.error("Ollama stream timed out")
        yield _fallback_response(prompt)
    except httpx.ConnectError:
        logger.error("Could not connect to Ollama for streaming. Is it running?")
        yield _fallback_response(prompt)
    except Exception as e:
        logger.error(f"Ollama stream error: {e}", exc_info=True)
        yield _fallback_response(prompt)



def _fallback_response(prompt: str) -> str:
    """
    Generate a basic response when the LLM is unavailable.
    Uses the deterministic rule checks embedded in the prompt.
    """
    # Try to extract the rule checks from the prompt
    checks_match = re.search(
        r"=== DETERMINISTIC CHECKS.*?===\n(.*?)(?=\n===|\Z)",
        prompt,
        re.DOTALL,
    )

    if checks_match:
        checks = checks_match.group(1).strip()
        return (
            "⚠️ The LLM is currently unavailable. Here are the automated policy check results:\n\n"
            f"{checks}\n\n"
            "Please consult the academic affairs office for a complete evaluation."
        )

    return (
        "⚠️ The AI assistant is temporarily unavailable. "
        "Please try again later or contact the academic affairs office."
    )


# ============================================================
# Response Parsing
# ============================================================
def _parse_decision_response(response: str) -> Dict[str, Any]:
    """
    Parse the LLM's structured decision response.

    Expected format:
    DECISION: [APPROVED/DENIED/CONDITIONAL/INFO]
    REASONING: [numbered list]
    ANSWER: [full answer]
    CITATIONS: [citation list]
    """
    result = {
        "decision": DecisionOutcome.INFO,
        "reasoning": [],
        "answer": response,
    }

    # Extract DECISION
    decision_match = re.search(
        r"DECISION:\s*(APPROVED|DENIED|CONDITIONAL|INFO)",
        response,
        re.IGNORECASE,
    )
    if decision_match:
        decision_str = decision_match.group(1).upper()
        try:
            result["decision"] = DecisionOutcome(decision_str)
        except ValueError:
            result["decision"] = DecisionOutcome.INFO

    # Extract REASONING
    reasoning_match = re.search(
        r"REASONING:\s*\n(.*?)(?=\nANSWER:|\nCITATIONS:|\Z)",
        response,
        re.DOTALL | re.IGNORECASE,
    )
    if reasoning_match:
        reasoning_text = reasoning_match.group(1).strip()
        # Parse numbered list items
        lines = reasoning_text.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("---"):
                # Remove leading numbers like "1." or "- "
                cleaned = re.sub(r"^\d+[\.\)]\s*", "", line)
                cleaned = re.sub(r"^[-•]\s*", "", cleaned)
                if cleaned:
                    result["reasoning"].append(cleaned)

    # Extract ANSWER
    answer_match = re.search(
        r"ANSWER:\s*\n(.*?)(?=\nCITATIONS:|\Z)",
        response,
        re.DOTALL | re.IGNORECASE,
    )
    if answer_match:
        result["answer"] = answer_match.group(1).strip()

    return result


def _calculate_confidence(
    documents: Optional[List] = None,
    rule_checks: Optional[List[Dict]] = None,
) -> float:
    """
    Calculate a confidence score based on:
    - Document retrieval scores
    - Number of documents found
    - Rule check results
    """
    confidence = 0.5  # Base confidence

    if documents:
        # Higher confidence with more relevant documents
        avg_score = sum(d.score for d in documents if d.score) / max(len(documents), 1)
        confidence += min(avg_score * 0.3, 0.3)

    if rule_checks:
        # Higher confidence when more checks pass
        total = len(rule_checks)
        passed = sum(1 for c in rule_checks if c.get("passed", False))
        confidence += (passed / max(total, 1)) * 0.2

    return round(min(confidence, 1.0), 2)


# ============================================================
# Streaming Query Processing (SSE)
# ============================================================
async def _build_prompt_for_query(
    question: str,
    query_type: QueryType,
    student_id: Optional[int],
    session: AsyncSession,
    conversation_history: str,
) -> tuple:
    """
    Build the LLM prompt and collect metadata for a query.
    Returns (prompt, documents, rule_checks, student_data) tuple.
    """
    documents = []
    rule_checks = []
    student_data = {}

    if query_type == QueryType.SQL_ONLY:
        sql_result = await execute_sql_query(session, question, student_id)
        student_data_str = json.dumps(sql_result.get("data", {}), indent=2, default=str)
        prompt = SQL_RESPONSE_PROMPT.format(
            student_data=student_data_str,
            question=question,
            conversation_history=conversation_history or "No previous conversation.",
        )
        student_data = sql_result.get("data", {})

    elif query_type == QueryType.RAG_ONLY:
        documents = await retrieve_documents(question)
        regulations_context = format_context_for_llm(documents)
        prompt = RAG_RESPONSE_PROMPT.format(
            regulations=regulations_context,
            question=question,
            conversation_history=conversation_history or "No previous conversation.",
        )

    else:  # HYBRID
        async def _fetch_student_data_stream():
            _sd = {}
            _prereq = {}
            _elig = {}
            _grad = {}
            if not student_id:
                return _sd, _prereq, _elig, _grad

            from app.sql_agent import queries as q
            _sd = await q.get_student_info(session, student_id) or {}
            completed = await q.get_completed_courses(session, student_id)
            _sd["completed_courses"] = completed
            _sd["completed_course_codes"] = [c["course_code"] for c in completed]

            course_code = extract_course_code(question)
            if course_code:
                course_info = await q.get_course_info(session, course_code)
                _prereq = await q.check_prerequisites_met(session, student_id, course_code)
                _elig = await q.check_course_eligibility(session, student_id, course_code)
                _sd["target_course"] = course_info
                _sd["prerequisite_check"] = _prereq
                _sd["eligibility_check"] = _elig

            q_lower = question.lower()
            if any(kw in q_lower for kw in ["graduat", "degree", "requirements", "hours"]):
                _grad = await q.get_graduation_requirements(session, student_id) or {}
                _sd["graduation_progress"] = _grad

            warnings = await q.get_student_warnings(session, student_id)
            _sd["active_warnings"] = warnings
            return _sd, _prereq, _elig, _grad

        (student_data_raw, prereq_data, _, grad_data), documents = await asyncio.gather(
            _fetch_student_data_stream(),
            retrieve_documents(question),
        )
        student_data = student_data_raw
        regulations_context = format_context_for_llm(documents)

        from app.decision.rules import format_checks_for_prompt, run_all_checks
        course_data = student_data.get("target_course", {})
        rule_checks = run_all_checks(
            student_data=student_data,
            prereq_data=prereq_data if prereq_data else None,
            grad_data=grad_data if grad_data else None,
            course_data=course_data if course_data else None,
        )
        rule_checks_str = format_checks_for_prompt(rule_checks)

        student_data_str = json.dumps(
            {k: v for k, v in student_data.items() if k != "completed_courses"},
            indent=2, default=str,
        )
        completed_summary = ", ".join(student_data.get("completed_course_codes", []))
        student_data_str += f"\n\nCompleted Courses: {completed_summary}"

        prompt = DECISION_PROMPT.format(
            student_data=student_data_str,
            regulations=regulations_context,
            rule_checks=rule_checks_str,
            question=question,
            conversation_history=conversation_history or "No previous conversation.",
        )

    return prompt, documents, rule_checks, student_data


async def process_query_stream(
    question: str,
    query_type: QueryType,
    student_id: Optional[int],
    session: AsyncSession,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
):
    """
    Stream the LLM response as Server-Sent Events (SSE).

    Yields SSE-formatted strings:
    - event: token  → individual text tokens as they arrive
    - event: metadata → final JSON with citations, decision, reasoning
    - event: done → signals completion
    """
    logger.info(
        f"[STREAM] Processing: type={query_type.value}, "
        f"student_id={student_id}, question='{question[:60]}...'"
    )

    # Save user message
    if session_id:
        await save_message(session, session_id, "user", question, user_id)

    # Get conversation history
    conversation_history = ""
    if session_id:
        conversation_history = await get_conversation_context(session, session_id)

    try:
        # Build prompt and collect metadata (SQL + RAG run in parallel for HYBRID)
        prompt, documents, rule_checks, student_data = await _build_prompt_for_query(
            question, query_type, student_id, session, conversation_history
        )

        # Stream LLM tokens
        full_response = ""
        async for token in _call_ollama_stream(prompt):
            full_response += token
            # SSE format: each event is "event: type\ndata: content\n\n"
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        # Build metadata
        citations = extract_citations(documents) if documents else []
        reasoning = []

        if query_type == QueryType.HYBRID:
            parsed = _parse_decision_response(full_response)
            for check in rule_checks:
                status_icon = "✅" if check["passed"] else "❌"
                reasoning.append(f"{status_icon} {check['detail']}")
            reasoning.extend(parsed.get("reasoning", []))
            decision = parsed.get("decision", DecisionOutcome.INFO)
        else:
            decision = DecisionOutcome.INFO

        # Send metadata as final event
        metadata = {
            "decision": decision.value if decision else None,
            "reasoning": reasoning,
            "citations": [c.model_dump() for c in citations] if citations else [],
            "confidence": _calculate_confidence(documents, rule_checks) if documents else 0.9,
            "query_type": query_type.value,
            "session_id": session_id,
            "answer": full_response,
        }
        yield f"event: metadata\ndata: {json.dumps(metadata, default=str)}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"

        # Save assistant response to conversation history
        if session_id:
            await save_message(
                session, session_id, "assistant", full_response, user_id,
                metadata={"query_type": query_type.value, "decision": decision.value if decision else None},
            )

    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        error_msg = f"I encountered an error while processing your question. Error: {str(e)}"
        yield f"event: token\ndata: {json.dumps({'token': error_msg})}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'error'})}\n\n"

