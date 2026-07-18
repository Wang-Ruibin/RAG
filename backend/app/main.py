"""FastAPI application entry point for 河海大学校园问答助手.

Wires together all routers, CORS, lifespan lifecycle, and seed data.
"""

from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import get_db, init_database, transaction, utc_now
from .security import hash_password
from .rag_engine import rag_engine
from .routers.auth import router as auth_router
from .routers.cache import router as cache_router
from .routers.users import router as users_router, stats_router
from .routers.documents import router as documents_router
from .routers.chat import router as chat_router
from .routers.conversations import router as conversations_router
from .routers.roles import router as roles_router


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def _seed_admin():
    """Create the default admin account if it does not already exist,
    and ensure its role is always ADMIN.

    Credentials: admin / admin123
    """
    with transaction() as db:
        # Seed default roles
        existing_roles = db.execute("SELECT COUNT(*) AS cnt FROM roles").fetchone()["cnt"]
        if existing_roles == 0:
            now = utc_now()
            db.execute(
                """INSERT INTO roles (name, description, is_system, created_at)
                   VALUES (?, ?, 1, ?)""",
                ("ADMIN", "系统管理员", now),
            )
            db.execute(
                """INSERT INTO roles (name, description, is_system, created_at)
                   VALUES (?, ?, 1, ?)""",
                ("STUDENT", "普通学生", now),
            )
            print("[OK] 默认角色创建成功 (ADMIN, STUDENT)")

        # Seed admin user
        admin = db.execute(
            "SELECT * FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if not admin:
            db.execute(
                """INSERT INTO users(name, username, password_hash, role, is_active, created_at)
                   VALUES (?, ?, ?, 'ADMIN', 1, ?)""",
                ("系统管理员", "admin", hash_password("admin123"), utc_now()),
            )
            print("[OK] 默认管理员账号创建成功 (admin / admin123)")
        elif admin["role"] != "ADMIN":
            # Fix if role was accidentally changed
            db.execute(
                "UPDATE users SET role = 'ADMIN' WHERE username = ?", ("admin",)
            )
            print("[OK] 已修复管理员角色 (admin -> ADMIN)")


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialise DB, RAG engine, seed data, and KB.

    Runs on every worker at startup; safe to call repeatedly.
    """
    # 1. Create required data directories
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # 2. Initialise database tables
    init_database()

    # 3. Initialise RAG engine (sentence-transformers + FAISS singleton)
    try:
        _ = rag_engine  # triggers singleton init
        print("[OK] RAG engine initialized (sentence-transformers + FAISS)")
    except Exception as e:
        print(f"[ERROR] RAG engine init failed: {e}")
        raise

    # 4. Seed default admin user if not already present
    _seed_admin()

    # 5. Load knowledge base asynchronously in a background thread
    def _load_kb():
        try:
            if rag_engine.vector_count > 0:
                print(f"[OK] 知识库已从缓存加载 ({rag_engine.vector_count} 向量), 跳过重新处理")
                return
            if settings.knowledge_base_dir.exists():
                loaded = rag_engine.load_knowledge_base(settings.knowledge_base_dir)
                print(f"[OK] 知识库加载完成: {loaded} 篇文档")
        except Exception as e:
            print(f"[ERROR] 知识库加载失败: {e}")

    threading.Thread(target=_load_kb, daemon=True).start()

    yield


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="河海大学校园问答助手 API",
    version="2.0.0",
    lifespan=lifespan,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth_router)
app.include_router(cache_router)
app.include_router(users_router)
app.include_router(stats_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(roles_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    """Basic health-check endpoint (no DB dependency)."""
    return {"status": "ok", "mode": "local", "version": "2.0.0"}
