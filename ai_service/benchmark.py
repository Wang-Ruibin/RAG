"""
Benchmark script for RAG parameter tuning.

Tests different *chunk_size* × *top_k* combinations against the 10 CLI test
questions, measuring retrieval performance and keyword hit rates without
making real DeepSeek API calls.

Usage
-----
    cd ai_service && python benchmark.py

Output
------
    - Formatted results table printed to stdout
    - JSON results saved to ``benchmark_results.json``
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

# ---------------------------------------------------------------------------
# Path setup: make engine modules importable  (same as cli.py)
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from engine.pipeline import RAGPipeline
from engine.generator import Generator
from cli import TEST_QUESTIONS

# ---------------------------------------------------------------------------
# Logging — only show warnings from engine modules
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ---------------------------------------------------------------------------
# Benchmark configuration
# ---------------------------------------------------------------------------

CHUNK_SIZES = [256, 512, 1024]
"""Chunk sizes (in characters) to test."""

TOP_KS = [3, 5, 10]
"""Number of retrieved chunks to test."""

CHUNK_OVERLAP = 50
"""Fixed chunk overlap used for all benchmark runs."""

_DATA_DIR = os.path.join(_THIS_DIR, "data")
_INDEX_PATH = os.path.join(_DATA_DIR, "faiss.index")
_META_PATH = os.path.join(_DATA_DIR, "metadata.json")
_BENCHMARK_RESULTS_PATH = os.path.join(_THIS_DIR, "benchmark_results.json")


# ---------------------------------------------------------------------------
# Mock generator — avoids real DeepSeek API calls during benchmarking
# ---------------------------------------------------------------------------


class MockGenerator(Generator):
    """Generator that returns a placeholder answer without calling the API.

    This lets us benchmark retrieval performance and keyword hit rates
    independently of LLM API latency / availability.
    """

    def __init__(self) -> None:
        # Intentionally skip parent ``__init__`` so no API key is required.
        pass

    # ------------------------------------------------------------------
    # Override the two methods called by the pipeline
    # ------------------------------------------------------------------

    def generate(
        self,
        system_prompt: str = "",
        user_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """Return a fixed placeholder — no API call."""
        return "[模拟回答] 基于检索到的文档内容生成。"

    def generate_stream(
        self,
        system_prompt: str = "",
        user_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ):
        """Yield nothing — no API call."""
        return iter([])

    # ------------------------------------------------------------------
    # Suppress diagnostic noise
    # ------------------------------------------------------------------

    def test(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _delete_index() -> None:
    """Remove persisted index and metadata files so the next run is clean."""
    for path in (_INDEX_PATH, _META_PATH):
        if os.path.isfile(path):
            os.remove(path)


def _keyword_hit_rate(answer: str, keywords: list[str]) -> float:
    """Return the fraction of *keywords* found inside *answer*."""
    if not keywords:
        return 1.0
    hits = sum(1 for kw in keywords if kw in answer)
    return hits / len(keywords)


def _has_sources(result: dict[str, Any]) -> bool:
    """Return ``True`` when the pipeline result includes at least one source."""
    return len(result.get("sources", [])) > 0


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


def run_benchmark() -> list[dict]:
    """Run all *chunk_size* × *top_k* combinations and return the raw data."""
    all_results: list[dict] = []
    total_combos = len(CHUNK_SIZES) * len(TOP_KS)
    combo_idx = 0

    for chunk_size in CHUNK_SIZES:
        for top_k in TOP_KS:
            combo_idx += 1
            print(f"\n[{combo_idx}/{total_combos}]  "
                  f"chunk_size={chunk_size},  top_k={top_k}")
            print("-" * 60)

            # 1. Clean slate — delete any previously persisted index
            _delete_index()

            # 2. Create pipeline with mock generator (no API calls)
            pipeline = RAGPipeline(generator=MockGenerator())

            # 3. Index documents with the current chunk_size
            print(f"    Indexing (chunk_size={chunk_size}, "
                  f"overlap={CHUNK_OVERLAP}) …")
            index_result = pipeline.index_documents(
                chunk_size=chunk_size,
                chunk_overlap=CHUNK_OVERLAP,
            )
            print(f"    → {index_result['chunks_count']} chunks from "
                  f"{index_result['docs_count']} docs in "
                  f"{index_result['time_seconds']}s")

            # 4. Run all test questions through the pipeline
            question_results: list[dict] = []
            for i, item in enumerate(TEST_QUESTIONS, 1):
                q = item["question"]
                keywords = item["keywords"]

                # -- Timed retrieval --------------------------------
                t0 = time.time()
                chunks = pipeline.retriever.retrieve(q, top_k=top_k)
                retrieval_time = time.time() - t0

                # -- Full pipeline (generate step is mocked) --------
                t0 = time.time()
                result = pipeline.run(query=q, top_k=top_k)
                generate_time = time.time() - t0

                answer = result.get("answer", "")
                hit_rate = _keyword_hit_rate(answer, keywords)
                has_src = _has_sources(result)

                question_results.append({
                    "question": q,
                    "retrieval_time": round(retrieval_time, 4),
                    "generate_time": round(generate_time, 4),
                    "keyword_hit_rate": hit_rate,
                    "all_keywords_found": hit_rate == 1.0,
                    "has_sources": has_src,
                    "num_chunks": len(chunks),
                    "answer_preview": answer[:120],
                })

                status = "PASS" if (hit_rate == 1.0 and has_src) else "FAIL"
                print(
                    f"    [{i:2d}/10] {status}  "
                    f"ret={retrieval_time:.3f}s  "
                    f"gen={generate_time:.3f}s  "
                    f"kw={hit_rate:.0%}  src={int(has_src)}  |  {q[:35]}"
                )

            # 5. Aggregate statistics for this parameter combination
            avg_retrieval = (
                sum(r["retrieval_time"] for r in question_results)
                / len(question_results)
            )
            avg_generate = (
                sum(r["generate_time"] for r in question_results)
                / len(question_results)
            )
            overall_hit_rate = (
                sum(r["keyword_hit_rate"] for r in question_results)
                / len(question_results)
            )
            sources_rate = (
                sum(1 for r in question_results if r["has_sources"])
                / len(question_results)
            )
            pass_count = sum(
                1 for r in question_results
                if r["all_keywords_found"] and r["has_sources"]
            )

            summary = {
                "chunk_size": chunk_size,
                "top_k": top_k,
                "avg_retrieval_time": round(avg_retrieval, 4),
                "avg_generate_time": round(avg_generate, 4),
                "keyword_hit_rate": round(overall_hit_rate, 4),
                "sources_rate": round(sources_rate, 4),
                "pass_count": pass_count,
                "total_questions": len(question_results),
                "index_info": {
                    "chunks_count": index_result["chunks_count"],
                    "docs_count": index_result["docs_count"],
                    "index_time_seconds": index_result["time_seconds"],
                },
                "failed_questions": [
                    r["question"][:60]
                    for r in question_results
                    if not (r["all_keywords_found"] and r["has_sources"])
                ],
                "per_question": question_results,
            }
            all_results.append(summary)

            print(
                f"    →  avg_retrieve={avg_retrieval:.3f}s  "
                f"avg_generate={avg_generate:.3f}s  "
                f"hit_rate={overall_hit_rate:.0%}  "
                f"sources={sources_rate:.0%}  "
                f"pass={pass_count}/{len(question_results)}"
            )

    return all_results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_results(results: list[dict]) -> None:
    """Print a formatted summary table and highlight the best combination."""
    print()
    print("=" * 80)
    print("  Benchmark Results")
    print("=" * 80)
    print()

    for r in results:
        cs = r["chunk_size"]
        tk = r["top_k"]
        art = r["avg_retrieval_time"]
        agt = r["avg_generate_time"]
        khr = r["keyword_hit_rate"]
        sr = r["sources_rate"]
        pc = r["pass_count"]
        tot = r["total_questions"]
        print(
            f"  chunk_size={cs}, top_k={tk}:  "
            f"avg_retrieve={art:.3f}s  "
            f"avg_generate={agt:.3f}s  "
            f"hit_rate={khr:.0%}  "
            f"sources={sr:.0%}  "
            f"pass={pc}/{tot}"
        )

    print()

    # Best: highest pass_count → highest hit_rate → lowest retrieval time
    best = max(
        results,
        key=lambda r: (
            r["pass_count"],
            r["keyword_hit_rate"],
            -r["avg_retrieval_time"],
        ),
    )
    print(
        f"  ★ Best: chunk_size={best['chunk_size']}, top_k={best['top_k']}  "
        f"(pass={best['pass_count']}/{best['total_questions']},  "
        f"hit_rate={best['keyword_hit_rate']:.0%})"
    )

    if best["failed_questions"]:
        print()
        print(f"  Failed questions for best config "
              f"({len(best['failed_questions'])}):")
        for fq in best["failed_questions"]:
            print(f"    · {fq}")

    print("=" * 80)
    print()


def save_results(results: list[dict], path: str) -> None:
    """Persist benchmark results to a JSON file for later analysis."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📁  Results saved to {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("RAG Benchmark — Parameter Tuning")
    print(f"  chunk_sizes:  {CHUNK_SIZES}")
    print(f"  top_k values: {TOP_KS}")
    print(f"  test queries: {len(TEST_QUESTIONS)}")
    print(f"  total combos: {len(CHUNK_SIZES) * len(TOP_KS)}")
    print()

    results = run_benchmark()
    print_results(results)
    save_results(results, _BENCHMARK_RESULTS_PATH)


if __name__ == "__main__":
    main()
