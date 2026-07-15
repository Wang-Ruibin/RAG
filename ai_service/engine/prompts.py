"""
Prompt templates and formatting utilities for the RAG engine.

Provides the system prompt, context builder from retrieved chunks, prompt
assembler, answer formatter (for frontend display), and SSE helpers for
streaming responses.

All functions are pure string/dict manipulation — no API calls, no imports
beyond the standard library.
"""

from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "你是一个河海大学校园知识问答助手。你的职责是：\n"
    "1. 根据提供的参考资料准确回答用户关于河海大学的问题\n"
    "2. 在回答中标注引用来源，格式为 [1][2][3]\n"
    '3. 如果参考资料不足以回答问题，请如实说明"未找到相关信息"，不要编造\n'
    "4. 回答简洁、准确、专业\n"
    "5. 用中文回答"
)

# ---------------------------------------------------------------------------
# Context & prompt builders
# ---------------------------------------------------------------------------


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered reference string.

    Parameters
    ----------
    chunks : list[dict]
        Each dict must contain at least the keys ``content`` and ``title``.

    Returns
    -------
    str
        Formatted context, e.g.::

            [1] 河海大学成立于1915年...
            （来源：学校简介）

            [2] 学校现有教职工...
            （来源：学校概况）
    """
    if not chunks:
        return ""

    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        content = chunk.get("content", "")
        title = chunk.get("title", "")
        parts.append(f"[{i}] {content}\n（来源：{title}）")

    return "\n\n".join(parts)


def build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]:
    """Assemble the full (system_prompt, user_prompt) pair for the LLM.

    Parameters
    ----------
    query : str
        The user's original question.
    chunks : list[dict]
        Retrieved chunks (same format as ``build_context``).

    Returns
    -------
    tuple[str, str]
        ``(system_prompt, user_prompt)`` — ready to pass to the LLM chat
        completion call.
    """
    context = build_context(chunks)
    user_prompt = f"参考资料：\n{context}\n\n用户问题：{query}"
    return SYSTEM_PROMPT, user_prompt


# ---------------------------------------------------------------------------
# Answer formatter (for frontend display)
# ---------------------------------------------------------------------------


def format_answer(answer: str, chunks: list[dict]) -> dict[str, Any]:
    """Wrap the LLM answer with structured source metadata.

    Parameters
    ----------
    answer : str
        The raw text returned by the LLM.
    chunks : list[dict]
        Retrieved chunks (same format as ``build_context``).  Each dict
        should contain ``title``, ``content``, and (optionally) ``score``.

    Returns
    -------
    dict
        ``{"answer": <str>, "sources": [{"title": ..., "content_preview": ..., "score": ...}, ...]}``
    """
    sources: list[dict[str, Any]] = []
    for chunk in chunks:
        content = chunk.get("content", "")
        sources.append({
            "title": chunk.get("title", ""),
            "content_preview": content[:100],
            "score": chunk.get("score", 0.0),
        })

    return {
        "answer": answer,
        "sources": sources,
    }


# ---------------------------------------------------------------------------
# SSE (Server-Sent Events) helpers for streaming responses
# ---------------------------------------------------------------------------

CHUNK_TEMPLATE = "data: {json}\n"


def format_sse_event(event: str, data: dict) -> str:
    """Format a dict as an SSE event string.

    Parameters
    ----------
    event : str
        Event type name (e.g. ``"token"``, ``"done"``, ``"error"``).
    data : dict
        Payload to serialize as JSON.

    Returns
    -------
    str
        SSE-formatted string::

            event: token
            data: {"text": "河海"}
    """
    serialized = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\n{CHUNK_TEMPLATE.format(json=serialized)}\n"
