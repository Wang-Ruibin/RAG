from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal, init_database  # noqa: E402
from app.models.orm import (  # noqa: E402
    AnswerKnowledgeTask,
    Document,
    QaEntry,
    QaSourceLink,
)
from app.rag.index import index_manager  # noqa: E402
from app.rag.qa_index import qa_index_manager  # noqa: E402
from app.services.answer_knowledge import answer_knowledge_service  # noqa: E402
from app.services.qa_knowledge import qa_knowledge_service  # noqa: E402
from sqlalchemy import func, select  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert legacy answer documents into hidden deduplicated QA entries."
    )
    parser.add_argument("--apply", action="store_true", help="Apply changes; otherwise only list")
    parser.add_argument(
        "--verify-query",
        default="",
        help="Run the hidden QA lookup for a query and print non-sensitive diagnostics.",
    )
    args = parser.parse_args()

    init_database()
    with SessionLocal() as db:
        task_ids = list(
            db.scalars(
                select(AnswerKnowledgeTask.id).where(
                    AnswerKnowledgeTask.qa_entry_id.is_(None),
                    AnswerKnowledgeTask.document_id.is_not(None),
                )
            ).all()
        )
        valid_qa_ids = list(db.scalars(select(QaEntry.id).where(QaEntry.is_active.is_(True))).all())
        qa_count = db.scalar(select(func.count(QaEntry.id))) or 0
        link_count = db.scalar(select(func.count(QaSourceLink.id))) or 0
        archive_count = (
            db.scalar(
                select(func.count(Document.id)).where(
                    Document.category == settings.answer_web_archive_category
                )
            )
            or 0
        )
    index_manager.load()
    qa_index_manager.load(valid_entry_ids=valid_qa_ids)
    print(
        f"legacy_tasks={len(task_ids)} qa_entries={qa_count} "
        f"source_links={link_count} web_archives={archive_count} apply={args.apply}"
    )
    if args.verify_query:
        lookup = qa_knowledge_service.lookup(args.verify_query)
        print(
            f"lookup_mode={lookup.mode} "
            f"score={lookup.match.score if lookup.match else None} "
            f"entry_id={lookup.match.entry_id if lookup.match else None} "
            f"resolved_sources={len(lookup.sources)}"
        )
        if lookup.match is not None:
            print(f"matched_question={lookup.match.question}")
        for source in lookup.sources:
            print(
                f"source marker={source.marker}{source.citation_index} "
                f"document_id={source.result.document_id} title={source.result.title}"
            )
    if not args.apply:
        return

    migrated = 0
    failed = 0
    for task_id in task_ids:
        if answer_knowledge_service.migrate_legacy_task(task_id):
            migrated += 1
            print(f"migrated task_id={task_id}")
        else:
            failed += 1
            print(f"failed task_id={task_id}")
    print(f"done migrated={migrated} failed={failed}")


if __name__ == "__main__":
    main()
