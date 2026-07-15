from __future__ import annotations

from datetime import date

from app.core.config import settings
from app.rag.chunker import chunk_document
from app.rag.generation import validate_citations
from app.rag.parser import ParsedDocument, ParsedSection, parse_file
from app.rag.retrieval import RetrievalService


def test_markdown_parser_extracts_metadata_and_removes_navigation(tmp_path) -> None:
    path = tmp_path / "notice.md"
    path.write_text(
        """# 测试通知

> 来源：https://example.edu.cn/notice/1
发布时间：2026-07-15

## 办理说明

请携带校园卡前往服务大厅。

上一篇：旧通知
下一篇：新通知
""",
        encoding="utf-8",
    )

    parsed = parse_file(path)

    assert parsed.title == "测试通知"
    assert parsed.source_url == "https://example.edu.cn/notice/1"
    assert parsed.published_at == date(2026, 7, 15)
    assert parsed.sections[0].heading_path == "测试通知 > 办理说明"
    assert "上一篇" not in parsed.sections[0].text


def test_chunker_keeps_title_path_and_overlap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "chunk_size", 80)
    monkeypatch.setattr(settings, "chunk_overlap", 12)
    text = "。".join(f"这是第{i}条校园办事说明" for i in range(30))
    parsed = ParsedDocument(
        title="校园办事指南",
        sections=[ParsedSection(text=text, heading_path="校园办事指南 > 流程")],
    )

    chunks = chunk_document(parsed)

    assert len(chunks) > 1
    assert [item.ordinal for item in chunks] == list(range(len(chunks)))
    assert all(item.content.startswith("校园办事指南\n校园办事指南 > 流程") for item in chunks)


def test_rrf_promotes_items_returned_by_both_retrievers() -> None:
    fused = RetrievalService._rrf(
        [(1, 0.8), (2, 0.7)],
        [(2, 5.0), (3, 4.0)],
    )

    assert [chunk_id for chunk_id, _score in fused] == [2, 1, 3]


def test_citation_validation_removes_unknown_sources_and_deduplicates() -> None:
    cleaned, cited = validate_citations("事实一[S1]，错误来源[S9]，再次引用[S1]。", 2)

    assert cleaned == "事实一[S1]，错误来源，再次引用[S1]。"
    assert cited == [1]
