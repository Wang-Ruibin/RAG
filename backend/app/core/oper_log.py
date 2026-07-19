"""操作日志中间件：把 Python 侧的写操作记入 Java 共用的 sys_oper_log 表。

Java 微服务用 LogAspect（Spring AOP）记录操作日志；/qa、/knowledge 走网关直达
Python 后，这些操作绕过了 Java 切面。本中间件补齐这一段：命中规则表的写请求
（POST/PATCH/DELETE）落库到同一张 sys_oper_log，系统日志页面无需任何改动。

实现为纯 ASGI 中间件：对 receive/send 做旁路 tee，不消费、不重放请求体，
对 SSE 流式响应零干扰（BaseHTTPMiddleware 读 body 会破坏下游解析，勿改回）。

只记写操作，GET 查询一律不记，避免日志噪音。
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger("uvicorn.error")

_PARAM_MAX_CHARS = 2000
_RESULT_MAX_CHARS = 2000
_BODY_CAPTURE_LIMIT = 64 * 1024  # 超过 64KB 的请求体不进日志（如文件上传）

# 提问路径单独成常量：访客无痕跳过与 _RULES 复用同一正则，避免双份漂移
_CHAT_PATH = re.compile(r"^/api/chat(/stream)?$")

# (请求方法, 路径正则, 模块标题, business_type: 0其它 1新增 2修改 3删除)
_RULES: list[tuple[str, re.Pattern[str], str, int]] = [
    ("POST", re.compile(r"^/api/documents$"), "知识库-文档上传", 1),
    ("PATCH", re.compile(r"^/api/documents/\d+$"), "知识库-文档编辑", 2),
    ("DELETE", re.compile(r"^/api/documents/\d+$"), "知识库-文档删除", 3),
    ("POST", re.compile(r"^/api/documents/\d+/reindex$"), "知识库-重建索引", 2),
    ("POST", _CHAT_PATH, "智能问答-提问", 0),
    ("DELETE", re.compile(r"^/api/conversations/\d+$"), "智能问答-删除会话", 3),
    ("POST", re.compile(r"^/api/messages/\d+/knowledge-task$"), "智能问答-答案沉淀", 1),
    ("POST", re.compile(r"^/api/messages/\d+/correction$"), "智能问答-提交纠错", 1),
    ("POST", re.compile(r"^/api/admin/answer-corrections/\d+/approve$"), "纠错审核-通过", 2),
    ("POST", re.compile(r"^/api/admin/answer-corrections/\d+/reject$"), "纠错审核-拒绝", 2),
]

_INSERT_SQL = text(
    "INSERT INTO sys_oper_log "
    "(title, business_type, method, request_method, oper_url, oper_ip, "
    " oper_param, json_result, status, error_msg, oper_name, cost_time) "
    "VALUES (:title, :business_type, :method, :request_method, :oper_url, :oper_ip, "
    " :oper_param, :json_result, :status, :error_msg, :oper_name, :cost_time)"
)


def _match_rule(method: str, path: str) -> tuple[str, int] | None:
    for rule_method, pattern, title, business_type in _RULES:
        if method == rule_method and pattern.match(path):
            return title, business_type
    return None


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else f"{value[:limit]}..."


def _normalize_ip(ip: str) -> str:
    """IPv6 回环/IPv4 映射地址归一化，与 Java 侧 LogAspect 的记录格式对齐。"""
    ip = ip.strip()
    if ip in ("::1", "0:0:0:0:0:0:0:1"):
        return "127.0.0.1"
    if ip.startswith("::ffff:"):
        return ip[7:]
    return ip


def _extract_error_msg(body_text: str) -> str | None:
    try:
        payload = json.loads(body_text)
    except (ValueError, TypeError):
        return None
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("detail")
        return str(message) if message else None
    return None


def _insert_row(row: dict[str, object]) -> None:
    try:
        with SessionLocal() as db:
            db.execute(_INSERT_SQL, row)
            db.commit()
    except Exception:  # noqa: BLE001 — 日志失败绝不影响业务请求
        logger.warning("sys_oper_log 写入失败（表不存在或数据库不可用）", exc_info=True)


class OperLogMiddleware:
    """ASGI 层旁路记录：透传所有消息，只在旁边攒一份副本用于落库。"""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        self.app = app

    async def __call__(self, scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rule = _match_rule(scope["method"], scope["path"])
        if rule is None:
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        # 访客提问彻底无痕：直接透传，不 tee 不落库（仅豁免提问，其余规则照记，保留越权探测痕迹）。
        # 信任前提：/qa/** 必经网关，PythonTrustHeaderFilter 以覆盖语义注入 X-Login-Name，无法伪造。
        if _CHAT_PATH.match(scope["path"]) and headers.get("x-login-name") == settings.guest_login_name:
            await self.app(scope, receive, send)
            return
        content_type = headers.get("content-type", "")
        try:
            content_length = int(headers.get("content-length") or 0)
        except ValueError:
            content_length = 0
        capture_req = (
            content_type.startswith("application/json")
            and content_length <= _BODY_CAPTURE_LIMIT
        )
        req_chunks: list[bytes] = []

        async def receive_tee():  # type: ignore[no-untyped-def]
            message = await receive()
            if capture_req and message["type"] == "http.request":
                req_chunks.append(message.get("body", b""))
            return message

        status_code = 500
        capture_resp = False
        resp_chunks: list[bytes] = []

        async def send_tee(message) -> None:  # type: ignore[no-untyped-def]
            nonlocal status_code, capture_resp
            if message["type"] == "http.response.start":
                status_code = message["status"]
                resp_headers = {
                    k.decode("latin-1").lower(): v.decode("latin-1")
                    for k, v in message.get("headers", [])
                }
                # 只攒 JSON 响应；SSE(text/event-stream) 不读，零干扰
                capture_resp = resp_headers.get("content-type", "").startswith("application/json")
            elif message["type"] == "http.response.body" and capture_resp:
                resp_chunks.append(message.get("body", b""))
            await send(message)

        title, business_type = rule
        started = time.perf_counter()
        try:
            await self.app(scope, receive_tee, send_tee)
        finally:
            cost_time = int((time.perf_counter() - started) * 1000)
            if capture_req:
                oper_param = _truncate(
                    b"".join(req_chunks).decode("utf-8", errors="replace"), _PARAM_MAX_CHARS
                )
            else:
                oper_param = f"<{content_type or 'no content-type'}, {content_length} bytes>"
            query = scope.get("query_string", b"").decode("latin-1")
            if query:
                oper_param = f"query: {query}\n{oper_param}"

            json_result: str | None = None
            error_msg: str | None = None
            if resp_chunks:
                body_text = b"".join(resp_chunks).decode("utf-8", errors="replace")
                json_result = _truncate(body_text, _RESULT_MAX_CHARS)
                if status_code >= 400:
                    error_msg = _extract_error_msg(body_text)

            forwarded = headers.get("x-forwarded-for", "")
            client = scope.get("client")
            oper_ip = _normalize_ip(
                forwarded.split(",")[0] if forwarded else (client[0] if client else "")
            )

            row = {
                "title": title,
                "business_type": business_type,
                "method": f"python:{scope['method']} {scope['path']}",
                "request_method": scope["method"],
                "oper_url": scope["path"],
                "oper_ip": oper_ip,
                "oper_param": oper_param,
                "json_result": json_result,
                "status": 1 if status_code < 400 else 0,
                "error_msg": error_msg,
                "oper_name": headers.get("x-login-name") or "python-direct",
                "cost_time": cost_time,  # SSE 场景为完整流式时长（finally 在流结束后执行）
            }
            threading.Thread(target=_insert_row, args=(row,), daemon=True).start()
