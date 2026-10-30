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
import json
from typing import Optional, Union

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
    PRODUCTION: bool = False  # Set to True in production; enables secure cookies & HTTPS-only session

    # ── URLs ──────────────────────────────────────────────────────────────────
    # Set these in .env — they drive OAuth redirects, CORS, and cookie security.
    # Local dev defaults are provided automatically.
    FRONTEND_URL: str = "http://localhost:3000"   # e.g. https://app.yourdomain.com
    BACKEND_URL: str = "http://localhost:5000"    # e.g. https://api.yourdomain.com

    # CORS origins: env var wins; falls back to FRONTEND_URL + localhost.
    # Set ALLOWED_ORIGINS as a comma-separated string in .env for production,
    # e.g. ALLOWED_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
    ALLOWED_ORIGINS: Union[list[str], str] = []

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, v: object) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        return []

    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Effective CORS origins — always includes FRONTEND_URL."""
        origins = list(self.ALLOWED_ORIGINS)  # from env var
        if not origins:
            if self.PRODUCTION:
                origins = [self.FRONTEND_URL]
            else:
                # Default: allow frontend + common local ports in development
                origins = [
                    self.FRONTEND_URL,
                    "http://localhost:3000",
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                ]
        # Always make sure FRONTEND_URL is included
        if self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return list(dict.fromkeys(origins))  # deduplicate, preserve order

    @property
    def COOKIE_SECURE(self) -> bool:
        """True when running in production (behind HTTPS)."""
        return self.PRODUCTION

    @property
    def SESSION_HTTPS_ONLY(self) -> bool:
        """https_only for Starlette SessionMiddleware."""
        return self.PRODUCTION

    # ── Security ──────────────────────────────────────────────────────────────
    FLASK_SECRET_KEY: str = Field(default="change-me-in-production")  # kept name for .env compat
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60  # Short-lived access token: 60 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh token lifetime: 7 days
    ENABLE_DEV_AUTH: bool = False  # Fail-closed: Must be explicitly enabled in non-production environments
    TRUSTED_PROXIES: Union[list[str], str] = ["127.0.0.1", "::1"]

    @field_validator("TRUSTED_PROXIES", mode="before")
    @classmethod
    def _parse_trusted_proxies(cls, v: object) -> list[str]:
        if not v:
            return ["127.0.0.1", "::1"]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return ["127.0.0.1", "::1"]
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            return [x.strip() for x in s.split(",") if x.strip()]
        if isinstance(v, (list, tuple, set)):
            return [str(x).strip() for x in v if str(x).strip()]
        return ["127.0.0.1", "::1"]  # CIDRs or IPs of trusted reverse proxies

    @property
    def JWT_SECRET(self) -> str:
        return self.FLASK_SECRET_KEY

    def validate_production_environment(self) -> None:
        """
        Invoked during lifespan startup. Fails fast if mandatory production
        settings are missing or insecure, preventing silent development fallbacks in production.
        """
        if not self.PRODUCTION:
            return

        if self.ENABLE_DEV_AUTH:
            raise RuntimeError(
                "CRITICAL: ENABLE_DEV_AUTH must never be True when PRODUCTION=True. Refusing to start."
            )

        if self.FLASK_SECRET_KEY == "change-me-in-production" or len(self.FLASK_SECRET_KEY) < 32:
            raise RuntimeError(
                "CRITICAL: PRODUCTION=True requires a strong, randomly-generated FLASK_SECRET_KEY "
                "(minimum 32 characters). Refusing to start with insecure secret."
            )

        if not self.SUPABASE_URL or not self.SUPABASE_ANON_KEY:
            raise RuntimeError(
                "CRITICAL: PRODUCTION=True requires an authoritative remote database "
                "(SUPABASE_URL and SUPABASE_SERVICE_KEY). Local offline storage fallback is disabled."
            )

        if "localhost" in self.FRONTEND_URL:
            raise RuntimeError(
                f"CRITICAL: PRODUCTION=True requires a valid production FRONTEND_URL, got '{self.FRONTEND_URL}'."
            )

        if self.JWT_EXPIRE_MINUTES > 1440:
            raise RuntimeError(
                f"CRITICAL: PRODUCTION=True requires short-lived JWT access tokens (<= 1440 min), "
                f"got {self.JWT_EXPIRE_MINUTES} min."
            )

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

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
    GEMINI_MODEL: str = "gemini-4-argon"

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

    # ── Dodo Payments & Payment Provider ───────────────────────────────────────
    PAYMENT_PROVIDER: str = "dodo"
    DODO_PAYMENTS_API_KEY: Optional[str] = None
    DODO_PAYMENTS_WEBHOOK_KEY: Optional[str] = None
    DODO_PAYMENTS_ENVIRONMENT: str = "test_mode"  # "test_mode" or "live_mode"
    DODO_PRODUCT_PRO_MONTHLY: str = "pdt_pro_monthly_29"
    DODO_PRODUCT_TEAM_MONTHLY: str = "pdt_team_monthly_79"

    # ── Clerk Authentication ──────────────────────────────────────────────────
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_JWT_KEY: Optional[str] = None

    # ── Email & Notification Dispatch (Resend / SMTP) ─────────────────────────
    RESEND_API_KEY: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_USE_TLS: bool = True
    MAIL_FROM: str = "notifications@dataforge.app"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton. Use this everywhere."""
    return Settings()
