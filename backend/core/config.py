"""
Analytic AI — Application Configuration
Reads settings from environment variables / .env file
"""
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    APP_NAME: str = "Analytic AI"
    APP_VERSION: str = "1.0.0"
    DEFAULT_CURRENCY: str = "KES"

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./analytic_ai.db"

    # ── Cloudflare R2 / S3 ────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "analytic-ai"

    # ── Directories ───────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"

    @property
    def upload_dir(self) -> Path:
        p = Path(__file__).parent.parent / self.UPLOAD_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_dir(self) -> Path:
        p = Path(__file__).parent.parent / self.OUTPUT_DIR
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
