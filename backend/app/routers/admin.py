"""管理后台 API — 缓存管理"""

import time
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse

from app.redis_client import redis_client
from app.services.user_service import UserService

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _success(data=None, message="success"):
    return {
        "code": 200,
        "message": message,
        "data": data,
        "timestamp": int(time.time()),
    }


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


def _scan_keys(pattern: str, count: int = 500) -> list[str]:
    """使用 SCAN 迭代获取匹配的 key 列表"""
    keys = []
    cursor = 0
    try:
        while True:
            cursor, batch = redis_client.scan(
                cursor=cursor, match=pattern, count=count
            )
            keys.extend(batch)
            if cursor == 0:
                break
    except Exception:
        pass
    return keys


# ─── 缓存统计 ─────────────────────────────────────────


@router.get("/cache/stats")
def get_cache_stats(_=Depends(_require_admin)):
    """获取缓存统计信息"""
    stat = {
        "total_keys": 0,
        "keys_by_prefix": {},
        "memory_used": "N/A",
        "memory_human": "N/A",
        "hit_ratio": "N/A",
        "evicted_keys": "N/A",
        "uptime": "N/A",
        "redis_version": "N/A",
        "server_type": "unknown",
    }

    try:
        # 检测是否为 fakeredis
        info = redis_client.info()
        stat["redis_version"] = info.get("redis_version", "N/A")
        stat["uptime"] = info.get("uptime_in_seconds", "N/A")
        used_memory = info.get("used_memory", 0)
        stat["memory_used"] = used_memory
        if used_memory and used_memory != "N/A":
            stat["memory_human"] = info.get("used_memory_human", str(used_memory))

        # keyspace_hits / misses
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        if total > 0:
            stat["hit_ratio"] = round(hits / total * 100, 2)

        stat["evicted_keys"] = info.get("evicted_keys", "N/A")
        stat["server_type"] = "real" if "uptime_in_seconds" in info else "fakeredis"
    except Exception:
        stat["server_type"] = "fakeredis"

    # 按前缀统计 key 数量
    prefixes = ["campus:qa:qa:*", "campus:qa:session:*", "campus:qa:hot:*"]
    label_map = {
        "campus:qa:qa:*": "Q&A 缓存",
        "campus:qa:session:*": "会话缓存",
        "campus:qa:hot:*": "热门问题",
    }
    total_keys = 0
    keys_by_prefix = {}
    for pattern in prefixes:
        keys = _scan_keys(pattern)
        count = len(keys)
        keys_by_prefix[label_map[pattern]] = {
            "count": count,
            "pattern": pattern,
        }
        total_keys += count

    # 其他 key
    all_keys = _scan_keys("*")
    other_count = len(all_keys) - total_keys
    if other_count > 0:
        keys_by_prefix["其他"] = {"count": other_count, "pattern": "*"}
        total_keys = len(all_keys)

    stat["total_keys"] = total_keys
    stat["keys_by_prefix"] = keys_by_prefix

    return _success(data=stat)


# ─── 缓存 key 列表 ────────────────────────────────────


@router.get("/cache/keys")
def list_cache_keys(
    pattern: str = "campus:qa:*",
    _=Depends(_require_admin),
):
    """列出所有缓存 key 及类型、TTL"""
    keys = _scan_keys(pattern)
    result = []
    for key in keys:
        try:
            ktype = redis_client.type(key)
            ttl = redis_client.ttl(key)
            result.append({"key": key, "type": ktype, "ttl": ttl})
        except Exception:
            result.append({"key": key, "type": "unknown", "ttl": -1})

    result.sort(key=lambda x: x["key"])
    return _success(
        data={"total": len(result), "keys": result, "pattern": pattern}
    )


# ─── 清理操作 ─────────────────────────────────────────


@router.delete("/cache/clear")
def clear_all_cache(_=Depends(_require_admin)):
    """清除所有缓存数据"""
    keys = _scan_keys("campus:qa:*")
    deleted = 0
    if keys:
        try:
            deleted = redis_client.delete(*keys)
        except Exception:
            for k in keys:
                try:
                    redis_client.delete(k)
                    deleted += 1
                except Exception:
                    pass
    return _success(data={"deleted": deleted}, message="所有缓存已清空")


@router.delete("/cache/clear/qa")
def clear_qa_cache(_=Depends(_require_admin)):
    """清除 Q&A 回答缓存"""
    keys = _scan_keys("campus:qa:qa:*")
    deleted = 0
    if keys:
        try:
            deleted = redis_client.delete(*keys)
        except Exception:
            for k in keys:
                try:
                    redis_client.delete(k)
                    deleted += 1
                except Exception:
                    pass
    return _success(data={"deleted": deleted}, message="Q&A 缓存已清空")


@router.delete("/cache/clear/sessions")
def clear_session_cache(_=Depends(_require_admin)):
    """清除会话缓存"""
    keys = _scan_keys("campus:qa:session:*")
    deleted = 0
    if keys:
        try:
            deleted = redis_client.delete(*keys)
        except Exception:
            for k in keys:
                try:
                    redis_client.delete(k)
                    deleted += 1
                except Exception:
                    pass
    return _success(data={"deleted": deleted}, message="会话缓存已清空")


@router.delete("/cache/clear/hot")
def clear_hot_cache(_=Depends(_require_admin)):
    """重置热门问题数据"""
    keys = _scan_keys("campus:qa:hot:*")
    deleted = 0
    if keys:
        try:
            deleted = redis_client.delete(*keys)
        except Exception:
            for k in keys:
                try:
                    redis_client.delete(k)
                    deleted += 1
                except Exception:
                    pass
    return _success(data={"deleted": deleted}, message="热门问题数据已重置")


# ─── 缓存预热 ─────────────────────────────────────────


@router.post("/cache/warmup")
def warmup_cache(
    limit: int = 10,
    _=Depends(_require_admin),
):
    """预热缓存

    从数据库中读取热门问答，预先写入 Redis 缓存。
    当前实现：统计现有缓存中的热点数据。
    """
    from app.cache.qa_cache import QACache

    hot = QACache.get_hot_questions(limit=limit)
    warmed = 0

    for item in hot:
        q = item["question"]
        # 获取已有缓存以避免重复查询
        if not QACache.get_cached_answer(0, q):
            # 标记为已预热（实际 RAG 环境会预计算答案）
            QACache.set_cached_answer(0, q, "[预热点] " + q)
            warmed += 1

    return _success(
        data={
            "warmed": warmed,
            "total_hot": len(hot),
            "limit": limit,
        },
        message=f"已预热 {warmed} 个热点问题",
    )


# ─── 管理后台页面 ─────────────────────────────────────


_html_path = Path(__file__).resolve().parent.parent / "static" / "admin.html"


@router.get("/ui/cache", response_class=HTMLResponse, include_in_schema=False)
def admin_dashboard(request: Request):
    """管理后台缓存面板页面"""
    if not _html_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard page not found")
    html_content = _html_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
