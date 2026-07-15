from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

QUESTION = "2026年9月全国计算机等级考试的报名时间是什么时候？"


def _require(response, expected: int, label: str) -> dict[str, object]:  # type: ignore[no-untyped-def]
    if response.status_code != expected:
        raise SystemExit(f"{label} 失败: HTTP {response.status_code} {response.text[:300]}")
    return response.json()


def main() -> None:
    password = settings.initial_admin_password.get_secret_value()
    if not password:
        raise SystemExit("INITIAL_ADMIN_PASSWORD 未配置，无法执行真实 API 冒烟测试")

    with TestClient(app) as client:
        health = _require(client.get("/api/health"), 200, "健康检查")
        if int(health["data"]["indexed_chunks"]) <= 0:  # type: ignore[index]
            raise SystemExit("健康检查显示 FAISS 知识库为空")
        spa = client.get("/chat")
        if spa.status_code != 200 or '<div id="root"></div>' not in spa.text:
            raise SystemExit(f"React SPA 路由失败: HTTP {spa.status_code}")
        login = _require(
            client.post(
                "/api/auth/login",
                json={"email": settings.initial_admin_email, "password": password},
            ),
            200,
            "管理员登录",
        )
        token = str(login["data"]["access_token"])  # type: ignore[index]
        headers = {"Authorization": f"Bearer {token}"}
        listing = _require(
            client.get("/api/documents?size=1", headers=headers), 200, "知识库列表"
        )
        total = int(listing["data"]["total"])  # type: ignore[index]

        completed = _require(
            client.post("/api/chat", headers=headers, json={"question": QUESTION}),
            200,
            "同步问答",
        )
        result = completed["data"]  # type: ignore[index]
        sources = result["sources"]  # type: ignore[index]
        if not sources:
            raise SystemExit("同步问答未返回知识库引用")

        events: list[str] = []
        with client.stream(
            "POST", "/api/chat/stream", headers=headers, json={"question": QUESTION}
        ) as response:
            if response.status_code != 200:
                raise SystemExit(f"SSE 问答失败: HTTP {response.status_code}")
            for line in response.iter_lines():
                if line.startswith("event: "):
                    events.append(line.removeprefix("event: "))
                elif line.startswith("data: ") and events and events[-1] == "error":
                    payload = json.loads(line.removeprefix("data: "))
                    raise SystemExit(f"SSE 问答错误: {payload.get('message')}")
        required_events = {"start", "sources", "delta", "done"}
        if not required_events.issubset(events):
            raise SystemExit(f"SSE 事件不完整: {events}")

        first_source = sources[0]  # type: ignore[index]
        print("real_api_smoke=ok")
        print(f"knowledge_documents={total}")
        print(f"source_title={first_source['title']}")
        print(f"source_url={first_source.get('source_url') or '(none)'}")
        print(f"answer_excerpt={str(result['answer'])[:160]}")
        print(f"sse_events={','.join(events)}")


if __name__ == "__main__":
    main()
