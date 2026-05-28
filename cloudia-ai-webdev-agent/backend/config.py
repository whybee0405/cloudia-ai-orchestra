from __future__ import annotations

from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    db_password: str = ""

    # Brand DNA Service
    brand_dna_service_url: str = "http://localhost:8000"
    internal_api_secret: str = ""

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Media APIs
    unsplash_access_key: Optional[str] = None
    pexels_api_key: Optional[str] = None

    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    notification_from: str = "noreply@cloudia.co.za"

    # App
    secret_key: str
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173"

    # Encryption — MUST be set. Application refuses to start if missing.
    encryption_key: str

    @model_validator(mode="after")
    def _validate_required_secrets(self) -> "Settings":
        """Refuse to start if critical security values are missing or left as placeholders."""
        errors: list[str] = []

        if not self.secret_key or not self.secret_key.strip():
            errors.append(
                "SECRET_KEY must be set to a non-empty random string. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )

        if not self.encryption_key or not self.encryption_key.strip():
            errors.append(
                "ENCRYPTION_KEY must be set to a valid Fernet key. "
                "Generate one with: "
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )

        if errors:
            raise ValueError(
                "Application startup blocked — missing required security settings:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
