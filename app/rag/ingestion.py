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
import os
from pathlib import Path
from typing import List, Optional

from haystack import Document, Pipeline
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy

from app.config import get_settings
from app.rag.document_store import get_document_store
from app.rag.embedders import DENSE_MODEL, SPARSE_MODEL

logger = logging.getLogger(__name__)
settings = get_settings()


def _read_regulation_files(directory: str) -> List[Document]:
    """
    Read all .txt regulation files from the given directory
    and convert them to Haystack Document objects with metadata.
    """
    documents = []
    reg_dir = Path(directory)

    if not reg_dir.exists():
        logger.warning(f"Regulations directory not found: {directory}")
        return documents

    for filepath in sorted(reg_dir.glob("*.txt")):
        logger.info(f"Reading regulation file: {filepath.name}")

        content = filepath.read_text(encoding="utf-8")

        # Extract metadata from the file content
        title = filepath.stem.replace("_", " ").title()

        # Parse sections from the document
        doc = Document(
            content=content,
            meta={
                "source": filepath.name,
                "title": title,
                "file_path": str(filepath),
                "type": "regulation",
            },
        )
        documents.append(doc)

    logger.info(f"Read {len(documents)} regulation files")
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
        progress_bar=True,
        meta_fields_to_embed=["title"],    # Also embed the title for better retrieval
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
    directory: Optional[str] = None,
    documents: Optional[List[Document]] = None,
) -> dict:
    """
    Run the ingestion pipeline on regulation documents.

    This is an async function. The heavy Haystack pipeline.run() call is
    offloaded to a thread pool via asyncio.to_thread() so it does not block
    the FastAPI event loop during ingestion.

    Args:
        directory: Path to regulation files directory.
                   Defaults to 'data/regulations/'.
        documents: Optional pre-created Document list (for API uploads).

    Returns:
        Dict with ingestion results.
    """
    if documents is None:
        if directory is None:
            # Default to project's data/regulations/ directory
            directory = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data",
                "regulations",
            )
        documents = _read_regulation_files(directory)

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
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    result = ingest_documents()
    print(f"\nIngestion Result: {result}")
