"""Cross-platform production entry point used by Windows, Linux, macOS, and WSL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    frontend_index = root / "frontend" / "dist" / "index.html"
    if not env_file.is_file():
        raise SystemExit("缺少 .env：请先复制 .env.example 并填写本机配置。")
    if not frontend_index.is_file():
        raise SystemExit("缺少前端构建产物：请先执行 cd frontend && npm run build。")

    os.chdir(root)
    sys.path.insert(0, str(root / "backend"))

    # Keep the versioned corpus and runtime knowledge base in sync at process
    # startup. The import is idempotent: existing content hashes are skipped,
    # while a document deleted at runtime can be imported again on a later
    # restart if its source file intentionally remains in knowledge_docs/.
    from app.cli import index_corpus
    from app.core.config import settings
    from app.core.database import init_database

    init_database()
    index_corpus(settings.knowledge_dir, settings.initial_admin_email)

    uvicorn.run(
        "app.main:app",
        app_dir=str(root / "backend"),
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )


if __name__ == "__main__":
    main()
