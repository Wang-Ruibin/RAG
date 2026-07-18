"""Configuration for the campus QA backend.

Reads from .env file with defaults for local development.
"""

from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env", override=False)

# Set HuggingFace mirror for users in China (hf-mirror.com is accessible)
# User can override via environment variable or .env file
if "HF_ENDPOINT" not in os.environ:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


@dataclass(frozen=True)
class Settings:
    # Security
    app_secret: str = os.getenv("APP_SECRET", "campus-qa-local-development-secret")
    token_minutes: int = 60 * 24  # 24 hours

    # Database
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "campus_qa.db"))
    )

    # File uploads
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads")))
    data_dir: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    max_upload_bytes: int = 10 * 1024 * 1024  # 10MB
    knowledge_base_dir: Path = Path(
        os.getenv("KNOWLEDGE_BASE_DIR", str(BASE_DIR.parent / "knowledge"))
    )

    # CORS
    frontend_origins: list[str] = field(default_factory=lambda: [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8081",
    ])

    # RAG / Embedding (local sentence-transformers, no API key needed)
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    # LLM — DeepSeek via OpenAI-compatible API (fallback: chains chunks together)
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv(
        "LLM_BASE_URL", "https://api.deepseek.com"
    )
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    # Retain backward compatibility for DashScope users
    dashscope_api_key: str = os.getenv("DASHSCOPE_API_KEY", "")

    # RAG parameters
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    top_k: int = int(os.getenv("TOP_K", "5"))


settings = Settings()
