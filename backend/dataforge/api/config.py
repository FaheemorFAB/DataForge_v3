"""
dataforge/api/config.py
─────────────────────────
Pydantic Settings — single source of truth for all configuration.

Load order (Pydantic-Settings default):
  1. .env file in project root
  2. Environment variables
  3. Field defaults
"""

from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Resolve project root ──────────────────────────────────────────────────────
_THIS_FILE = Path(__file__).resolve()
_API_DIR   = _THIS_FILE.parent           # dataforge/api/
_DATAFORGE = _API_DIR.parent             # dataforge/
_BACKEND   = _DATAFORGE.parent           # backend/
_PROJECT_ROOT = _BACKEND.parent          # DataForge_v3-main/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "DataForge"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]

    # ── Security ──────────────────────────────────────────────────────────────
    FLASK_SECRET_KEY: str = Field(default="change-me-in-production")  # kept name for .env compat
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    @property
    def JWT_SECRET(self) -> str:
        return self.FLASK_SECRET_KEY

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    @property
    def GOOGLE_AUTH_ENABLED(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    # ── Database (Supabase) ───────────────────────────────────────────────────
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None  # legacy alias

    @property
    def SUPABASE_ANON_KEY(self) -> Optional[str]:
        return self.SUPABASE_SERVICE_KEY or self.SUPABASE_KEY

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Storage paths ─────────────────────────────────────────────────────────
    DATAFORGE_ROOT: str = str(_DATAFORGE)
    DATAFORGE_PROJECTS_DIR: Optional[str] = None
    DATAFORGE_INSTANCE_DIR: Optional[str] = None
    DATAFORGE_STORE_DIR: Optional[str] = None

    @property
    def PROJECTS_DIR(self) -> Path:
        if self.DATAFORGE_PROJECTS_DIR:
            return Path(self.DATAFORGE_PROJECTS_DIR)
        instance = Path(self.DATAFORGE_INSTANCE_DIR) if self.DATAFORGE_INSTANCE_DIR else Path(self.DATAFORGE_ROOT) / "instance"
        return instance / "projects"

    # ── Frontend ──────────────────────────────────────────────────────────────
    FRONTEND_DIR: str = str(_PROJECT_ROOT / "frontend")

    @property
    def TEMPLATES_DIR(self) -> Path:
        return Path(self.FRONTEND_DIR) / "templates"

    @property
    def STATIC_DIR(self) -> Path:
        return Path(self.FRONTEND_DIR) / "static"

    # ── Worker ────────────────────────────────────────────────────────────────
    WORKER_MAX_THREADS: int = Field(default=0)  # 0 = auto (cpu_count * 2, max 8)

    @property
    def RESOLVED_WORKER_THREADS(self) -> int:
        if self.WORKER_MAX_THREADS > 0:
            return self.WORKER_MAX_THREADS
        return min((os.cpu_count() or 2) * 2, 8)

    # ── Gemini / Vertex AI ────────────────────────────────────────────────────
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    VERTEX_PROJECT: Optional[str] = None
    VERTEX_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── Upload limits ─────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 200

    @property
    def MAX_UPLOAD_BYTES(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ── Rate limits ───────────────────────────────────────────────────────────
    RATE_LIMIT_UPLOAD: str = "20/minute"
    RATE_LIMIT_QUERY: str = "30/minute"
    RATE_LIMIT_AUTOML: str = "2/2minutes"
    RATE_LIMIT_AUTH: str = "10/minute"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton. Use this everywhere."""
    return Settings()
