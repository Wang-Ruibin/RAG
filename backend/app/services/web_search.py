from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx
from ddgs import DDGS
from ddgs.exceptions import DDGSException, RatelimitException, TimeoutException

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class WebSearchErrorKind(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    QUOTA = "QUOTA"
    TIMEOUT = "TIMEOUT"
    SERVICE = "SERVICE"
    CONFIGURATION = "CONFIGURATION"


class WebSearchError(RuntimeError):
    def __init__(self, kind: WebSearchErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


@dataclass(slots=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str
    content: str | None
    site_name: str | None
    domain: str
    published_at: date | None
    citation_index: int

    def source_dict(self) -> dict[str, object]:
        return {
            "source_type": "WEB_SEARCH",
            "citation_index": self.citation_index,
            "title": self.title,
            "url": self.url,
            "source_url": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "site_name": self.site_name,
            "domain": self.domain,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


class WebSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str) -> list[WebSearchResult]:
        raise NotImplementedError


class DisabledWebSearchProvider(WebSearchProvider):
    def search(self, query: str) -> list[WebSearchResult]:
        return []


class FreeWebSearchProvider(WebSearchProvider):
    def search(self, query: str) -> list[WebSearchResult]:
        try:
            references = DDGS(timeout=max(1, settings.free_search_timeout_seconds)).text(
                query,
                region=settings.free_search_region,
                safesearch=settings.free_search_safe_search,
                timelimit=settings.free_search_time_limit,
                max_results=max(1, min(settings.free_search_max_results, 20)),
                backend=settings.free_search_backend,
            )
        except TimeoutException as exc:
            raise WebSearchError(
                WebSearchErrorKind.TIMEOUT,
                "Free web search timed out",
            ) from exc
        except RatelimitException as exc:
            raise WebSearchError(
                WebSearchErrorKind.QUOTA,
                "Free web search was rate limited",
            ) from exc
        except DDGSException as exc:
            if "no results found" in str(exc).lower():
                return []
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Free web search request failed",
            ) from exc

        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        for item in references:
            if not isinstance(item, dict):
                continue
            url = _normalize_url(str(item.get("href") or item.get("url") or ""))
            if not url or url in seen_urls:
                continue
            snippet = _clean_text(str(item.get("body") or item.get("snippet") or ""))
            if not snippet:
                continue
            seen_urls.add(url)
            domain = urlparse(url).netloc.lower()
            title = _clean_text(str(item.get("title") or "")) or domain
            snippet = _limit_text(snippet, max(1, settings.web_search_snippet_max_chars))
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    content=snippet,
                    site_name=domain,
                    domain=domain,
                    published_at=None,
                    citation_index=len(results) + 1,
                )
            )
        return results[: settings.free_search_max_results]


class BaiduWebSearchProvider(WebSearchProvider):
    search_source = "baidu_search_v2"

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def search(self, query: str) -> list[WebSearchResult]:
        api_key, auth_header = self._credentials()
        response = self._post(query, api_key, auth_header)
        data = self._response_payload(response)
        return self._normalize_results(self._references(data))

    @staticmethod
    def _credentials() -> tuple[str, str]:
        api_key = settings.baidu_search_api_key.get_secret_value()
        if not api_key:
            raise WebSearchError(
                WebSearchErrorKind.CONFIGURATION,
                "BAIDU_SEARCH_API_KEY is empty",
            )
        auth_header = settings.baidu_search_auth_header.strip()
        if not auth_header:
            raise WebSearchError(
                WebSearchErrorKind.CONFIGURATION,
                "BAIDU_SEARCH_AUTH_HEADER is empty",
            )
        return api_key, auth_header

    def _post(self, query: str, api_key: str, auth_header: str) -> httpx.Response:
        try:
            response = self._get_client().post(
                self._url(),
                headers={auth_header: f"Bearer {api_key}"},
                json=self._payload(query),
            )
        except httpx.TimeoutException as exc:
            raise WebSearchError(
                WebSearchErrorKind.TIMEOUT,
                "Baidu web search timed out",
            ) from exc
        except httpx.HTTPError as exc:
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Baidu web search request failed",
            ) from exc
        self._raise_for_status(response)
        return response

    @staticmethod
    def _payload(query: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "messages": [{"role": "user", "content": query}],
            "search_source": BaiduWebSearchProvider.search_source,
            "resource_type_filter": [
                {"type": "web", "top_k": max(1, min(settings.baidu_search_max_results, 50))}
            ],
            "safe_search": settings.baidu_search_safe_search,
            "stream": False,
        }
        if settings.baidu_search_recency_filter:
            payload["search_recency_filter"] = settings.baidu_search_recency_filter
        if settings.baidu_search_match_site:
            payload["search_filter"] = {
                "match": {"site": [settings.baidu_search_match_site.strip()]}
            }
        blocked = [
            item.strip() for item in settings.baidu_search_block_websites.split(",") if item.strip()
        ]
        if blocked:
            payload["block_websites"] = blocked
        return payload

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise WebSearchError(
                WebSearchErrorKind.AUTHENTICATION,
                "Baidu web search auth failed",
            )
        if response.status_code == 429:
            raise WebSearchError(
                WebSearchErrorKind.QUOTA,
                "Baidu web search quota exceeded",
            )
        if response.status_code >= 500:
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Baidu web search service error",
            )
        if response.status_code >= 400:
            raise WebSearchError(
                BaiduWebSearchProvider._classify_error(response),
                f"Baidu web search returned HTTP {response.status_code}",
            )

    @classmethod
    def _response_payload(cls, response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError as exc:
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Baidu web search returned invalid JSON",
            ) from exc
        if not isinstance(data, dict):
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Baidu web search returned malformed JSON",
            )

        code = data.get("code")
        if code not in (None, 0, "0"):
            message = str(data.get("message") or "")
            raise WebSearchError(
                cls._classify_message(message),
                message or "Baidu web search error",
            )
        return data

    @staticmethod
    def _references(data: dict[str, Any]) -> list[Any]:
        references = data.get("references")
        if references is None and isinstance(data.get("data"), dict):
            references = data["data"].get("references")
        if references is None:
            return []
        if not isinstance(references, list):
            raise WebSearchError(
                WebSearchErrorKind.SERVICE,
                "Baidu web search references malformed",
            )
        return references

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            timeout = httpx.Timeout(
                connect=settings.baidu_search_timeout_connect_seconds,
                read=settings.baidu_search_timeout_read_seconds,
                write=settings.baidu_search_timeout_read_seconds,
                pool=settings.baidu_search_timeout_connect_seconds,
            )
            self._client = httpx.Client(timeout=timeout)
        return self._client

    @staticmethod
    def _url() -> str:
        base = settings.baidu_search_base_url.rstrip("/")
        path = "/" + settings.baidu_search_path.lstrip("/")
        return f"{base}{path}"

    @staticmethod
    def _classify_error(response: httpx.Response) -> WebSearchErrorKind:
        try:
            payload = response.json()
        except ValueError:
            return WebSearchErrorKind.SERVICE
        return BaiduWebSearchProvider._classify_message(str(payload.get("message") or ""))

    @staticmethod
    def _classify_message(message: str) -> WebSearchErrorKind:
        lowered = message.lower()
        if any(token in lowered for token in ("auth", "unauthorized", "permission", "api key")):
            return WebSearchErrorKind.AUTHENTICATION
        if any(token in message for token in ("额度", "配额", "欠费", "限额")) or any(
            token in lowered for token in ("quota", "rate limit", "qps")
        ):
            return WebSearchErrorKind.QUOTA
        return WebSearchErrorKind.SERVICE

    @staticmethod
    def _normalize_results(references: list[Any]) -> list[WebSearchResult]:
        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()
        for item in references:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "web") != "web":
                continue
            url = _normalize_url(str(item.get("url") or ""))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = _clean_text(str(item.get("title") or ""))
            snippet = _clean_text(str(item.get("snippet") or ""))
            content = _clean_text(str(item.get("content") or ""))
            if not snippet and content:
                snippet = content
            if not snippet:
                continue

            domain = urlparse(url).netloc.lower()
            site_name = _clean_text(str(item.get("website") or "")) or domain
            title = title or site_name or domain
            snippet = _limit_text(snippet, max(1, settings.web_search_snippet_max_chars))
            limited_content = (
                _limit_text(content, max(1, settings.web_search_content_max_chars))
                if content
                else None
            )
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    content=limited_content,
                    site_name=site_name,
                    domain=domain,
                    published_at=_parse_date(item.get("date")),
                    citation_index=len(results) + 1,
                )
            )
        return results[: settings.baidu_search_max_results]


def get_web_search_provider() -> WebSearchProvider:
    if not settings.web_search_enabled:
        return DisabledWebSearchProvider()
    if settings.web_search_provider == "free":
        return FreeWebSearchProvider()
    if settings.web_search_provider == "baidu":
        return BaiduWebSearchProvider()
    raise WebSearchError(
        WebSearchErrorKind.CONFIGURATION,
        f"Unsupported WEB_SEARCH_PROVIDER: {settings.web_search_provider}",
    )


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _limit_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars].rstrip()}..."


def _normalize_url(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            "",
            parsed.query,
            "",
        )
    )


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).strip()
    for candidate in (text, text[:10]):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None
