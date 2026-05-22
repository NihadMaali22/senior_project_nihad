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

from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.rankers import TransformersSimilarityRanker
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

from app.config import get_settings
from app.rag.document_store import get_document_store
from app.rag.embedders import DENSE_MODEL, RERANKER_MODEL

logger = logging.getLogger(__name__)
settings = get_settings()

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
        progress_bar=False,
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

    logger.info(f"Retrieving documents for query: '{query[:80]}...'")

    try:
        documents = await asyncio.to_thread(_sync_retrieve, pipeline, query)

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
