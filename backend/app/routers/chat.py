"""AI Q&A streaming chat router.

Provides a server-sent events (SSE) endpoint for the RAG-powered question
answering flow.  Each conversation is persisted to SQLite with user/assistant
message pairs and source metadata.
"""

from typing import Annotated
from collections.abc import Iterator
import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..database import get_db, utc_now
from ..models import ChatBody
from ..utils import normalize_question
from .auth import current_user
from ..rag_engine import rag_engine

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/stream")
def chat_stream(
    body: ChatBody,
    db: sqlite3.Connection = Depends(get_db),
    user: sqlite3.Row = Depends(current_user),
) -> StreamingResponse:
    """Stream an AI answer to *question*, optionally continuing *conversation_id*.

    Returns a ``text/event-stream`` response compatible with the standard
    ``EventSource`` API.  Each SSE event is one of:

    - ``meta``    – carries ``sources`` and the resolved ``conversation_id``
    - ``token``   – a single text token of the answer
    - ``done``    – signals the end of the stream

    If *conversation_id* is ``None`` a new conversation is created whose title
    is the first 28 characters of the question.
    """
    now = utc_now()

    # ------------------------------------------------------------------
    # Resolve (or create) conversation
    # ------------------------------------------------------------------
    if body.conversation_id is not None:
        conv = db.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (body.conversation_id,),
        ).fetchone()
        if conv is None or conv["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = body.conversation_id
    else:
        cursor = db.execute(
            """INSERT INTO conversations (user_id, title, created_at, updated_at)
               VALUES (?, ?, ?, ?)""",
            (user["id"], body.question[:28], now, now),
        )
        db.commit()
        conversation_id = cursor.lastrowid

    # ------------------------------------------------------------------
    # Q&A Cache Check
    # ------------------------------------------------------------------
    sig = normalize_question(body.question)
    cached = db.execute(
        "SELECT * FROM qa_cache WHERE question_signature = ?",
        (sig,),
    ).fetchone()

    if cached:
        # ---- Cache hit: increment counter, return cached answer as SSE ----
        db.execute(
            "UPDATE qa_cache SET hit_count = hit_count + 1, updated_at = ? WHERE id = ?",
            (utc_now(), cached["id"]),
        )
        db.commit()

        def cached_events() -> Iterator[str]:
            yield (
                f"event: meta\n"
                f"data: {json.dumps({'sources': json.loads(cached['sources']), 'conversation_id': conversation_id, 'cached': True}, ensure_ascii=False)}\n\n"
            )
            for char in cached["answer"]:
                yield (
                    f"event: token\n"
                    f"data: {json.dumps({'text': char}, ensure_ascii=False)}\n\n"
                )
            yield "event: done\ndata: {}\n\n"

            # ---- Persist messages after the cached stream ----
            db.execute(
                """INSERT INTO messages
                   (conversation_id, role, content, sources, created_at)
                   VALUES (?, 'USER', ?, '[]', ?)""",
                (conversation_id, body.question, now),
            )
            db.execute(
                """INSERT INTO messages
                   (conversation_id, role, content, sources, created_at)
                   VALUES (?, 'ASSISTANT', ?, ?, ?)""",
                (
                    conversation_id,
                    cached["answer"],
                    cached["sources"],
                    utc_now(),
                ),
            )
            db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (utc_now(), conversation_id),
            )
            db.commit()

        return StreamingResponse(cached_events(), media_type="text/event-stream")

    # ------------------------------------------------------------------
    # Cache miss → SSE event generator (original RAG flow)
    # ------------------------------------------------------------------
    def events() -> Iterator[str]:
        """Yield SSE-formatted strings consumed by ``StreamingResponse``."""
        full_answer = ""
        sources = []

        for raw in rag_engine.stream_query(body.question, conversation_id):
            # Defensive decode — ensure we always work with str
            if isinstance(raw, bytes):
                raw_event = raw.decode("utf-8")
            else:
                raw_event = raw

            # ---- Parse the SSE event type from the first line ----
            event_type = ""
            data_str = ""
            for line in raw_event.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data_str = line[6:]

            if event_type == "meta":
                # Inject conversation_id into the meta payload
                try:
                    data = json.loads(data_str) if data_str else {}
                    if "sources" in data:
                        sources = data["sources"]
                    data["conversation_id"] = conversation_id
                    yield (
                        f"event: meta\n"
                        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    )
                except Exception:
                    # Defensive: fall back to the original event if parsing fails
                    yield raw_event

            elif event_type == "token":
                try:
                    data = json.loads(data_str) if data_str else {}
                    full_answer += data.get("text", "")
                except Exception:
                    pass
                yield raw_event

            elif event_type == "done":
                yield raw_event

            else:
                # Pass through any unrecognised event type unchanged
                yield raw_event

        # ---- Persist messages after the stream completes ----
        db.execute(
            """INSERT INTO messages
               (conversation_id, role, content, sources, created_at)
               VALUES (?, 'USER', ?, '[]', ?)""",
            (conversation_id, body.question, now),
        )
        db.execute(
            """INSERT INTO messages
               (conversation_id, role, content, sources, created_at)
               VALUES (?, 'ASSISTANT', ?, ?, ?)""",
            (
                conversation_id,
                full_answer,
                json.dumps(sources, ensure_ascii=False),
                utc_now(),
            ),
        )
        db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (utc_now(), conversation_id),
        )
        db.commit()

        # ---- Cache the Q&A pair for future requests ----
        db.execute(
            """INSERT OR REPLACE INTO qa_cache
               (question_signature, question, answer, sources, hit_count, created_at, updated_at)
               VALUES (?, ?, ?, ?,
                       COALESCE((SELECT hit_count FROM qa_cache WHERE question_signature = ?), 0) + 1,
                       ?, ?)""",
            (
                sig,
                body.question,
                full_answer,
                json.dumps(sources, ensure_ascii=False),
                sig,
                now,
                utc_now(),
            ),
        )
        db.commit()

    return StreamingResponse(events(), media_type="text/event-stream")


__all__ = ["router"]
