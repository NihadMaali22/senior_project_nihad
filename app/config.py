# ============================================================
# Application Configuration — Pydantic Settings
# ============================================================
"""
Centralized configuration management using pydantic-settings.
All settings are loaded from environment variables or .env file.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Supports .env file for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "Academic Decision Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ---- PostgreSQL ----
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "academic_user"
    POSTGRES_PASSWORD: str = "academic_pass_2024"
    POSTGRES_DB: str = "academic_db"
    DATABASE_URL: str = "postgresql+asyncpg://academic_user:academic_pass_2024@localhost:5432/academic_db"

    # ---- Qdrant ----
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "university_regulations"
    QDRANT_GRPC_PORT: int = 6334

    # ---- Ollama (Local LLM) ----
    # OLLAMA_URL: str = "http://localhost:11434"
    # OLLAMA_MODEL: str = "llama3.1:8b"
    # OLLAMA_TIMEOUT: int = 120

    # ---- Gemini API ----
    GEMINI_API_KEY: str = "AIzaSyCiexVZaLFDJMPF1QR_wtaC5Es1OWtd0IQ"
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_TIMEOUT: int = 90

    # ---- Groq API ----
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "qwen/qwen3-32b"

    # ---- Embedding Models ----
    DENSE_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    DENSE_EMBEDDING_DIM: int = 384
    SPARSE_EMBEDDING_MODEL: str = "prithivida/Splade_PP_en_v1"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ---- RAG Settings ----
    RAG_TOP_K: int = 10
    RAG_RERANK_TOP_K: int = 5
    RAG_SPLIT_BY: str = "sentence"
    RAG_SPLIT_LENGTH: int = 5
    RAG_SPLIT_OVERLAP: int = 1

    # ---- JWT Authentication ----
    JWT_SECRET_KEY: str = "change-this-to-a-very-long-random-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480

    # ---- CORS ----
    CORS_ORIGINS: str = '["http://localhost:3000","http://localhost:8080"]'

    # ---- TTS ----
    MUNSIT_API_KEY: str = ""
    ELEVEN_API_KEY: str = ""

    # ---- Data Directories ----
    REGULATIONS_DATA_DIR: str = "data/regulations"   # hand-written policy files
    KNOWLEDGE_DATA_DIR: str = "data/knowledge"        # crawled from aaup.edu/ar

    # ---- Web Crawler (Knowledge Pipeline) ----
    AAUP_BASE_URL: str = "https://www.aaup.edu"
    CRAWLER_DELAY_SECONDS: float = 1.0               # polite delay between requests

    # ---- Frontend / Mobile App ----
    # يُستخدم في /robot/session لبناء qr_data URL الذي يقرأه التطبيق
    FRONTEND_URL: str = "mujeeb://robot-login"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from JSON string to list."""
        try:
            return json.loads(self.CORS_ORIGINS)
        except (json.JSONDecodeError, TypeError):
            return ["http://localhost:3000"]


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings singleton.
    Call this function to get the application settings anywhere in the codebase.
    """
    return Settings()
