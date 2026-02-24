"""
Application configuration via environment variables.
Uses pydantic-settings for type-safe config with .env file support.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cudas"
    DATABASE_ECHO: bool = False

    # ── LLM Configuration ──────────────────────────────────────────────────
    # GEMINI_API_KEY: str = ""
    # GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama3-70b-8192"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # ── Audio ─────────────────────────────────────────────────────────────
    AUDIO_UPLOAD_DIR: Path = Path("storage/audio/uploads")
    AUDIO_OUTPUT_DIR: Path = Path("storage/audio/outputs")

    # ── Interview Defaults ────────────────────────────────────────────────
    DEFAULT_DIFFICULTY: str = "medium"
    MAX_QUESTIONS_PER_SESSION: int = 15


settings = Settings()
