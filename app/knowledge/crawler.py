# ============================================================
# Knowledge Crawler — AAUP Website
# ============================================================
"""
Async web crawler for aaup.edu/ar using crawl4ai.

- Crawls pages defined in targets.py
- Saves clean Markdown text to data/knowledge/
- Skips already-crawled pages unless force=True
- Polite crawling: respects CRAWLER_DELAY_SECONDS between requests

Usage (via pipeline):
    python -m app.knowledge.pipeline

Usage (standalone):
    from app.knowledge.crawler import crawl_all_pages
    await crawl_all_pages(force=False)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

from app.config import get_settings
from app.knowledge.targets import AAUP_TARGETS, CrawlTarget

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from crawl4ai import AsyncWebCrawler
    _CRAWL4AI_AVAILABLE = True
except ImportError:
    _CRAWL4AI_AVAILABLE = False
    logger.warning(
        "crawl4ai not installed. Run: pip install crawl4ai  "
        "Then: crawl4ai-setup"
    )


async def _crawl_single_page(
    crawler: "AsyncWebCrawler",
    target: CrawlTarget,
    output_dir: Path,
) -> Optional[Path]:
    """
    Crawl one page and save its content to disk.

    Returns the saved file path, or None on failure.
    """
    url = f"{settings.AAUP_BASE_URL}{target['path']}"
    out_path = output_dir / f"aaup_{target['slug']}.txt"

    try:
        result = await crawler.arun(url=url)

        if not result.success or not result.markdown:
            logger.warning(f"No content from: {url}")
            return None

        # Prepend the Arabic title so the LLM has page context
        content = f"# {target['title']}\nالمصدر: {url}\n\n{result.markdown}"
        out_path.write_text(content, encoding="utf-8")
        logger.info(f"  Saved {target['slug']}.txt  ({len(result.markdown):,} chars)")
        return out_path

    except Exception as exc:
        logger.error(f"  Failed to crawl {url}: {exc}")
        return None


async def crawl_all_pages(force: bool = False) -> List[Path]:
    """
    Crawl all AAUP target pages and save content to data/knowledge/.

    Args:
        force: If True, re-crawl even pages that already have a saved file.
               If False (default), skip pages that already exist on disk.

    Returns:
        List of file paths that were saved in this run.
    """
    if not _CRAWL4AI_AVAILABLE:
        raise RuntimeError(
            "crawl4ai is not installed. "
            "Install it with: pip install crawl4ai && crawl4ai-setup"
        )

    output_dir = Path(settings.KNOWLEDGE_DATA_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Decide which pages to crawl
    if force:
        targets = AAUP_TARGETS
        logger.info(f"Force-crawling all {len(targets)} pages...")
    else:
        targets = [
            t for t in AAUP_TARGETS
            if not (output_dir / f"aaup_{t['slug']}.txt").exists()
        ]
        if not targets:
            logger.info(
                "All pages already crawled. "
                "Use force=True (or --force flag) to re-crawl."
            )
            return []
        logger.info(f"Crawling {len(targets)} new pages (skipping already-saved)...")

    saved: List[Path] = []

    async with AsyncWebCrawler(verbose=False) as crawler:
        for i, target in enumerate(targets):
            logger.info(f"[{i + 1}/{len(targets)}] {target['path']}")
            path = await _crawl_single_page(crawler, target, output_dir)
            if path:
                saved.append(path)
            # Polite delay between requests
            if i < len(targets) - 1:
                await asyncio.sleep(settings.CRAWLER_DELAY_SECONDS)

    logger.info(f"Crawl complete — {len(saved)}/{len(targets)} pages saved to {output_dir}/")
    return saved
