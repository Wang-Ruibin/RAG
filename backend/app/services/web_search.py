from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


@dataclass
class WebSearchItem:
    title: str = ""
    url: str = ""
    snippet: str = ""


@dataclass
class WebSearchResult:
    success: bool = True
    summary: str = ""
    items: list[WebSearchItem] = field(default_factory=list)
    error: str | None = None


class WebSearchService:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=15.0)
        return self._client

    def search_sync(self, query: str) -> WebSearchResult:
        if settings.web_search_provider == "bing":
            return self._search_bing(query)
        if settings.web_search_provider == "duckduckgo":
            return self._search_duckduckgo(query)
        return self._search_bing_html(query)

    def _search_bing(self, query: str) -> WebSearchResult:
        api_key = settings.web_search_api_key.get_secret_value()
        if not api_key:
            return WebSearchResult(success=False, error="Bing API Key 未配置")
        try:
            response = self._get_client().get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={
                    "q": query,
                    "count": settings.web_search_max_results,
                    "mkt": "zh-CN",
                },
                headers={"Ocp-Apim-Subscription-Key": api_key},
            )
            response.raise_for_status()
            data = response.json()
            web_pages = data.get("webPages", {}).get("value", [])
            items = [
                WebSearchItem(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                )
                for item in web_pages
            ]
            return WebSearchResult(
                success=True, summary=f"找到 {len(items)} 条结果", items=items
            )
        except Exception as exc:
            logger.exception("Bing search failed")
            return WebSearchResult(success=False, error=f"Bing 搜索失败: {exc}")

    def _search_duckduckgo(self, query: str) -> WebSearchResult:
        try:
            response = self._get_client().get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                },
            )
            response.raise_for_status()
            data = response.json()
            items: list[WebSearchItem] = []
            abstract = data.get("AbstractText", "")
            if abstract:
                items.append(
                    WebSearchItem(
                        title=data.get("Heading", "摘要"),
                        url=data.get("AbstractURL", ""),
                        snippet=abstract,
                    )
                )
            for topic in data.get("RelatedTopics", []):
                if len(items) >= settings.web_search_max_results:
                    break
                if "Topics" in topic:
                    for sub in topic["Topics"]:
                        if len(items) >= settings.web_search_max_results:
                            break
                        items.append(
                            WebSearchItem(
                                title=sub.get("Text", "")[:80],
                                url=sub.get("FirstURL", ""),
                                snippet=sub.get("Text", ""),
                            )
                        )
                else:
                    items.append(
                        WebSearchItem(
                            title=topic.get("Text", "")[:80],
                            url=topic.get("FirstURL", ""),
                            snippet=topic.get("Text", ""),
                        )
                    )
            return WebSearchResult(
                success=True, summary=f"找到 {len(items)} 条结果", items=items
            )
        except Exception as exc:
            logger.exception("DuckDuckGo search failed")
            return WebSearchResult(success=False, error=f"联网搜索失败: {exc}")

    def _search_bing_html(self, query: str) -> WebSearchResult:
        # Domains never useful for campus activity info
        low_value_domains = {
            "yz.chsi.com.cn", "baike.baidu.com", "huodongxing.com",
            "eventwang.cn", "xiaoyuanyou.cn", "huodong.com",
        }

        try:
            response = self._get_client().get(
                "https://www.bing.com/search",
                params={
                    "q": query,
                    "count": settings.web_search_max_results,
                    "mkt": "zh-CN",
                },
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                follow_redirects=True,
            )
            response.raise_for_status()

            text = html.unescape(response.text)
            items: list[WebSearchItem] = []
            domain_count: dict[str, int] = {}
            blocks = re.findall(
                r'<li class="b_algo"[^>]*>(.*?)</li>', text, re.DOTALL
            )
            for block in blocks:
                link_match = re.search(
                    r'<h2[^>]*>.*?<a[^>]*href="(.*?)"[^>]*>(.*?)</a>',
                    block,
                    re.DOTALL,
                )
                snippet_match = re.search(
                    r'<p[^>]*>(.*?)</p>', block, re.DOTALL
                )
                if not link_match:
                    continue

                url = link_match.group(1)
                domain = urlparse(url).hostname or ""
                # Strip www. prefix for consistent matching
                domain_key = domain.removeprefix("www.") if domain else ""

                # Skip low-value domains
                if domain_key in low_value_domains:
                    continue
                # Max 2 per domain
                if domain_count.get(domain_key, 0) >= 2:
                    continue

                title = re.sub(r"<.*?>", "", link_match.group(2)).strip()
                snippet = ""
                if snippet_match:
                    snippet = re.sub(r"<.*?>", "", snippet_match.group(1)).strip()

                domain_count[domain_key] = domain_count.get(domain_key, 0) + 1
                items.append(
                    WebSearchItem(title=title, url=url, snippet=snippet)
                )

                if len(items) >= settings.web_search_max_results:
                    break

            return WebSearchResult(
                success=True,
                summary=(
                    f"找到 {len(items)} 条结果"
                    if items
                    else "未找到相关结果"
                ),
                items=items,
            )
        except Exception as exc:
            logger.exception("Bing HTML search failed")
            return WebSearchResult(
                success=False, error=f"联网搜索失败: {exc}"
            )


web_search_service = WebSearchService()
