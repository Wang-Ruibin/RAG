from __future__ import annotations

import json

import httpx
import pytest
from app.services.web_search import BaiduWebSearchProvider, WebSearchError, WebSearchErrorKind
from pydantic import SecretStr


def provider_with_response(monkeypatch, response: httpx.Response) -> BaiduWebSearchProvider:
    monkeypatch.setattr(
        "app.services.web_search.settings.baidu_search_api_key",
        SecretStr("test-key"),
    )
    provider = BaiduWebSearchProvider()
    transport = httpx.MockTransport(lambda _request: response)
    provider._client = httpx.Client(transport=transport)
    return provider


def test_baidu_provider_normalizes_and_filters_results(monkeypatch) -> None:
    provider = provider_with_response(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "references": [
                    {
                        "type": "web",
                        "title": " 河海大学通知 ",
                        "url": "https://WWW.HHU.EDU.CN/news?id=1#top",
                        "website": "河海大学",
                        "snippet": " 官网发布通知 ",
                        "content": "官网发布通知正文",
                        "date": "2026-07-01",
                    },
                    {
                        "type": "web",
                        "title": "重复",
                        "url": "https://www.hhu.edu.cn/news?id=1",
                        "snippet": "重复内容",
                    },
                    {"type": "image", "url": "https://www.hhu.edu.cn/a.jpg", "snippet": "图片"},
                    {"type": "web", "url": "javascript:alert(1)", "snippet": "非法链接"},
                    {"type": "web", "url": "https://www.hhu.edu.cn/empty", "snippet": ""},
                ]
            },
        ),
    )

    results = provider.search("河海大学通知")

    assert len(results) == 1
    assert results[0].citation_index == 1
    assert results[0].title == "河海大学通知"
    assert results[0].url == "https://www.hhu.edu.cn/news?id=1"
    assert results[0].site_name == "河海大学"
    assert results[0].published_at is not None


def test_baidu_provider_uses_official_request_shape(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        captured["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"references": []})

    monkeypatch.setattr(
        "app.services.web_search.settings.baidu_search_api_key",
        SecretStr("test-key"),
    )
    monkeypatch.setattr(
        "app.services.web_search.settings.baidu_search_auth_header",
        "X-Appbuilder-Authorization",
    )
    monkeypatch.setattr("app.services.web_search.settings.baidu_search_max_results", 3)
    provider = BaiduWebSearchProvider()
    provider._client = httpx.Client(transport=httpx.MockTransport(handle))

    assert provider.search("河海大学校历") == []

    request = captured["request"]
    assert isinstance(request, httpx.Request)
    assert request.method == "POST"
    assert request.url.path == "/v2/ai_search/web_search"
    assert request.headers["X-Appbuilder-Authorization"] == "Bearer test-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["messages"] == [{"role": "user", "content": "河海大学校历"}]
    assert payload["search_source"] == "baidu_search_v2"
    assert payload["resource_type_filter"] == [{"type": "web", "top_k": 3}]


@pytest.mark.parametrize(
    ("status_code", "kind"),
    [
        (401, WebSearchErrorKind.AUTHENTICATION),
        (403, WebSearchErrorKind.AUTHENTICATION),
        (429, WebSearchErrorKind.QUOTA),
        (500, WebSearchErrorKind.SERVICE),
    ],
)
def test_baidu_provider_classifies_http_errors(monkeypatch, status_code, kind) -> None:
    provider = provider_with_response(monkeypatch, httpx.Response(status_code, json={}))

    with pytest.raises(WebSearchError) as exc_info:
        provider.search("query")

    assert exc_info.value.kind == kind


def test_baidu_provider_classifies_payload_quota_error(monkeypatch) -> None:
    provider = provider_with_response(
        monkeypatch,
        httpx.Response(200, json={"code": "LimitExceeded", "message": "配额不足"}),
    )

    with pytest.raises(WebSearchError) as exc_info:
        provider.search("query")

    assert exc_info.value.kind == WebSearchErrorKind.QUOTA


def test_baidu_provider_handles_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.web_search.settings.baidu_search_api_key",
        SecretStr("test-key"),
    )
    provider = BaiduWebSearchProvider()

    def raise_timeout(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    provider._client = httpx.Client(transport=httpx.MockTransport(raise_timeout))

    with pytest.raises(WebSearchError) as exc_info:
        provider.search("query")

    assert exc_info.value.kind == WebSearchErrorKind.TIMEOUT


def test_baidu_provider_returns_empty_results(monkeypatch) -> None:
    provider = provider_with_response(monkeypatch, httpx.Response(200, json={"references": []}))

    assert provider.search("query") == []
