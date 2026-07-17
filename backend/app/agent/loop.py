from __future__ import annotations

import concurrent.futures
import json
import logging
from collections.abc import Iterator

from app.agent.schemas import AgentContext, ToolResult
from app.agent.tools import TOOL_DISPATCH, get_tool_openai_defs
from app.core.config import settings
from app.rag.generation import AGENT_SYSTEM_PROMPT, generator, validate_all_citations

logger = logging.getLogger("uvicorn.error")


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def agent_loop(  # noqa: C901
    question: str,
    history: list[dict[str, str]],
    web_search_enabled: bool = True,
    max_iterations: int | None = None,
) -> Iterator[str]:
    """Agent loop: LLM thinks -> calls tools -> synthesises answer.

    Yields SSE-formatted event strings (agent_step, delta, sources, done).
    """
    ctx = AgentContext(
        question=question,
        history=history,
        max_iterations=max_iterations or settings.agent_max_iterations,
    )
    tools = get_tool_openai_defs(web_search_enabled=web_search_enabled)

    messages: list[dict] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
    ]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": question})

    for iteration in range(ctx.max_iterations):
        ctx.iteration = iteration + 1
        response = generator.chat_with_tools(messages, tools=tools, stream=False)

        if "tool_calls" in response:
            assistant_msg: dict = {
                "role": "assistant",
                "content": response.get("content") or None,
                "tool_calls": response["tool_calls"],
            }
            messages.append(assistant_msg)

            # Collect tool info
            tool_infos = []
            for tc in response["tool_calls"]:
                tool_name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    args = {}
                tool_infos.append((tc, tool_name, args))

            # Yield all tool_call events first (before any execution)
            for tc, tool_name, args in tool_infos:
                yield sse(
                    "agent_step",
                    {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "args": args,
                        "status": "running",
                        "iteration": ctx.iteration,
                    },
                )

            # Execute all tools in parallel
            def run_tool(
                tc_spec: dict, tc_args: dict
            ) -> tuple[dict, str, ToolResult]:
                tc_tool_name = tc_spec["function"]["name"]
                tc_handler = TOOL_DISPATCH.get(tc_tool_name)
                if tc_handler is None:
                    return (
                        tc_spec,
                        tc_tool_name,
                        ToolResult(
                            tool_name=tc_tool_name,
                            success=False,
                            error=f"未知工具: {tc_tool_name}",
                        ),
                    )
                return tc_spec, tc_tool_name, tc_handler(**tc_args)

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=len(tool_infos)
            ) as executor:
                future_map = {
                    executor.submit(run_tool, tc, args): (tc, tool_name, args)
                    for tc, tool_name, args in tool_infos
                }
                for future in concurrent.futures.as_completed(future_map):
                    tc, tool_name, args = future_map[future]
                    _, _, result = future.result()

                    yield sse(
                        "agent_step",
                        {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": {
                                "summary": result.summary,
                                "success": result.success,
                            },
                            "status": "success" if result.success else "error",
                            "iteration": ctx.iteration,
                        },
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": (
                                json.dumps(result.data, ensure_ascii=False)
                                if result.data
                                else result.summary
                            ),
                        }
                    )

                    # Collect sources for final output (deduplicated by URL)
                    if result.success and result.data:
                        for item in result.data:
                            source_url = str(
                                item.get("url", item.get("source_url", ""))
                            )
                            if source_url and source_url in ctx.seen_urls:
                                continue
                            if source_url:
                                ctx.seen_urls.add(source_url)
                            source: dict[str, object] = {
                                "title": item.get("title", ""),
                                "content": item.get("content", ""),
                                "url": source_url,
                            }
                            if tool_name == "knowledge_search":
                                source["type"] = "knowledge"
                                source["score"] = item.get("score", 0)
                                ctx.knowledge_sources.append(source)
                            else:
                                source["type"] = "web"
                                ctx.web_sources.append(source)

            continue

        # LLM returned text — final answer
        answer = response.get("content", "")
        if not answer.strip():
            answer = "抱歉，我无法生成有效的回答。"

        # Trim to at most 3 per source type
        ctx.knowledge_sources.sort(key=lambda s: s.get("score", 0), reverse=True)
        del ctx.knowledge_sources[3:]
        del ctx.web_sources[3:]

        s_count = len(ctx.knowledge_sources)
        w_count = len(ctx.web_sources)
        cleaned, cited_s, cited_w = validate_all_citations(answer, s_count, w_count)

        if not cited_s and not cited_w and (ctx.knowledge_sources or ctx.web_sources):
            if ctx.knowledge_sources:
                cleaned = f"{cleaned} [S1]"
            elif ctx.web_sources:
                cleaned = f"{cleaned} [W1]"

        final_sources: list[dict[str, object]] = []
        for i, src in enumerate(ctx.knowledge_sources, start=1):
            src["citation"] = f"S{i}"
            final_sources.append(src)
        for i, src in enumerate(ctx.web_sources, start=1):
            src["citation"] = f"W{i}"
            final_sources.append(src)

        yield sse("delta", {"text": cleaned})
        yield sse(
            "sources",
            {
                "items": final_sources,
                "low_confidence": False,
                "final": True,
            },
        )
        yield sse("done", {"model": settings.llm_model})
        return

    # Max iterations exceeded — force final answer from accumulated context
    force_messages = messages.copy()
    force_messages.append(
        {
            "role": "user",
            "content": "基于以上所有信息，请给出最终回答。如果信息不足，如实告知。",
        }
    )
    response = generator.chat_with_tools(force_messages, tools=None, stream=False)
    answer = response.get("content", "") or "抱歉，经过多轮分析后仍无法生成完整回答。"

    # Trim to at most 3 per source type
    ctx.knowledge_sources.sort(key=lambda s: s.get("score", 0), reverse=True)
    del ctx.knowledge_sources[3:]
    del ctx.web_sources[3:]

    s_count = len(ctx.knowledge_sources)
    w_count = len(ctx.web_sources)
    cleaned, cited_s, cited_w = validate_all_citations(answer, s_count, w_count)

    final_sources: list[dict[str, object]] = []
    for i, src in enumerate(ctx.knowledge_sources, start=1):
        src["citation"] = f"S{i}"
        final_sources.append(src)
    for i, src in enumerate(ctx.web_sources, start=1):
        src["citation"] = f"W{i}"
        final_sources.append(src)

    yield sse("delta", {"text": cleaned})
    yield sse(
        "sources",
        {
            "items": final_sources,
            "low_confidence": False,
            "final": True,
        },
    )
    yield sse("done", {"model": settings.llm_model})
