"""
Application configuration via environment variables.
Uses pydantic-settings for type-safe config with .env file support.
"""

from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_APP_DIR = Path(__file__).resolve().parents[1]
_ENV_PATH = _APP_DIR / ".env"


class Settings(BaseSettings):
    """Central application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:yagna@localhost:5432/CUDAS"
    DATABASE_ECHO: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_database_url(cls, url: str) -> str:
        """Accept a plain Neon/Postgres URL and adapt it for asyncpg."""
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        if "?" in url:
            base, query = url.split("?", 1)
            params = [p for p in query.split("&") if p and not p.startswith("channel_binding=")]
            params = ["ssl=require" if p.startswith("sslmode=") else p for p in params]
            url = base + ("?" + "&".join(params) if params else "")
        return url

    # ── Deployment ────────────────────────────────────────────────────────
    # Comma-separated extra CORS origins, e.g. "https://cudas.vercel.app"
    CORS_ORIGINS: str = ""
    # Skip loading the embedding model at startup (saves RAM on small hosts)
    SKIP_EMBEDDING_WARMUP: bool = False
    # If set, embeddings are computed via the Hugging Face Inference API
    # instead of loading the model locally (needed on 512 MB hosts)
    HF_TOKEN: str = ""

    # ── LLM Configuration ──────────────────────────────────────────────────
    # GEMINI_API_KEY: str = ""
    # GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GROQ_API_KEY: str = ""
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"
    # NVIDIA NIM (OpenAI-compatible). Used when LLM_PROVIDER=nvidia, or when
    # LLM_PROVIDER is empty and NVIDIA_API_KEY is set.
    LLM_PROVIDER: str = ""  # "nvidia" | "groq" | "" (auto)
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL_NAME: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    NVIDIA_ENABLE_THINKING: bool = False
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_TEMPERATURE: float = 0.4
    LLM_MAX_TOKENS: int = 1024

    # ── Audio ─────────────────────────────────────────────────────────────
    AUDIO_UPLOAD_DIR: Path = Path("storage/audio/uploads")
    AUDIO_OUTPUT_DIR: Path = Path("storage/audio/outputs")

    # ── Interview Defaults ────────────────────────────────────────────────
    DEFAULT_DIFFICULTY: str = "medium"
    MAX_QUESTIONS_PER_SESSION: int = 15
    VOICE_SILENCE_TIMEOUT: int = 10
    ANSWER_TIMEOUT: int = 20

    # ── JWT Authentication ────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-super-secret-key"
    JWT_REFRESH_SECRET: str = "change-me-refresh-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── SMTP Email ────────────────────────────────────────────────────────
    SMTP_EMAIL: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    # ── Static CUDAS Admin ────────────────────────────────────────────────
    CUDAS_ADMIN_EMAIL: str = "admin@cudas.com"
    CUDAS_ADMIN_PASSWORD: str = "admin123"

    @field_validator("CUDAS_ADMIN_EMAIL", "CUDAS_ADMIN_PASSWORD")
    @classmethod
    def _strip_admin_credentials(cls, value: str) -> str:
        """Tolerate stray spaces/newlines pasted into hosting dashboards."""
        return value.strip()

    # ── RAG / Embedding ──────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5


settings = Settings()
