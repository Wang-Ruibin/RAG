from __future__ import annotations

from datetime import date

from app.core.config import settings
from app.rag.chunker import chunk_document
from app.rag.generation import validate_citations
from app.rag.parser import ParsedDocument, ParsedSection, parse_file
from app.rag.retrieval import RetrievalResult, RetrievalService, lexical_coverage
from app.services.chat import chat_service


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


def test_plain_text_parser_uses_business_title_instead_of_storage_uuid(tmp_path) -> None:
    path = tmp_path / "63e1ecb0ba0442b288597939124cf5e9.txt"
    path.write_text("1+1=2", encoding="utf-8")

    parsed = parse_file(path, fallback_title="计算题")
    chunks = chunk_document(parsed)

    assert parsed.title == "计算题"
    assert chunks[0].content == "计算题\n1+1=2"


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


def test_strong_hybrid_lexical_match_can_clear_a_borderline_score() -> None:
    content = "计算题\n1+1=2"
    coverage = lexical_coverage("1+1等于几", content)
    result = RetrievalResult(
        chunk_id=1,
        document_id=1028,
        title="计算题",
        content=content,
        source_url=None,
        published_at=None,
        score=0.71,
        dense_rank=1,
        sparse_rank=1,
        lexical_coverage=coverage,
    )

    assert coverage == 1.0
    assert not chat_service.is_low_confidence([result])


def test_weak_lexical_match_remains_low_confidence() -> None:
    result = RetrievalResult(
        chunk_id=2,
        document_id=99,
        title="无关资料",
        content="这是一段无关内容。",
        source_url=None,
        published_at=None,
        score=0.71,
        dense_rank=1,
        sparse_rank=1,
        lexical_coverage=0.0,
    )

    assert chat_service.is_low_confidence([result])


def test_relevant_context_keeps_multiple_strong_results_and_drops_weak_ones() -> None:
    def result(chunk_id: int, score: float) -> RetrievalResult:
        return RetrievalResult(
            chunk_id=chunk_id,
            document_id=chunk_id,
            title=f"资料{chunk_id}",
            content="相关资料",
            source_url=None,
            published_at=None,
            score=score,
        )

    selected = chat_service.relevant_context(
        [result(1, 0.81), result(2, 0.72), result(3, 0.59), result(4, 0.50)]
    )

    assert [item.chunk_id for item in selected] == [1, 2]


def test_grounded_answer_exposes_only_cited_context_sources() -> None:
    results = [
        RetrievalResult(1, 1, "资料1", "事实", None, None, 0.90),
        RetrievalResult(2, 2, "资料2", "补充事实", None, None, 0.82),
    ]

    answer, sources, cited = chat_service.grounded_answer("答案 [S1]", results)

    assert answer == "答案 [S1]"
    assert cited == [1]
    assert [source["citation_index"] for source in sources] == [1]


def test_retrieval_query_only_adds_history_for_context_dependent_followups() -> None:
    history = [
        {"role": "user", "content": "河海大学常州校区的地址是什么？"},
        {"role": "assistant", "content": "地址见资料。[S1]"},
    ]

    assert chat_service._retrieval_query("在哪里？", history) == (
        "河海大学常州校区的地址是什么？ 在哪里？"
    )
    assert chat_service._retrieval_query("做一下计算题", history) == "做一下计算题"


def test_retrieval_query_scopes_implicit_campus_subject_without_overwriting_other_school() -> None:
    assert chat_service._retrieval_query("校训", []) == "河海大学校训"
    assert chat_service._retrieval_query("北京大学校训", []) == "北京大学校训"


def test_citation_validation_removes_unknown_sources_and_deduplicates() -> None:
    cleaned, cited = validate_citations("事实一[S1]，错误来源[S9]，再次引用[S1]。", 2)

    assert cleaned == "事实一[S1]，错误来源，再次引用[S1]。"
    assert cited == [1]
