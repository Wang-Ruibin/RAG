"""RAG 问答 API 路由 — 对接 ai_service"""

import time

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.rag_service import RAGService
from app.services.user_service import UserService

router = APIRouter(prefix="/api/ai", tags=["RAG 问答"])


def _success(data=None, message="success"):
    """统一成功响应"""
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


def _error(code: int, message: str):
    """统一错误响应"""
    return {
        "code": code,
        "message": message,
        "data": None,
        "timestamp": int(time.time()),
    }


def _get_current_user(authorization: str = Header(None)) -> int:
    """从 JWT 令牌中解析当前用户ID"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="认证令牌格式错误")

    payload = UserService.decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="认证令牌无效")

    return user_id


def _require_admin(authorization: str = Header(None)) -> dict:
    """验证 JWT 并确保角色为 admin"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="认证令牌格式错误")

    payload = UserService.decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")

    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权限访问，需要管理员角色")

    return payload


# ─── 请求 / 响应模型 ───────────────────────────────────


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


# ─── 端点 ──────────────────────────────────────────────


@router.post("/query")
async def query(
    data: QueryRequest,
    user_id: int = Depends(_get_current_user),
):
    """RAG 问答查询"""
    try:
        result = await RAGService.query(question=data.question, top_k=data.top_k)
        return _success(data=result, message="查询成功")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")


@router.get("/query/stream")
async def query_stream(
    question: str,
    top_k: int = 5,
    user_id: int = Depends(_get_current_user),
):
    """SSE 流式 RAG 问答查询"""

    async def event_generator():
        async for event in RAGService.query_stream(question=question, top_k=top_k):
            yield f"data: {event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/reindex")
async def reindex(_=Depends(_require_admin)):
    """触发全量重新索引（管理员权限）"""
    try:
        result = await RAGService.reindex()
        return _success(data=result, message="重新索引已触发")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")


@router.get("/stats")
async def stats(_=Depends(_require_admin)):
    """获取知识库统计信息（管理员权限）"""
    try:
        result = await RAGService.stats()
        return _success(data=result, message="获取统计成功")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI 服务调用失败: {e}")
