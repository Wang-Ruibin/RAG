"""
CLI RAG script — standalone question-answering tool for the Hohai University
knowledge base.

Usage
-----
    python cli.py --ask "问题"        Single question mode
    python cli.py --test              Test mode (10 pre-defined questions)
    python cli.py                     Interactive mode
    python cli.py --rebuild           Force rebuild index, then exit
    python cli.py --index             Build index only, do not ask

Optional arguments
------------------
    --chunk-size    Chunk size in characters (default: 500)
    --overlap       Chunk overlap in characters (default: 50)
    --top-k         Number of chunks to retrieve (default: 5)

Notes
-----
- Imports engine modules directly (engine.pipeline.RAGPipeline).
- Does NOT import from backend/ or use FastAPI.
- Index files (faiss.index + metadata.json) are stored under ai_service/data/.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys

# ---------------------------------------------------------------------------
# Path setup: make engine modules importable
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from engine.pipeline import RAGPipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("cli")

# ---------------------------------------------------------------------------
# Test questions (from the instructor's specification)
# ---------------------------------------------------------------------------

TEST_QUESTIONS: list[dict] = [
    {
        "question": "河海大学的校训是什么？",
        "keywords": ["艰苦朴素", "实事求是", "严格要求", "勇于探索"],
    },
    {
        "question": "河海大学是哪一年创办的？",
        "keywords": ["1915"],
    },
    {
        "question": "河海大学的创办人是谁？",
        "keywords": ["张謇"],
    },
    {
        "question": "河海大学有几个校区？分别在哪些城市？",
        "keywords": ["南京", "常州"],
    },
    {
        "question": "河海大学的首任院长是谁？",
        "keywords": ["钱正英"],
    },
    {
        "question": "河海大学的前身是什么？",
        "keywords": ["河海工程专门学校"],
    },
    {
        "question": "河海大学的校庆日是哪一天？",
        "keywords": ["10月27日"],
    },
    {
        "question": "河海大学的校歌是什么？",
        "keywords": ["大哉河海奔前程"],
    },
    {
        "question": "河海大学是哪一年恢复校名的？",
        "keywords": ["1985"],
    },
    {
        "question": "河海大学有多少个学科进入ESI世界排名前1%？",
        "keywords": ["10"],
    },
]

# ---------------------------------------------------------------------------
# Data directory helpers
# ---------------------------------------------------------------------------

_DATA_DIR = os.path.join(_THIS_DIR, "data")
_INDEX_PATH = os.path.join(_DATA_DIR, "faiss.index")
_META_PATH = os.path.join(_DATA_DIR, "metadata.json")


def _index_exists() -> bool:
    """Check whether a persisted index is already present on disk."""
    return os.path.isfile(_INDEX_PATH) and os.path.isfile(_META_PATH)


def _delete_index() -> None:
    """Remove persisted index and metadata files."""
    for path in (_INDEX_PATH, _META_PATH):
        if os.path.isfile(path):
            os.remove(path)
            logger.info("Deleted %s", path)


# ---------------------------------------------------------------------------
# Pipeline helpers
# ---------------------------------------------------------------------------


def _get_pipeline(
    chunk_size: int = 500,
    overlap: int = 50,
    top_k: int = 5,
) -> tuple[RAGPipeline, int]:
    """Return a (pipeline, top_k) tuple.

    If the index does not exist on disk, build it first.
    """
    pipeline = RAGPipeline()
    if not _index_exists():
        print("📦 Index not found — building from scratch ...")
        pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)
    return pipeline, top_k


def _ensure_index(
    pipeline: RAGPipeline,
    chunk_size: int = 500,
    overlap: int = 50,
) -> None:
    """Build index if it does not already exist."""
    if not _index_exists():
        pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def cmd_ask(question: str, chunk_size: int, overlap: int, top_k: int) -> None:
    """Single question mode: index → retrieve → generate → print."""
    pipeline, k = _get_pipeline(chunk_size, overlap, top_k)
    _ensure_index(pipeline, chunk_size, overlap)

    print(f"\n问题：{question}")
    result = pipeline.run(query=question, top_k=k)
    print(f"答案：{result['answer']}")
    if result["sources"]:
        print("来源：")
        for i, src in enumerate(result["sources"], 1):
            title = src.get("title", "未知")
            score = src.get("score", 0.0)
            print(f"  [{i}] {title} (score: {score:.3f})")
    print()


def cmd_test(chunk_size: int, overlap: int, top_k: int) -> None:
    """Test mode: run all 10 pre-defined questions and report PASS/FAIL."""
    pipeline = RAGPipeline()
    if not _index_exists():
        print("📦 Index not found — building from scratch ...")
        pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)

    passed = 0
    total = len(TEST_QUESTIONS)

    print(f"\n{'='*60}")
    print(f"  开始测试 — 共 {total} 题")
    print(f"{'='*60}\n")

    for i, item in enumerate(TEST_QUESTIONS, 1):
        q = item["question"]
        keywords = item["keywords"]

        print(f"--- 第 {i}/{total} 题 ---")
        print(f"问题：{q}")

        result = pipeline.run(query=q, top_k=top_k)
        answer = result["answer"]

        print(f"答案：{answer[:200]}{'…' if len(answer) > 200 else ''}")

        # Keyword check
        all_found = True
        for kw in keywords:
            if kw in answer:
                print(f"  ✅ 关键词「{kw}」命中")
            else:
                print(f"  ❌ 关键词「{kw}」未命中")
                all_found = False

        if all_found:
            passed += 1
            print(f"  >>> PASS <<<\n")
        else:
            print(f"  >>> FAIL <<<\n")

    # Summary
    score = passed / total * 100
    print(f"{'='*60}")
    print(f"  测试完成：{passed}/{total} 通过 ({score:.1f}%)")
    print(f"{'='*60}\n")


def cmd_interactive(chunk_size: int, overlap: int, top_k: int) -> None:
    """Interactive mode: loop reading questions from stdin."""
    pipeline = RAGPipeline()
    if not _index_exists():
        print("📦 Index not found — building from scratch ...")
        pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)

    print("\n🔤 交互模式已启动。输入问题开始查询，输入 quit 退出，输入 rebuild 重建索引。\n")

    while True:
        try:
            q = input("问题 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not q:
            continue

        if q.lower() == "quit":
            print("再见！")
            break

        if q.lower() == "rebuild":
            print("🔄 正在重建索引 ...")
            _delete_index()
            pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)
            print("✅ 索引重建完成\n")
            continue

        result = pipeline.run(query=q, top_k=top_k)
        print(f"答案：{result['answer']}")
        if result["sources"]:
            print("来源：")
            for i, src in enumerate(result["sources"], 1):
                title = src.get("title", "未知")
                score = src.get("score", 0.0)
                print(f"  [{i}] {title} (score: {score:.3f})")
        print()


def cmd_rebuild(chunk_size: int, overlap: int) -> None:
    """Force rebuild index: delete existing index and rebuild from scratch."""
    print("🔄 强制重建索引 ...")
    _delete_index()
    pipeline = RAGPipeline()
    result = pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)
    print(f"✅ 索引重建完成：{result['chunks_count']} 个块，{result['docs_count']} 个文档")
    print(f"   耗时 {result['time_seconds']} 秒")


def cmd_index(chunk_size: int, overlap: int) -> None:
    """Only build index, do not ask questions."""
    if _index_exists():
        print("索引已存在，跳过构建。")
        print("如需强制重建请使用 --rebuild 参数。")
        return
    print("📦 正在构建索引 ...")
    pipeline = RAGPipeline()
    result = pipeline.index_documents(chunk_size=chunk_size, chunk_overlap=overlap)
    print(f"✅ 索引构建完成：{result['chunks_count']} 个块，{result['docs_count']} 个文档")
    print(f"   耗时 {result['time_seconds']} 秒")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="河海大学 RAG 知识问答命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python cli.py --ask \"河海大学的校训是什么？\"\n"
            "  python cli.py --test\n"
            "  python cli.py --rebuild\n"
            "  python cli.py --index\n"
            "  python cli.py --chunk-size 300 --overlap 30 --ask \"校训是什么？\"\n"
        ),
    )

    # Mutually exclusive mode flags
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--ask",
        type=str,
        default=None,
        metavar="问题",
        help="单问题模式：提问并获取答案",
    )
    mode.add_argument(
        "--test",
        action="store_true",
        help="测试模式：运行 10 个预定义问题并报告 PASS/FAIL",
    )
    mode.add_argument(
        "--rebuild",
        action="store_true",
        help="强制重建索引（删除已有索引后重建）",
    )
    mode.add_argument(
        "--index",
        action="store_true",
        help="仅构建索引，不提问",
    )

    # Parameters
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="分块大小（字符数，默认 500）",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="分块重叠（字符数，默认 50）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="检索块数量（默认 5）",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    chunk_size = args.chunk_size
    overlap = args.overlap
    top_k = args.top_k

    if args.rebuild:
        cmd_rebuild(chunk_size, overlap)
    elif args.index:
        cmd_index(chunk_size, overlap)
    elif args.ask is not None:
        cmd_ask(args.ask, chunk_size, overlap, top_k)
    elif args.test:
        cmd_test(chunk_size, overlap, top_k)
    else:
        # Default: interactive mode
        cmd_interactive(chunk_size, overlap, top_k)


if __name__ == "__main__":
    main()
