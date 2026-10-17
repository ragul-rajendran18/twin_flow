"""Environment-based application configuration.

All secrets and environment-specific values are read from environment
variables (optionally from a local ``.env`` file).  No credentials are ever
hardcoded or committed.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---------------------------------------------------------
    database_url: str = "postgresql+psycopg://postgres:ragul1810@localhost:5432/warehouse_db"
    db_echo: bool = False

    # --- Authentication --------------------------------------------------
    jwt_secret_key: SecretStr | None = None
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    # --- Application ------------------------------------------------------
    app_name: str = "warehouse-congestion-backend"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    # --- CORS / frontend --------------------------------------------------
    frontend_origin: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # --- Limits -----------------------------------------------------------
    max_batch_size: int = Field(default=50, ge=1, le=1000)
    max_simulation_events: int = Field(default=500, ge=1, le=10000)
    max_page_size: int = Field(default=100, ge=1, le=1000)

    # --- ML ---------------------------------------------------------------
    artifacts_dir: str = "ml/artifacts"
    congestion_threshold_moderate: float = Field(default=0.40, ge=0.0, le=1.0)
    congestion_threshold_high: float = Field(default=0.70, ge=0.0, le=1.0)
    bottleneck_threshold: float = Field(default=0.50, ge=0.0, le=1.0)

    # --- Derived helpers --------------------------------------------------
    @property
    def cors_origin_list(self) -> List[str]:
        """CORS origins as a list (``CORS_ORIGINS`` CSV, fallback to frontend)."""
        raw = self.cors_origins.strip()
        if not raw:
            return [self.frontend_origin]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        """Synchronous SQLAlchemy URL (used by Alembic and tests)."""
        return self.database_url

    @property
    def artifacts_path(self) -> Path:
        return Path(self.artifacts_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]
