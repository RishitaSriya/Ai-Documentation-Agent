"""Application configuration module using Pydantic Settings."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "AI-API-Doc-Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Database
    DATABASE_URL: str = "sqlite:///./storage/api_agent.db"

    # Storage Paths
    STORAGE_PATH: str = "./storage"

    # GitHub Credentials
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None

    # AI Provider Settings
    LLM_PROVIDER: str = "mock"  # mock, gemini, openai
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gemini-2.5-flash"

    # Automation & Quality Thresholds
    CONFIDENCE_THRESHOLD: float = 0.85
    AUTO_PUBLISH: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def storage_dir(self) -> Path:
        p = Path(self.STORAGE_PATH).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def repositories_storage_dir(self) -> Path:
        p = self.storage_dir / "repositories"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def openapi_storage_dir(self) -> Path:
        p = self.storage_dir / "openapi"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def logs_storage_dir(self) -> Path:
        p = self.storage_dir / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
