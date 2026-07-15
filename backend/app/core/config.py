"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Backend project root (…/backend), used to anchor relative paths so they don't
# depend on the process's working directory. config.py lives at
# backend/app/core/config.py, so the root is three parents up.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application
    APP_NAME: str = "AI Powered TMS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=list)

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "tms"

    # Security / JWT
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_SETUP_TOKEN_EXPIRE_HOURS: int = 48
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 2

    # AI
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-opus-4-8"
    # Quiz generation is a structured extraction task — a fast model keeps it
    # quick without sacrificing quality (output is validated regardless).
    CLAUDE_QUIZ_MODEL: str = "claude-haiku-4-5-20251001"
    # Trending recommendations are short, bounded JSON — a fast model keeps the
    # admin page responsive instead of waiting on the heavyweight default model.
    CLAUDE_TRENDING_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_MAX_TOKENS: int = 8192
    # Local speech-to-text model (faster-whisper) for transcribing uploaded
    # audio/video so quizzes can be generated from spoken content.
    # tiny|base|small|medium — larger = more accurate but slower on CPU.
    WHISPER_MODEL: str = "base"

    # SSO — Microsoft Entra ID (OpenID Connect). Optional; additive to password
    # login. When these are unset, SSO stays disabled and nothing else changes.
    SSO_TENANT_ID: str = ""
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    SSO_REDIRECT_URI: str = "http://localhost:8020/api/v1/auth/sso/callback"
    # Frontend page that receives the issued tokens after a successful login.
    SSO_POST_LOGIN_URL: str = "http://localhost:5180/sso/callback"
    # Create an employee account on first SSO login for unknown emails.
    SSO_AUTO_PROVISION: bool = True
    # Comma-separated email domains that use SSO (e.g. "incubxperts.com,acme.com").
    # The login page enables the "Sign in with Microsoft" button only for emails
    # in these domains. Empty = any domain may use SSO (when SSO is configured).
    SSO_ALLOWED_DOMAINS: str = ""

    # File storage
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 200

    # Frontend
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    # Due-date reminders — a background task periodically creates reminder
    # notifications (and emails) for enrollments approaching their due date.
    REMINDER_SCHEDULER_ENABLED: bool = True
    REMINDER_INTERVAL_HOURS: int = 12

    # Email
    # Two delivery backends, tried in this order by app.utils.email:
    #   1. Brevo HTTP API (BREVO_API_KEY) — required on hosts that block outbound
    #      SMTP (e.g. Render). Sends over HTTPS, so it works where SMTP can't.
    #   2. SMTP (SMTP_HOST) — used for local dev / hosts that allow SMTP.
    # If neither is set, email is a no-op ("skipped"). The sender identity
    # (SMTP_FROM) is shared by both backends.
    BREVO_API_KEY: str = ""
    BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "AI TMS <no-reply@tms.local>"
    SMTP_TLS: bool = True

    # Bootstrap admin
    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_EMAIL: str = "admin@yopmail.com"
    FIRST_ADMIN_PASSWORD: str = "Admin@12345"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _assemble_cors(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def upload_path(self) -> Path:
        """Absolute base directory for stored files.

        An absolute UPLOAD_DIR is used as-is (e.g. a persistent volume in
        production); a relative one is anchored to the backend project root so
        the location is stable no matter which directory the server starts in.
        File paths are persisted relative to this base, so the same database
        value resolves correctly in every environment (local and deployed)."""
        p = Path(self.UPLOAD_DIR)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p)
        return p.resolve()

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def sso_configured(self) -> bool:
        return bool(self.SSO_TENANT_ID and self.SSO_CLIENT_ID and self.SSO_CLIENT_SECRET)

    @property
    def sso_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.SSO_ALLOWED_DOMAINS.split(",") if d.strip()]

    def sso_eligible_email(self, email: str) -> bool:
        """True if this email may sign in with SSO.

        Requires SSO to be fully configured; then, if SSO domains are listed,
        the email's domain must be one of them (else any domain is allowed)."""
        if not self.sso_configured:
            return False
        if "@" not in (email or ""):
            return False
        domain = email.split("@")[-1].strip().lower()
        if not domain:
            return False
        allowed = self.sso_domains
        return domain in allowed if allowed else True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
