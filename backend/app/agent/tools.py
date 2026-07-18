from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.agent.schemas import ToolDef, ToolResult

# ── Tool definitions (OpenAI function-calling format) ──────────────

KNOWLEDGE_SEARCH_TOOL = ToolDef(
    name="knowledge_search",
    description="搜索河海大学校园知识库，查找校史校训、院系专业、招生政策、校园设施、新闻通知等信息",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，建议使用简洁的核心词，如'校训'、'计算机专业录取分数'",
            }
        },
        "required": ["query"],
    },
)

WEB_SEARCH_TOOL = ToolDef(
    name="web_search",
    description="搜索互联网获取最新的校园相关信息，如招生简章、新闻公告、活动通知等时效性内容。搜索技巧：① 包含具体时间词（如'2026年'、'2026年7月'）② 查校园通知可加 site:my.hhu.edu.cn 缩小范围 ③ 多角度换词搜索（活动→通知→公告→新闻）④ 避免使用过于宽泛的关键词",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词。建议：包含时间词（如2026年），特定校园通知可加 site: 限定域名，用具体词汇替代宽泛词",
            }
        },
        "required": ["query"],
    },
)

# ── Tool execution ────────────────────────────────────────────────

KWSEP = "\n───\n"


def execute_knowledge_search(query: str) -> ToolResult:
    """Execute knowledge base search using the existing RAG retrieval pipeline."""
    from app.rag.retrieval import retrieval_service

    try:
        results = retrieval_service.search(query)
    except Exception as exc:
        return ToolResult(
            tool_name="knowledge_search",
            success=False,
            error=f"知识库搜索失败: {exc}",
        )

    if not results:
        return ToolResult(
            tool_name="knowledge_search",
            summary="知识库未找到相关信息",
            data=[],
        )

    items = []
    for r in results:
        items.append(
            {
                "document_id": r.document_id,
                "title": r.title,
                "score": round(r.score, 4),
                "content": r.content[:600],
                "source_url": r.source_url or "",
                "published_at": r.published_at.isoformat() if r.published_at else "",
            }
        )
    source_texts = "\n\n".join(
        f"[S{i+1}] {item['title']} (分数:{item['score']})\n{item['content'][:300]}"
        for i, item in enumerate(items)
    )
    return ToolResult(
        tool_name="knowledge_search",
        success=True,
        summary=f"知识库找到 {len(items)} 条相关结果",
        data=items,
    )


def execute_web_search(query: str) -> ToolResult:
    """Execute web search via the configured search provider."""
    from app.services.web_search import web_search_service

    # Extract site: filter if present (Bing often ignores it)
    site_filter = None
    clean_query = query
    site_match = re.search(r'\bsite:([a-z0-9.-]+)', query)
    if site_match:
        site_filter = site_match.group(1).removeprefix("www.")
        clean_query = re.sub(r'\s*site:[a-z0-9.-]+\s*', ' ', query).strip()

    try:
        result = web_search_service.search_sync(clean_query or query)
    except Exception as exc:
        return ToolResult(
            tool_name="web_search",
            success=False,
            error=f"联网搜索失败: {exc}",
        )
    if not result.success:
        return ToolResult(
            tool_name="web_search",
            success=False,
            error=result.error or "联网搜索失败",
        )
    items = [
        {
            "title": item.title,
            "url": item.url,
            "content": item.snippet,
        }
        for item in result.items
        if not site_filter or site_filter in (urlparse(item.url).hostname or "")
    ]
    return ToolResult(
        tool_name="web_search",
        success=True,
        summary=f"联网搜索找到 {len(items)} 条结果",
        data=items,
    )


TOOL_DEFINITIONS: list[ToolDef] = [KNOWLEDGE_SEARCH_TOOL, WEB_SEARCH_TOOL]


def get_tool_openai_defs(*, web_search_enabled: bool = True) -> list[dict[str, Any]]:
    """Return the OpenAI-format tool list, optionally omitting web_search."""
    defs = [KNOWLEDGE_SEARCH_TOOL.to_openai_tool()]
    if web_search_enabled:
        defs.append(WEB_SEARCH_TOOL.to_openai_tool())
    return defs


TOOL_DISPATCH: dict[str, callable] = {
    "knowledge_search": execute_knowledge_search,
    "web_search": execute_web_search,
}
