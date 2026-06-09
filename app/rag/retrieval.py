# ============================================================
# Hybrid Retrieval Pipeline — Haystack 2.x
# ============================================================
"""
Hybrid retrieval pipeline that combines:
1. Dense retrieval (SentenceTransformers → QdrantEmbeddingRetriever)
2. Reciprocal Rank Fusion for result merging
3. Cross-encoder reranking for final quality

Pipeline architecture:
    Query → SentenceTransformersTextEmbedder → QdrantEmbeddingRetriever → Ranker → Results

For simplicity and reliability, this uses dense retrieval + reranking.
The QdrantDocumentStore with use_sparse_embeddings=True enables
sparse vector storage, and can be upgraded to full hybrid retrieval
with QdrantHybridRetriever when needed.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
import torch
from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.rankers import TransformersSimilarityRanker
from haystack.utils import ComponentDevice
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

from app.config import get_settings
from app.rag.document_store import get_document_store
from app.rag.embedders import DENSE_MODEL, RERANKER_MODEL, QUERY_PREFIX

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level fallback HTTP client (used when app.state is unavailable)
_fallback_http_client: Optional[httpx.AsyncClient] = None


def _get_http_client() -> httpx.AsyncClient:
    """
    Return the shared httpx.AsyncClient stored on app.state.
    Falls back to a module-level reusable client (tests / CLI).
    """
    try:
        from app.main import app  # noqa: PLC0415
        client = getattr(app.state, "http_client", None)
        if client is not None:
            return client
    except Exception:
        pass
    global _fallback_http_client
    if _fallback_http_client is None or _fallback_http_client.is_closed:
        _fallback_http_client = httpx.AsyncClient(
            timeout=float(settings.OLLAMA_TIMEOUT),
        )
    return _fallback_http_client

# ---- GPU / CPU device selection ----
_DEVICE = ComponentDevice.from_str("cuda:0") if torch.cuda.is_available() else ComponentDevice.from_str("cpu")
logger.info(f"Retrieval pipeline device: {'cuda:0' if torch.cuda.is_available() else 'cpu'}")

# Cache the pipeline after first build
_retrieval_pipeline: Optional[Pipeline] = None


def build_retrieval_pipeline() -> Pipeline:
    """
    Build the Haystack 2.x hybrid retrieval pipeline.

    Pipeline flow:
    1. SentenceTransformersTextEmbedder — embeds the query
    2. QdrantEmbeddingRetriever — retrieves top-k candidates via dense search
    3. TransformersSimilarityRanker — reranks candidates with a cross-encoder

    The reranker is critical: it uses a cross-encoder model that scores
    query-document pairs together, producing much more accurate relevance
    scores than embedding similarity alone.
    """
    document_store = get_document_store()

    # 1. Dense query embedder
    text_embedder = SentenceTransformersTextEmbedder(
        model=DENSE_MODEL,
        prefix=QUERY_PREFIX,
        progress_bar=False,
        device=_DEVICE,
    )

    # 2. Dense retriever from Qdrant
    retriever = QdrantEmbeddingRetriever(
        document_store=document_store,
        top_k=settings.RAG_TOP_K,         # Retrieve 10 candidates
    )

    # 3. Cross-encoder reranker for precision
    ranker = TransformersSimilarityRanker(
        model=RERANKER_MODEL,
        top_k=settings.RAG_RERANK_TOP_K,  # Keep top 5 after reranking
        device=_DEVICE,
    )

    # Build pipeline
    pipeline = Pipeline()
    pipeline.add_component("text_embedder", text_embedder)
    pipeline.add_component("retriever", retriever)
    pipeline.add_component("ranker", ranker)

    # Connect: embedder → retriever → ranker
    pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
    pipeline.connect("retriever.documents", "ranker.documents")

    logger.info("Retrieval pipeline built successfully")
    return pipeline


def get_retrieval_pipeline() -> Pipeline:
    """Get or create the cached retrieval pipeline singleton."""
    global _retrieval_pipeline
    if _retrieval_pipeline is None:
        _retrieval_pipeline = build_retrieval_pipeline()
    return _retrieval_pipeline


async def translate_query_if_arabic(query: str) -> str:
    """Translate the query to English if it contains Arabic characters."""
    if not any('\u0600' <= char <= '\u06FF' for char in query):
        return query

    import re

    prompt = (
        f"Translate the following Arabic academic question from a student into clear English "
        f"suitable for search/retrieval of academic regulations. Return ONLY the English translation, "
        f"nothing else. Do not include quotes.\n\n"
        f"Question: {query}"
    )

    http_client = _get_http_client()

    # 1. Try Groq if configured
    if settings.GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_completion_tokens": 100
            }
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            response = await http_client.post(url, json=payload, headers=headers, timeout=5.0)
            if response.status_code == 200:
                res_json = response.json()
                translation = res_json['choices'][0]['message']['content'].strip()
                # Strip think blocks if any
                translation = re.sub(r"<think>.*?</think>", "", translation, flags=re.DOTALL).strip()
                translation = translation.strip('"\'')
                logger.info(f"Translated query for retrieval (via Groq): '{query}' -> '{translation}'")
                return translation
            else:
                logger.warning(f"Groq translation API returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to translate query via Groq: {e}")

    return query


def _sync_retrieve(pipeline: Pipeline, query: str) -> List[Document]:
    """Run the retrieval pipeline synchronously (called from thread pool)."""
    result = pipeline.run({
        "text_embedder": {"text": query},
        "ranker": {"query": query},
    })
    return result.get("ranker", {}).get("documents", [])


async def retrieve_documents(
    query: str,
    top_k: Optional[int] = None,
) -> List[Document]:
    """
    Retrieve and rerank relevant regulation documents for a query.
    Runs the Haystack pipeline in a thread pool to avoid blocking the event loop.

    Args:
        query: The user's question or search query.
        top_k: Override the default number of results to return.

    Returns:
        List of Haystack Document objects, ranked by relevance.
    """
    pipeline = get_retrieval_pipeline()

    # For native multilingual RAG, search directly in the query's original language.
    search_query = query

    logger.info(f"Retrieving documents for query: '{search_query[:80]}...' (original: '{query[:80]}')")

    try:
        documents = await asyncio.to_thread(_sync_retrieve, pipeline, search_query)

        # Apply custom top_k if specified
        if top_k and len(documents) > top_k:
            documents = documents[:top_k]

        logger.info(f"Retrieved {len(documents)} documents after reranking")
        return documents

    except Exception as e:
        logger.error(f"Retrieval failed: {e}", exc_info=True)
        return []


async def retrieve_with_scores(
    query: str,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve documents with their relevance scores and metadata.

    Returns:
        List of dicts with 'content', 'score', 'meta' for each document.
    """
    documents = await retrieve_documents(query, top_k)

    results = []
    for doc in documents:
        results.append({
            "content": doc.content,
            "score": doc.score,
            "meta": doc.meta or {},
            "id": doc.id,
        })

    return results


def format_context_for_llm(documents: List[Document]) -> str:
    """
    Format retrieved documents into a context string for the LLM prompt.

    Each document chunk is formatted with its source metadata
    and section information for proper citation.
    """
    if not documents:
        return "No relevant regulations found."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        source = doc.meta.get("title", "Unknown") if doc.meta else "Unknown"
        file_source = doc.meta.get("source", "") if doc.meta else ""

        context_parts.append(
            f"--- Regulation Source [{i}]: {source} (file: {file_source}) ---\n"
            f"{doc.content}\n"
        )

    return "\n".join(context_parts)
