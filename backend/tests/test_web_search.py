from __future__ import annotations

import json

import httpx
import pytest
from app.services.web_search import (
    BaiduWebSearchProvider,
    FreeWebSearchProvider,
    WebSearchError,
    WebSearchErrorKind,
)
from ddgs.exceptions import RatelimitException, TimeoutException
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
    monkeypatch.setattr("app.services.web_search.settings.baidu_search_safe_search", True)
    monkeypatch.setattr(
        "app.services.web_search.settings.baidu_search_match_site",
        "www.hhu.edu.cn",
    )
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
    assert payload["safe_search"] is True
    assert payload["search_filter"] == {"match": {"site": ["www.hhu.edu.cn"]}}


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


def test_free_provider_needs_no_key_and_normalizes_results(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeDDGS:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        def text(self, query: str, **kwargs):
            captured["query"] = query
            captured["kwargs"] = kwargs
            return [
                {
                    "title": " 河海大学通知 ",
                    "href": "https://WWW.HHU.EDU.CN/news#top",
                    "body": " 官网发布的最新通知。 ",
                },
                {
                    "title": "重复来源",
                    "href": "https://www.hhu.edu.cn/news",
                    "body": "重复内容",
                },
                {"title": "非法链接", "href": "javascript:alert(1)", "body": "忽略"},
            ]

    monkeypatch.setattr("app.services.web_search.DDGS", FakeDDGS)
    provider = FreeWebSearchProvider()

    results = provider.search("河海大学最近通知")

    assert len(results) == 1
    assert results[0].title == "河海大学通知"
    assert results[0].url == "https://www.hhu.edu.cn/news"
    assert results[0].citation_index == 1
    assert captured["timeout"] == 15
    assert captured["query"] == "河海大学最近通知"
    assert captured["kwargs"] == {
        "region": "cn-zh",
        "safesearch": "moderate",
        "timelimit": None,
        "max_results": 5,
        "backend": "auto",
    }


@pytest.mark.parametrize(
    ("exception", "kind"),
    [
        (TimeoutException("timeout"), WebSearchErrorKind.TIMEOUT),
        (RatelimitException("limited"), WebSearchErrorKind.QUOTA),
    ],
)
def test_free_provider_classifies_errors(monkeypatch, exception, kind) -> None:
    class FailingDDGS:
        def __init__(self, **_kwargs) -> None:
            pass

        def text(self, _query: str, **_kwargs):
            raise exception

    monkeypatch.setattr("app.services.web_search.DDGS", FailingDDGS)

    with pytest.raises(WebSearchError) as exc_info:
        FreeWebSearchProvider().search("query")

    assert exc_info.value.kind == kind
