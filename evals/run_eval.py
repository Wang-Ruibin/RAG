from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.rag.generation import generator, validate_citations
from app.rag.index import index_manager
from app.rag.retrieval import RetrievalResult, retrieval_service


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number} 不是有效 JSON") from exc
    return cases


def is_gold(result: RetrievalResult, case: dict[str, Any]) -> bool:
    needles = case.get("gold_title_contains", [])
    if isinstance(needles, str):
        needles = [needles]
    return any(needle.lower() in result.title.lower() for needle in needles)


def choose_threshold(rows: list[dict[str, Any]]) -> dict[str, float]:
    scores = sorted({float(row["top_score"]) for row in rows})
    candidates = [-1.0, *scores, 1.000001]
    best: dict[str, float] | None = None
    for threshold in candidates:
        tp = fp = fn = 0
        outside = outside_accepted = 0
        for row in rows:
            predicted = float(row["top_score"]) >= threshold
            actual = bool(row["answerable"])
            if actual and predicted:
                tp += 1
            elif not actual and predicted:
                fp += 1
            elif actual and not predicted:
                fn += 1
            if not actual:
                outside += 1
                outside_accepted += int(predicted)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        false_accept_rate = outside_accepted / outside if outside else 0.0
        candidate = {
            "threshold": threshold,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "outside_false_accept_rate": false_accept_rate,
        }
        if false_accept_rate <= 0.10 and (
            best is None or (candidate["f1"], -threshold) > (best["f1"], -best["threshold"])
        ):
            best = candidate
    return best or {
        "threshold": 1.000001,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "outside_false_accept_rate": 0.0,
    }


def evaluate_case(case: dict[str, Any], with_generation: bool, mode: str) -> dict[str, Any]:
    query = case.get("standalone_question") or case["question"]
    started = time.perf_counter()
    results = retrieval_service.search(
        query,
        top_k=5,
        use_sparse=mode != "dense",
        use_rerank=mode == "hybrid-rerank",
    )
    retrieval_ms = round((time.perf_counter() - started) * 1000, 2)
    rank = next(
        (index for index, result in enumerate(results, start=1) if is_gold(result, case)),
        None,
    )
    row: dict[str, Any] = {
        "id": case["id"],
        "group": case["group"],
        "question": case["question"],
        "answerable": bool(case["answerable"]),
        "rank": rank,
        "hit_at_5": rank is not None,
        "reciprocal_rank": 1 / rank if rank else 0.0,
        "top_score": results[0].score if results else -1.0,
        "retrieval_ms": retrieval_ms,
        "retrieved_titles": [result.title for result in results],
    }
    if with_generation and case["answerable"] and results:
        answer = generator.complete(case["question"], results)
        cleaned, cited = validate_citations(answer, len(results))
        correct = sum(is_gold(results[index - 1], case) for index in cited)
        expected = case.get("expected_terms", [])
        row.update(
            {
                "answer": cleaned,
                "citation_count": len(cited),
                # This is intentionally a strict proxy: related supplemental sources can
                # support the answer but still not match the single curated gold title.
                "citation_gold_title_precision": correct / len(cited) if cited else 0.0,
                "expected_term_recall": (
                    sum(term.lower() in cleaned.lower() for term in expected) / len(expected)
                    if expected
                    else None
                ),
            }
        )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusQA 可重复检索与引用评测")
    parser.add_argument("--dataset", type=Path, default=Path("evals/campus_qa.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("docs/evaluation_report.json"))
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--with-generation", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("dense", "hybrid", "hybrid-rerank"),
        default="hybrid-rerank",
    )
    parser.add_argument("--rerank-candidates", type=int, default=None)
    parser.add_argument("--reranker-max-length", type=int, default=None)
    args = parser.parse_args()

    if args.rerank_candidates is not None:
        settings.rerank_candidate_k = args.rerank_candidates
    if args.reranker_max_length is not None:
        settings.reranker_max_length = args.reranker_max_length
    indexed_chunks = index_manager.rebuild()
    cases = load_cases(args.dataset)
    if args.limit:
        cases = cases[: args.limit]
    rows = []
    for index, case in enumerate(cases, start=1):
        rows.append(evaluate_case(case, args.with_generation, args.mode))
        if index % 10 == 0 or index == len(cases):
            print(f"评测进度 {index}/{len(cases)}", flush=True)
    answerable_rows = [row for row in rows if row["answerable"]]
    latencies = sorted(float(row["retrieval_ms"]) for row in rows)
    p95_index = max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1))
    threshold = choose_threshold(rows)
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "mode": args.mode,
        "indexed_chunks": indexed_chunks,
        "case_count": len(rows),
        "groups": {
            group: sum(row["group"] == group for row in rows)
            for group in sorted({row["group"] for row in rows})
        },
        "retrieval": {
            "hit_at_5": (
                sum(row["hit_at_5"] for row in answerable_rows) / len(answerable_rows)
                if answerable_rows
                else 0.0
            ),
            "mrr_at_5": (
                sum(row["reciprocal_rank"] for row in answerable_rows) / len(answerable_rows)
                if answerable_rows
                else 0.0
            ),
            "p95_ms": latencies[p95_index] if latencies else 0.0,
        },
        "recommended_refusal": threshold,
        "configuration": {
            "embedding_model": settings.embedding_model,
            "reranker_model": settings.reranker_model,
            "reranker_max_length": settings.reranker_max_length,
            "rerank_candidate_k": settings.rerank_candidate_k,
            "dense_top_k": settings.dense_top_k,
            "sparse_top_k": settings.sparse_top_k,
            "fusion_top_k": settings.fusion_top_k,
            "context_top_k": settings.context_top_k,
            "rrf_k": settings.rrf_k,
        },
        "cases": rows,
    }
    if args.with_generation:
        generated = [row for row in rows if "citation_gold_title_precision" in row]
        report["generation"] = {
            "citation_gold_title_precision": (
                sum(row["citation_gold_title_precision"] for row in generated) / len(generated)
                if generated
                else 0.0
            )
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "cases"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
