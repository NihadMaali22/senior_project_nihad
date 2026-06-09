# ============================================================
# Document Ingestion Pipeline — Haystack 2.x
# ============================================================
"""
Ingestion pipeline that processes university regulation documents:
1. Reads text files from the data/regulations/ directory
2. Splits documents into sentence-based chunks
3. Generates dense embeddings (SentenceTransformers)
4. Generates sparse embeddings (FastEmbed SPLADE)
5. Writes enriched documents to QdrantDocumentStore

Pipeline architecture:
    TextFiles → DocumentSplitter → [DenseEmbedder, SparseEmbedder] → DocumentWriter

Usage:
    python -m app.rag.ingestion
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import torch
from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import ComponentDevice

from app.config import get_settings
from app.rag.document_store import get_document_store
from app.rag.embedders import DENSE_MODEL, SPARSE_MODEL, DOCUMENT_PREFIX

logger = logging.getLogger(__name__)
settings = get_settings()

# ---- GPU / CPU device selection ----
_DEVICE = ComponentDevice.from_str("cuda:0") if torch.cuda.is_available() else ComponentDevice.from_str("cpu")
logger.info(f"Ingestion pipeline device: {'cuda:0' if torch.cuda.is_available() else 'cpu'}")


def _read_text_files(directory: str) -> List[Document]:
    """
    Read all .txt files from a directory and convert them to
    Haystack Document objects with metadata.

    The document type is inferred from the directory name:
      - directories containing 'knowledge' → type='knowledge'
      - all others                         → type='regulation'
    """
    documents = []
    source_dir = Path(directory)

    if not source_dir.exists():
        logger.debug(f"Directory not found (skipping): {directory}")
        return documents

    # Infer document type from directory name
    doc_type = "knowledge" if "knowledge" in source_dir.name else "regulation"

    for filepath in sorted(source_dir.glob("*.txt")):
        logger.info(f"  Reading [{doc_type}] {filepath.name}")
        content = filepath.read_text(encoding="utf-8")
        title = filepath.stem.replace("_", " ").title()

        doc = Document(
            content=content,
            meta={
                "source": filepath.name,
                "title": title,
                "file_path": str(filepath),
                "type": doc_type,
            },
        )
        documents.append(doc)

    logger.info(f"  Read {len(documents)} files from {source_dir}")
    return documents


def build_ingestion_pipeline() -> Pipeline:
    """
    Build the Haystack 2.x ingestion pipeline.

    Pipeline flow:
    1. DocumentCleaner — removes extra whitespace and normalizes text
    2. DocumentSplitter — splits into sentence-based chunks
    3. SentenceTransformersDocumentEmbedder — generates dense embeddings
    4. DocumentWriter — writes to QdrantDocumentStore

    Note: Sparse embeddings are handled natively by Qdrant's document store
    when use_sparse_embeddings=True is set. The QdrantDocumentStore
    generates sparse embeddings internally using FastEmbed during write.
    """
    document_store = get_document_store()

    # Component initialization
    cleaner = DocumentCleaner(
        remove_empty_lines=True,
        remove_extra_whitespaces=True,
    )

    splitter = DocumentSplitter(
        split_by=settings.RAG_SPLIT_BY,           # "sentence"
        split_length=settings.RAG_SPLIT_LENGTH,     # 5 sentences per chunk
        split_overlap=settings.RAG_SPLIT_OVERLAP,   # 1 sentence overlap
    )

    dense_embedder = SentenceTransformersDocumentEmbedder(
        model=DENSE_MODEL,
        prefix=DOCUMENT_PREFIX,
        progress_bar=True,
        meta_fields_to_embed=["title"],    # Also embed the title for better retrieval
        device=_DEVICE,
    )

    writer = DocumentWriter(
        document_store=document_store,
        policy=DuplicatePolicy.OVERWRITE,
    )

    # Build the pipeline
    pipeline = Pipeline()
    pipeline.add_component("cleaner", cleaner)
    pipeline.add_component("splitter", splitter)
    pipeline.add_component("dense_embedder", dense_embedder)
    pipeline.add_component("writer", writer)

    # Connect components
    pipeline.connect("cleaner", "splitter")
    pipeline.connect("splitter", "dense_embedder")
    pipeline.connect("dense_embedder", "writer")

    logger.info("Ingestion pipeline built successfully")
    return pipeline


async def ingest_documents(
    directories: Optional[List[str]] = None,
    documents: Optional[List[Document]] = None,
) -> dict:
    """
    Run the ingestion pipeline on text documents from one or more directories.

    This is an async function. The heavy Haystack pipeline.run() call is
    offloaded to a thread pool via asyncio.to_thread() so it does not block
    the FastAPI event loop during ingestion.

    Args:
        directories: List of directory paths to read .txt files from.
                     Defaults to both 'data/regulations/' and 'data/knowledge/'.
        documents:   Optional pre-created Document list (bypasses directory scan,
                     used for API-uploaded files).

    Returns:
        Dict with ingestion results.
    """
    if documents is None:
        if directories is None:
            directories = [
                settings.REGULATIONS_DATA_DIR,
                settings.KNOWLEDGE_DATA_DIR,
            ]
        documents = []
        for directory in directories:
            documents.extend(_read_text_files(directory))

    if not documents:
        return {
            "message": "No documents to ingest",
            "documents_ingested": 0,
            "chunks_created": 0,
        }

    logger.info(f"Starting ingestion of {len(documents)} documents...")

    pipeline = build_ingestion_pipeline()

    # Run the CPU/IO-heavy pipeline in a thread pool to avoid blocking the event loop
    def _run_pipeline() -> dict:
        return pipeline.run({"cleaner": {"documents": documents}})

    result = await asyncio.to_thread(_run_pipeline)

    # Count written documents
    written = result.get("writer", {}).get("documents_written", 0)

    logger.info(f"Ingestion complete: {written} chunks written to Qdrant")

    return {
        "message": "Ingestion completed successfully",
        "documents_ingested": len(documents),
        "chunks_created": written,
    }



async def ingest_text(
    title: str,
    content: str,
    source: str = "manual",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Ingest a single text document into the vector store.

    This is an async function that delegates to the async ingest_documents().

    Args:
        title: Document title.
        content: Raw text content.
        source: Source identifier.
        metadata: Additional metadata.

    Returns:
        Dict with ingestion results.
    """
    meta = {
        "title": title,
        "source": source,
        "type": "regulation",
    }
    if metadata:
        meta.update(metadata)

    doc = Document(content=content, meta=meta)
    return await ingest_documents(documents=[doc])



# ============================================================
# CLI entry point
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    result = asyncio.run(ingest_documents())
    print(f"\nIngestion Result: {result}")
