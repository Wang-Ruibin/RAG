from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "河海大学校园知识问答助手"
    app_version: str = "0.1.0"
    database_url: str = ""
    db_backend: Literal["sqlite", "mysql"] = "sqlite"
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: SecretStr = SecretStr("")
    mysql_database: str = "campus_qa"
    data_dir: Path = Path("data")
    knowledge_dir: Path = Path("knowledge_docs")
    frontend_dist: Path = Path("frontend/dist")
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    jwt_secret: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 120
    initial_admin_email: str = "admin@campusqa.cn"
    initial_admin_name: str = "系统管理员"
    initial_admin_password: SecretStr = SecretStr("")

    deepseek_api_key: SecretStr = SecretStr("")
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024
    llm_timeout_seconds: float = 60.0

    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dimension: int = 512
    embedding_batch_size: int = 32
    model_device: Literal["auto", "cpu", "cuda"] = "auto"
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_max_length: int = 256
    rerank_candidate_k: int = 5
    model_local_files_only: bool = False
    rag_prewarm: bool = True
    rerank_enabled: bool = True
    retrieval_min_score: float = 0.7256
    retrieval_lexical_override_score: float = 0.70
    retrieval_lexical_min_coverage: float = 0.8
    retrieval_hybrid_max_rank: int = 3
    retrieval_context_min_score: float = 0.60
    retrieval_context_score_margin: float = 0.20
    dense_top_k: int = 20
    sparse_top_k: int = 20
    fusion_top_k: int = 12
    context_top_k: int = 5
    rrf_k: int = 60

    chunk_size: int = 500
    chunk_overlap: int = 80
    max_upload_bytes: int = 50 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = Field(default=(".md", ".txt", ".pdf", ".docx"))

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def index_dir(self) -> Path:
        return self.knowledge_base_dir / "index"

    @property
    def knowledge_base_dir(self) -> Path:
        """Standalone knowledge base; SQL never stores source text or embeddings."""
        return self.data_dir / "knowledge_base"

    @property
    def knowledge_artifact_dir(self) -> Path:
        return self.knowledge_base_dir / "documents"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Build a driver URL without requiring users to percent-encode passwords."""
        if self.database_url:
            return self.database_url
        if self.db_backend == "mysql":
            return URL.create(
                drivername="mysql+pymysql",
                username=self.mysql_user,
                password=self.mysql_password.get_secret_value(),
                host=self.mysql_host,
                port=self.mysql_port,
                database=self.mysql_database,
                query={"charset": "utf8mb4"},
            ).render_as_string(hide_password=False)
        return "sqlite:///./data/campusqa.db"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_artifact_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def validate_runtime(self) -> None:
        if self.db_backend != "mysql" or self.database_url:
            return
        missing = []
        unsafe_values = {
            "",
            "development-only-change-me",
            "replace-with-a-long-random-string",
            "replace-with-your-local-password",
        }
        if self.mysql_password.get_secret_value() in unsafe_values:
            missing.append("MYSQL_PASSWORD")
        if self.jwt_secret in unsafe_values or len(self.jwt_secret) < 32:
            missing.append("JWT_SECRET")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"MySQL 演示模式缺少安全配置: {names}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
