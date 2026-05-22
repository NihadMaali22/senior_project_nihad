# ============================================================
# Qdrant Document Store Configuration
# ============================================================
"""
Initializes and manages the QdrantDocumentStore for university regulations.
Supports both dense and sparse embeddings for hybrid retrieval.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache()
def get_document_store() -> QdrantDocumentStore:
    """
    Create and cache the Qdrant document store singleton.

    Configuration:
    - Uses sparse embeddings for hybrid retrieval (BM25-like via SPLADE)
    - Embedding dimension matches the dense model (384 for MiniLM, 768 for multilingual-e5)
    - Does NOT recreate the index on startup (preserves existing data)
    """
    logger.info(
        f"Initializing QdrantDocumentStore at {settings.QDRANT_URL}, "
        f"collection='{settings.QDRANT_COLLECTION}', "
        f"dim={settings.DENSE_EMBEDDING_DIM}"
    )

    store = QdrantDocumentStore(
        url=settings.QDRANT_URL,
        index=settings.QDRANT_COLLECTION,
        embedding_dim=settings.DENSE_EMBEDDING_DIM,
        use_sparse_embeddings=True,    # Enable sparse vectors for hybrid search
        recreate_index=False,          # Don't wipe data on restart
        return_embedding=False,        # Save memory — don't return embeddings in results
        wait_result_from_api=True,     # Ensure writes are confirmed
    )

    logger.info("QdrantDocumentStore initialized successfully")
    return store


def get_document_count() -> int:
    """Get the total number of documents in the store."""
    try:
        store = get_document_store()
        return store.count_documents()
    except Exception as e:
        logger.error(f"Failed to count documents: {e}")
        return 0
