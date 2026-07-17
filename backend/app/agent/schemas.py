from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolDef:
    """OpenAI-compatible tool definition with helper for serialization."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    """A single tool invocation request from the LLM."""

    tool_call_id: str = field(default_factory=lambda: f"call_{uuid.uuid4().hex[:12]}")
    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """The result of executing a tool."""

    tool_call_id: str = ""
    tool_name: str = ""
    success: bool = True
    summary: str = ""
    data: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass
class AgentContext:
    """Holds state across agent loop iterations."""

    question: str
    history: list[dict[str, str]]
    messages: list[dict[str, Any]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 3
    sources: list[dict[str, Any]] = field(default_factory=list)
    web_sources: list[dict[str, Any]] = field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = field(default_factory=list)
    seen_urls: set[str] = field(default_factory=set)


AgentStepType = Literal["tool_call", "tool_result"]
AgentStepStatus = Literal["running", "success", "error"]


@dataclass
class AgentStepEvent:
    """An SSE event emitted for each agent step."""

    type: AgentStepType
    tool_name: str
    tool_call_id: str = ""
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    status: AgentStepStatus = "success"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "type": self.type,
            "tool_name": self.tool_name,
            "status": self.status,
        }
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.args is not None:
            d["args"] = self.args
        if self.result is not None:
            d["result"] = self.result
        return d
