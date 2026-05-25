# ============================================================
# Knowledge Targets — AAUP Pages to Crawl
# ============================================================
"""
Defines which pages to crawl from the AAUP website.

Each entry has:
  path   — URL path relative to aaup.edu
  slug   — output filename (saved as aaup_<slug>.txt in data/knowledge/)
  title  — Arabic page title (prepended to the saved file for RAG context)
  type   — document type tag stored in Qdrant metadata
"""

from __future__ import annotations

from typing import List, TypedDict


class CrawlTarget(TypedDict):
    path: str
    slug: str
    title: str
    type: str


# ── Core academic content ──────────────────────────────────────────────────────
AAUP_TARGETS: List[CrawlTarget] = [
    {
        "path": "/ar/study/academic-programs",
        "slug": "academic_programs",
        "title": "البرامج الأكاديمية",
        "type": "academic",
    },
    {
        "path": "/ar/study/faculties",
        "slug": "faculties",
        "title": "الكليات والأقسام",
        "type": "academic",
    },
    {
        "path": "/ar/study",
        "slug": "admissions",
        "title": "القبول والدراسة",
        "type": "admissions",
    },
    {
        "path": "/ar/study/internal-and-scholarships",
        "slug": "scholarships",
        "title": "المنح الدراسية والمساعدات المالية",
        "type": "admissions",
    },
    # ── Regulations & Rules ────────────────────────────────────────────────────
    {
        "path": "/ar/media-center/bulletins/instruction-regulation",
        "slug": "regulations",
        "title": "الأنظمة والتعليمات",
        "type": "regulation",
    },
    {
        "path": "/ar/media-center/academic-calendar",
        "slug": "academic_calendar",
        "title": "التقويم الأكاديمي",
        "type": "regulation",
    },
    # ── University info ────────────────────────────────────────────────────────
    {
        "path": "/ar/about-university",
        "slug": "about_university",
        "title": "عن الجامعة",
        "type": "general",
    },
    {
        "path": "/ar/about-university/facts-and-figures",
        "slug": "facts_figures",
        "title": "الحقائق والأرقام",
        "type": "general",
    },
    # ── Student services ───────────────────────────────────────────────────────
    {
        "path": "/ar/e-services",
        "slug": "e_services",
        "title": "الخدمات الإلكترونية",
        "type": "services",
    },
    {
        "path": "/ar/university-life",
        "slug": "university_life",
        "title": "الحياة الجامعية",
        "type": "general",
    },
    {
        "path": "/ar/university-life/aaup-alumni",
        "slug": "alumni",
        "title": "الخريجون",
        "type": "general",
    },
    # ── Graduate programs ──────────────────────────────────────────────────────
    {
        "path": "/ar/masters",
        "slug": "masters_programs",
        "title": "برامج الدراسات العليا — الماجستير",
        "type": "academic",
    },
]
