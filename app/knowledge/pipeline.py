# ============================================================
# Knowledge Pipeline — Crawl → Save → Ingest
# ============================================================
"""
Standalone pipeline that builds the university knowledge base:

  Step 1 — Crawl:   Visits AAUP pages, saves clean text to data/knowledge/
  Step 2 — Ingest:  Reads saved text files, embeds them, writes to Qdrant

This pipeline is NEVER called during app startup.
Run it manually on demand (once per semester, or after major website updates).

Usage:
    python -m app.knowledge.pipeline            # only crawl new pages + ingest
    python -m app.knowledge.pipeline --force    # re-crawl all pages + ingest
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from app.config import get_settings
from app.knowledge.crawler import crawl_all_pages
from app.rag.ingestion import ingest_documents

logger = logging.getLogger(__name__)
settings = get_settings()


async def run_knowledge_pipeline(force_recrawl: bool = False) -> dict:
    """
    Run the full knowledge pipeline.

    Args:
        force_recrawl: If True, re-crawl all pages even if already saved.

    Returns:
        Summary dict with pages_crawled and ingestion stats.
    """
    logger.info("=" * 60)
    logger.info("Knowledge Pipeline Starting")
    logger.info("=" * 60)

    # ── Step 1: Crawl ─────────────────────────────────────────
    logger.info("Step 1/2 — Crawling AAUP website...")
    saved_files = await crawl_all_pages(force=force_recrawl)
    logger.info(f"  → {len(saved_files)} pages crawled")

    # ── Step 2: Ingest ────────────────────────────────────────
    knowledge_dir = str(Path(settings.KNOWLEDGE_DATA_DIR))
    logger.info(f"Step 2/2 — Ingesting knowledge files from {knowledge_dir}...")

    ingest_result = await ingest_documents(directories=[knowledge_dir])
    logger.info(f"  → {ingest_result.get('chunks_created', 0)} chunks written to Qdrant")

    logger.info("=" * 60)
    logger.info("Knowledge Pipeline Complete")
    logger.info("=" * 60)

    return {
        "pages_crawled": len(saved_files),
        "documents_ingested": ingest_result.get("documents_ingested", 0),
        "chunks_created": ingest_result.get("chunks_created", 0),
    }


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Build the AAUP knowledge base (crawl + ingest)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-crawl all pages even if already saved on disk",
    )
    args = parser.parse_args()

    result = asyncio.run(run_knowledge_pipeline(force_recrawl=args.force))
    print(f"\nResult: {result}")
