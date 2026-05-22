# ============================================================
# Embedding Model Configuration
# ============================================================
"""
Centralized configuration for embedding models used across
ingestion and retrieval pipelines.
"""

from __future__ import annotations

from app.config import get_settings

settings = get_settings()

# ============================================================
# Model Constants
# ============================================================

# Dense embedding model — used for semantic similarity search
DENSE_MODEL = settings.DENSE_EMBEDDING_MODEL        # "sentence-transformers/all-MiniLM-L6-v2"
DENSE_DIM = settings.DENSE_EMBEDDING_DIM             # 384

# Sparse embedding model — used for keyword-based search (SPLADE)
SPARSE_MODEL = settings.SPARSE_EMBEDDING_MODEL       # "prithivida/Splade_PP_en_v1"

# Reranker model — cross-encoder for reranking retrieved documents
RERANKER_MODEL = settings.RERANKER_MODEL             # "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ============================================================
# Embedding Prefixes
# ============================================================
# Some models (e.g., E5 family) require prefixes for queries vs documents
# For MiniLM, no prefix is needed; for E5, use "query: " and "passage: "
QUERY_PREFIX = ""
DOCUMENT_PREFIX = ""
