# ============================================================
# Document Management API
# ============================================================
"""
Endpoints for managing university regulation documents
in the Qdrant vector store.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.auth.middleware import get_current_user, require_role
from app.auth.schemas import TokenPayload
from app.db.schemas import DocumentIngestRequest, DocumentIngestResponse
from app.rag.document_store import get_document_count, get_document_store
from app.rag.ingestion import ingest_documents, ingest_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Document Management"])


@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    summary="Ingest Regulation Documents",
    description="Ingest all regulation files from the data/regulations/ directory.",
)
async def ingest_all_documents(
    _: TokenPayload = Depends(require_role("admin")),
):
    """
    Trigger ingestion of all regulation files from the server's
    data/regulations/ directory. Requires admin role.
    """
    try:
        result = await ingest_documents()
        return DocumentIngestResponse(**result)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}",
        )


@router.post(
    "/ingest/text",
    response_model=DocumentIngestResponse,
    summary="Ingest Text Content",
    description="Ingest raw text as a regulation document.",
)
async def ingest_text_document(
    request: DocumentIngestRequest,
    _: TokenPayload = Depends(require_role("admin")),
):
    """
    Ingest a single text document into the vector store.
    Requires admin role.
    """
    if not request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content field is required for text ingestion.",
        )

    try:
        result = await ingest_text(
            title=request.title,
            content=request.content,
            source=request.source,
            metadata=request.metadata,
        )
        return DocumentIngestResponse(**result)
    except Exception as e:
        logger.error(f"Text ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text ingestion failed: {str(e)}",
        )


@router.get(
    "/count",
    summary="Get Document Count",
    description="Get the total number of document chunks in the vector store.",
)
async def document_count(
    _: TokenPayload = Depends(get_current_user),
):
    """Get the number of documents in the Qdrant collection."""
    count = get_document_count()
    return {"total_chunks": count}
