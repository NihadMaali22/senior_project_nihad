# ============================================================
# Knowledge Module
# ============================================================
# Crawls the AAUP university website (aaup.edu/ar) and saves
# clean text to data/knowledge/ for RAG ingestion.
#
# This module is STANDALONE — it is NOT imported by the app at
# startup. Run it manually on demand:
#
#   python -m app.knowledge.pipeline            # crawl + ingest
#   python -m app.knowledge.pipeline --force    # re-crawl all pages
# ============================================================
