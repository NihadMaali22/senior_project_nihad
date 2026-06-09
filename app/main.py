# ============================================================
# FastAPI Application — Main Entry Point
# ============================================================
"""
The FastAPI application factory with:
- CORS middleware
- Lifespan handler for startup/shutdown
- Health check endpoint
- Error handlers
- All API routes
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings

settings = get_settings()

# ============================================================
# Logging Configuration
# ============================================================
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================
# Application Lifespan (startup/shutdown)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown.

    Startup:
    - Initialize database tables
    - Log configuration info

    Shutdown:
    - Close database connections
    """
    import torch
    gpu_status = f"cuda:0 — {torch.cuda.get_device_name(0)}" if torch.cuda.is_available() else "CPU only"
    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Debug: {settings.DEBUG}")
    logger.info(f"  Database: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")
    logger.info(f"  Qdrant: {settings.QDRANT_URL}")
    logger.info(f"  Groq: {settings.GROQ_MODEL}")
    logger.info(f"  Ollama: {settings.OLLAMA_MODEL} at {settings.OLLAMA_URL}")
    logger.info(f"  Dense Model: {settings.DENSE_EMBEDDING_MODEL}")
    logger.info(f"  GPU: {gpu_status}")
    logger.info("=" * 60)

    # Startup: Initialize database
    from app.db.database import init_db
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application starting without database — some features may not work")

    # Startup: Create shared httpx client for external APIs (reused across all requests)
    settings_obj = get_settings()
    app.state.http_client = httpx.AsyncClient(
        timeout=float(settings_obj.OLLAMA_TIMEOUT),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
    logger.info("Shared HTTP client created for external API calls")

    yield

    # Shutdown: Close connections
    from app.db.database import close_db
    await close_db()
    await app.state.http_client.aclose()
    logger.info("Application shutdown complete")


# ============================================================
# Create FastAPI Application
# ============================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "An intelligent academic assistant that combines Hybrid RAG, "
        "SQL querying, and policy-based decision-making to answer "
        "complex university academic questions."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================================
# CORS Middleware
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Global Exception Handlers
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to prevent 500 error leakage."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "type": type(exc).__name__,
        },
    )



# ============================================================
# Health Check Endpoint
# ============================================================
@app.get("/health", tags=["System"], summary="Health Check")
async def health_check():
    """
    Health check endpoint for Docker/Kubernetes readiness probes.
    Returns basic system status.
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================
# Include API Routes
# ============================================================
from app.api.router import api_router  # noqa: E402

app.include_router(api_router)

# ============================================================
# Mount Frontend Static Files
# ============================================================
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
