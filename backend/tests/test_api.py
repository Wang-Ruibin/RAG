from __future__ import annotations

from datetime import date

import pytest
from app.core.database import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models.enums import MessageStatus, Role
from app.models.orm import Message, User
from app.rag.generation import generator
from app.rag.retrieval import RetrievalResult
from app.services.answer_knowledge import answer_knowledge_service
from app.services.chat import chat_service
from app.services.web_search import WebSearchResult
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def register(client: AsyncClient, email: str = "student@example.com") -> dict[str, object]:
    response = await client.post(
        "/api/auth/register",
        json={"name": "测试学生", "email": email, "password": "safe-pass-123"},
    )
    assert response.status_code == 201
    return response.json()["data"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_health_checks_business_database(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["data"]["database"] == "ok"


async def test_register_login_and_admin_boundary(client: AsyncClient) -> None:
    registered = await register(client)
    token = str(registered["access_token"])

    me = await client.get("/api/auth/me", headers=auth_header(token))
    assert me.status_code == 200
    assert me.json()["data"]["role"] == "STUDENT"

    forbidden = await client.get("/api/admin/users", headers=auth_header(token))
    assert forbidden.status_code == 403
    assert forbidden.json()["message"] == "需要管理员权限"

    login = await client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "safe-pass-123"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["token_type"] == "bearer"


async def test_admin_cannot_deactivate_self(client: AsyncClient) -> None:
    with SessionLocal() as db:
        admin = User(
            name="管理员",
            email="admin@example.com",
            password_hash=hash_password("admin-pass-123"),
            role=Role.ADMIN,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        admin_id = admin.id

    token = create_access_token(admin_id, Role.ADMIN.value)
    response = await client.patch(
        f"/api/admin/users/{admin_id}",
        headers=auth_header(token),
        json={"is_active": False},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "不能停用当前管理员"


async def test_grounded_chat_persists_citations_and_enforces_ownership(
    client: AsyncClient, monkeypatch
) -> None:
    first = await register(client)
    first_header = auth_header(str(first["access_token"]))
    result = RetrievalResult(
        chunk_id=11,
        document_id=7,
        title="校园卡办理指南",
        content="校园卡补办需要携带有效身份证件。",
        source_url="https://example.edu.cn/card",
        published_at=date(2026, 1, 1),
        score=0.93,
    )
    monkeypatch.setattr(chat_service, "retrieve", lambda _question, _history: (_question, [result]))
    monkeypatch.setattr(
        chat_service,
        "search_web",
        lambda _query: pytest.fail("web search should not be called for valid local context"),
    )
    monkeypatch.setattr(
        generator,
        "complete",
        lambda _question, _results: "请携带有效身份证件。[S1]",
    )

    response = await client.post(
        "/api/chat",
        headers=first_header,
        json={"question": "校园卡如何补办？"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer"].endswith("[S1]")
    assert data["answer_origin"] == "KNOWLEDGE_BASE"
    assert data["sources"][0]["source_url"] == "https://example.edu.cn/card"

    conversation = await client.get(
        f"/api/conversations/{data['conversation_id']}", headers=first_header
    )
    assert conversation.status_code == 200
    assert len(conversation.json()["data"]["messages"]) == 2

    monkeypatch.setattr(answer_knowledge_service, "submit", lambda _task_id: None)
    knowledge_task = await client.post(
        f"/api/messages/{data['message_id']}/knowledge-task",
        headers=first_header,
    )
    assert knowledge_task.status_code == 202
    task_data = knowledge_task.json()["data"]
    assert task_data["assistant_message_id"] == data["message_id"]
    assert task_data["status"] == "QUEUED"

    duplicate_task = await client.post(
        f"/api/messages/{data['message_id']}/knowledge-task",
        headers=first_header,
    )
    assert duplicate_task.status_code == 202
    assert duplicate_task.json()["data"]["id"] == task_data["id"]

    conversation_with_task = await client.get(
        f"/api/conversations/{data['conversation_id']}", headers=first_header
    )
    assistant_message = conversation_with_task.json()["data"]["messages"][1]
    assert assistant_message["knowledge_task"]["id"] == task_data["id"]

    second = await register(client, "other@example.com")
    unauthorized = await client.get(
        f"/api/conversations/{data['conversation_id']}",
        headers=auth_header(str(second["access_token"])),
    )
    assert unauthorized.status_code == 404
    forbidden_task = await client.post(
        f"/api/messages/{data['message_id']}/knowledge-task",
        headers=auth_header(str(second["access_token"])),
    )
    assert forbidden_task.status_code == 404


async def test_stream_chat_emits_protocol_and_persists_complete_message(
    client: AsyncClient, monkeypatch
) -> None:
    registered = await register(client, "stream@example.com")
    header = auth_header(str(registered["access_token"]))
    result = RetrievalResult(
        chunk_id=21,
        document_id=9,
        title="计算机等级考试报名通知",
        content="报名时间为6月25日至7月15日。",
        source_url="https://example.edu.cn/ncre",
        published_at=date(2026, 6, 24),
        score=0.95,
    )
    weak_result = RetrievalResult(
        chunk_id=22,
        document_id=10,
        title="无关资料",
        content="与问题无关的正文。",
        source_url=None,
        published_at=None,
        score=0.50,
    )
    monkeypatch.setattr(
        chat_service, "retrieve", lambda question, _history: (question, [result, weak_result])
    )
    generation_context: list[RetrievalResult] = []

    def fake_stream(_question, results):
        generation_context.extend(results)
        return iter(["报名时间", "见通知。[S1]"])

    monkeypatch.setattr(generator, "stream", fake_stream)

    response = await client.post(
        "/api/chat/stream",
        headers=header,
        json={"question": "计算机等级考试何时报名？"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: start" in response.text
    assert response.text.count("event: status") == 2
    assert response.text.count("event: sources") == 1
    assert '"final": true' in response.text
    assert response.text.count("event: delta") == 2
    assert "event: done" in response.text
    assert generation_context == [result]
    assert "无关资料" not in response.text
    with SessionLocal() as db:
        assistant = db.query(Message).order_by(Message.id.desc()).first()
        assert assistant is not None
        assert assistant.status == MessageStatus.COMPLETE
        assert assistant.content == "报名时间见通知。[S1]"
        assert assistant.sources_json[0]["chunk_id"] == 21


async def test_stream_chat_uses_mocked_baidu_web_search(client: AsyncClient, monkeypatch) -> None:
    registered = await register(client, "stream-web@example.com")
    header = auth_header(str(registered["access_token"]))
    monkeypatch.setattr(chat_service, "retrieve", lambda question, _history: (question, []))
    web_result = WebSearchResult(
        title="河海大学通知",
        url="https://www.hhu.edu.cn/news",
        snippet="河海大学官网发布了通知。",
        content="河海大学官网发布了通知。",
        site_name="河海大学",
        domain="www.hhu.edu.cn",
        published_at=date(2026, 7, 2),
        citation_index=1,
    )
    monkeypatch.setattr(chat_service, "search_web", lambda _query: [web_result])
    monkeypatch.setattr(
        generator,
        "stream_web",
        lambda _question, _results: iter(["官网通知", "。[W1]"]),
    )

    response = await client.post(
        "/api/chat/stream",
        headers=header,
        json={"question": "河海大学最近有什么通知？"},
    )

    assert response.status_code == 200
    assert response.text.count("event: status") == 3
    assert '"answer_origin": "WEB_SEARCH"' in response.text
    assert '"source_type": "WEB_SEARCH"' in response.text
    assert "event: done" in response.text
    with SessionLocal() as db:
        assistant = db.query(Message).order_by(Message.id.desc()).first()
        assert assistant is not None
        assert assistant.answer_origin == "WEB_SEARCH"
        assert assistant.sources_json[0]["url"] == "https://www.hhu.edu.cn/news"


async def test_low_confidence_question_is_refused_without_calling_llm(
    client: AsyncClient, monkeypatch
) -> None:
    registered = await register(client, "refusal@example.com")
    header = auth_header(str(registered["access_token"]))
    monkeypatch.setattr(chat_service, "retrieve", lambda question, _history: (question, []))

    response = await client.post(
        "/api/chat",
        headers=header,
        json={"question": "火星校区宿舍何时开放？"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "暂未找到足够相关的信息" in data["answer"]
    assert data["answer_origin"] == "NO_ANSWER"
    assert data["sources"] == []


async def test_low_confidence_question_uses_mocked_baidu_web_search(
    client: AsyncClient, monkeypatch
) -> None:
    registered = await register(client, "web@example.com")
    header = auth_header(str(registered["access_token"]))
    monkeypatch.setattr(chat_service, "retrieve", lambda question, _history: (question, []))
    web_result = WebSearchResult(
        title="河海大学校历",
        url="https://www.hhu.edu.cn/calendar",
        snippet="河海大学发布了新学期校历安排。",
        content="河海大学发布了新学期校历安排。",
        site_name="河海大学",
        domain="www.hhu.edu.cn",
        published_at=date(2026, 7, 1),
        citation_index=1,
    )
    monkeypatch.setattr(chat_service, "search_web", lambda _query: [web_result])
    monkeypatch.setattr(
        generator,
        "complete_web",
        lambda _question, _results: "以官网校历为准。[W1]",
    )

    response = await client.post(
        "/api/chat",
        headers=header,
        json={"question": "新学期校历什么时候发布？"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer_origin"] == "WEB_SEARCH"
    assert data["answer"].endswith("[W1]")
    assert data["sources"][0]["source_type"] == "WEB_SEARCH"
    assert data["sources"][0]["site_name"] == "河海大学"


async def test_stream_error_is_sanitized_and_persisted(client: AsyncClient, monkeypatch) -> None:
    registered = await register(client, "stream-error@example.com")
    header = auth_header(str(registered["access_token"]))
    result = RetrievalResult(
        chunk_id=31,
        document_id=12,
        title="测试通知",
        content="测试资料正文。",
        source_url=None,
        published_at=None,
        score=0.99,
    )
    monkeypatch.setattr(chat_service, "retrieve", lambda question, _history: (question, [result]))

    def broken_stream(_question, _results):
        raise RuntimeError("internal-sensitive-upstream-detail")

    monkeypatch.setattr(generator, "stream", broken_stream)
    response = await client.post(
        "/api/chat/stream",
        headers=header,
        json={"question": "测试流式异常？"},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert "回答生成失败，请稍后重试" in response.text
    assert "internal-sensitive-upstream-detail" not in response.text
    with SessionLocal() as db:
        assistant = db.query(Message).order_by(Message.id.desc()).first()
        assert assistant is not None
        assert assistant.status == MessageStatus.ERROR


async def test_empty_llm_stream_is_reported_as_error(client: AsyncClient, monkeypatch) -> None:
    registered = await register(client, "empty-stream@example.com")
    header = auth_header(str(registered["access_token"]))
    result = RetrievalResult(
        chunk_id=41,
        document_id=13,
        title="测试资料",
        content="测试资料正文。",
        source_url=None,
        published_at=None,
        score=0.99,
    )
    monkeypatch.setattr(chat_service, "retrieve", lambda question, _history: (question, [result]))
    monkeypatch.setattr(generator, "stream", lambda _question, _results: iter(()))

    response = await client.post(
        "/api/chat/stream",
        headers=header,
        json={"question": "测试空响应"},
    )

    assert "event: error" in response.text
    assert "event: done" not in response.text
    with SessionLocal() as db:
        assistant = db.query(Message).order_by(Message.id.desc()).first()
        assert assistant is not None
        assert assistant.status == MessageStatus.ERROR
