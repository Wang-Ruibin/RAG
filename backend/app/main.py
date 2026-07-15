"""FastAPI 应用入口"""

import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import admin_router, document_router, qa_router, user_router
from app.redis_client import redis_client as _  # Redis pre-init

app = FastAPI(title="CampusQA", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(user_router)
app.include_router(document_router)
app.include_router(qa_router)
app.include_router(admin_router)

# ---- Frontend static files (build first: cd frontend && npm run build) ----
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend_assets")
    # SPA fallback: serve index.html for all non-API routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str, request: Request):
        # Skip API routes (they should have matched above routers)
        if full_path.startswith("api/") or full_path.startswith("admin/cache") or full_path.startswith("docs") or full_path.startswith("redoc"):
            return HTMLResponse(status_code=404)
        fp = FRONTEND_DIR / full_path
        if fp.exists() and fp.is_file():
            return FileResponse(fp)
        return FileResponse(FRONTEND_DIR / "index.html")


_admin_html = Path(__file__).resolve().parent / "static" / "admin.html"


@app.get("/admin/cache", response_class=HTMLResponse, include_in_schema=False)
def admin_cache_page():
    """管理后台缓存面板"""
    if _admin_html.exists():
        return HTMLResponse(content=_admin_html.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.on_event("startup")
def on_startup():
    """应用启动时创建数据库表"""
    try:
        init_db()
        print("✓ 数据库表初始化完成")
    except Exception as e:
        print(f"✗ 数据库表初始化失败: {e}")
        print("  请确保 MySQL 服务已启动且连接信息正确")


@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "service": "CampusQA",
            "version": "1.0.0",
            "status": "running",
        },
        "timestamp": int(time.time()),
    }
