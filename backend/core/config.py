"""
Analytic AI — App Settings
Reads from .env via pydantic-settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "Analytic AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/analytic_ai.db"

    # File storage
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    MAX_UPLOAD_SIZE_MB: int = 50

    # CORS
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://analytic-ai-icg.web.app"
    )

    # Currency
    DEFAULT_CURRENCY: str = "KES"
    DECIMAL_PLACES: int = 2

    # Branding
    COMPANY_NAME: str = "Analytic AI"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def upload_dir(self) -> Path:
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        return self.UPLOAD_DIR

    @property
    def output_dir(self) -> Path:
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return self.OUTPUT_DIR


settings = Settings()
