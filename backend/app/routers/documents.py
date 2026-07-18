"""Knowledge base document management router.

Endpoints
--------
- GET    /api/documents       — list all documents (admin only)
- POST   /api/documents       — upload a new document (admin only)
- DELETE /api/documents/{id}  — delete a document (admin only)
- POST   /api/documents/{id}/reprocess — re-process a document (admin only)
"""

from pathlib import Path
from typing import Annotated
import sqlite3
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..database import get_db, utc_now
from ..config import settings
from .auth import current_user, admin_user
from ..rag_engine import rag_engine

router = APIRouter(prefix="/api/documents", tags=["documents"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}

Db = Annotated[sqlite3.Connection, Depends(get_db)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lookup_document(document_id: int, db: sqlite3.Connection) -> dict:
    """Fetch a single document row by id, or raise 404."""
    row = db.execute(
        "SELECT d.*, u.name AS uploader_name FROM documents d"
        " JOIN users u ON d.uploaded_by = u.id"
        " WHERE d.id = ?",
        (document_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return dict(row)


def _validate_and_save_file(
    title: str,
    file: UploadFile,
) -> tuple[bytes, str, str, str]:
    """Validate extension, size, and content; persist to disk.

    Returns
    -------
    (content_bytes, stored_name, mime_type, saved_path_str)
    """
    # --- title validation ---
    title = title.strip()
    if len(title) < 2 or len(title) > 120:
        raise HTTPException(
            status_code=422,
            detail="Title must be between 2 and 120 characters",
        )

    # --- extension check ---
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="文件格式不支持")

    # --- read content ---
    content = file.file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件不能超过 10MB")

    # --- persist ---
    stored_name = uuid.uuid4().hex + ext
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.upload_dir / stored_name
    dest.write_bytes(content)

    return content, stored_name, file.content_type or "application/octet-stream", str(dest)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def list_documents(
    db: Db,
    user: Annotated[dict, Depends(current_user)],
):
    """Return all documents."""
    rows = db.execute(
        "SELECT d.*, u.name AS uploader_name FROM documents d"
        " JOIN users u ON d.uploaded_by = u.id"
        " ORDER BY d.created_at DESC",
    ).fetchall()
    docs = []
    for r in rows:
        d = dict(r)
        d["size"] = int(d["size"])
        docs.append(d)
    return docs


@router.post("", status_code=201)
def upload_document(
    db: Db,
    user: Annotated[dict, Depends(current_user)],
    title: str = Form(...),
    file: UploadFile = File(...),
):
    """Upload a new document and trigger RAG indexing."""
    # --- validate & persist file ---
    content_bytes, stored_name, mime_type, saved_path = _validate_and_save_file(
        title, file
    )

    now = utc_now()

    # --- insert document row (status = PROCESSING) ---
    cursor = db.execute(
        """INSERT INTO documents
           (title, filename, stored_name, mime_type, size, status, uploaded_by,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, 'PROCESSING', ?, ?, ?)""",
        (
            title.strip(),
            file.filename,
            stored_name,
            mime_type,
            len(content_bytes),
            user["id"],
            now,
            now,
        ),
    )
    db.commit()
    document_id = cursor.lastrowid

    # --- process via RAG engine ---
    try:
        rag_engine.add_document(
            file_path=saved_path,
            document_id=document_id,
            title=title.strip(),
            category="其他",
            db=db,
        )
        db.execute(
            "UPDATE documents SET status = 'READY', updated_at = ? WHERE id = ?",
            (utc_now(), document_id),
        )
    except Exception:
        db.execute(
            "UPDATE documents SET status = 'ERROR', updated_at = ? WHERE id = ?",
            (utc_now(), document_id),
        )
    db.commit()

    return _lookup_document(document_id, db)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Db,
    user: Annotated[dict, Depends(admin_user)],
):
    """Delete a document, its RAG index, and (optionally) disk file (admin only)."""
    doc = _lookup_document(document_id, db)

    # --- DB row ---
    db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.commit()

    # --- RAG index ---
    rag_engine.delete_document(document_id)

    # --- physical file (skip seed documents) ---
    if not doc["stored_name"].startswith("seed-"):
        file_path = settings.upload_dir / doc["stored_name"]
        if file_path.exists():
            file_path.unlink()


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: int,
    db: Db,
    user: Annotated[dict, Depends(admin_user)],
):
    """Re-process an existing document through the RAG pipeline (admin only)."""
    doc = _lookup_document(document_id, db)

    # --- check physical file ---
    file_path = settings.upload_dir / doc["stored_name"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # --- process ---
    try:
        rag_engine.reprocess_document(
            file_path=str(file_path),
            document_id=document_id,
            title=doc["title"],
            category=doc.get("category", "其他"),
            db=db,
        )
        db.execute(
            "UPDATE documents SET status = 'READY', updated_at = ? WHERE id = ?",
            (utc_now(), document_id),
        )
    except Exception:
        db.execute(
            "UPDATE documents SET status = 'ERROR', updated_at = ? WHERE id = ?",
            (utc_now(), document_id),
        )
    db.commit()

    return _lookup_document(document_id, db)
