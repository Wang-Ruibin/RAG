"""FastAPI 应用入口"""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import document_router, qa_router, user_router
from app.redis_client import redis_client as _  # 触发 Redis 预初始化

app = FastAPI(
    title="CampusQA - 河海大学校园知识问答助手",
    description="基于 FastAPI + RAG 的校园知识问答系统后端 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(user_router)
app.include_router(document_router)
app.include_router(qa_router)


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
