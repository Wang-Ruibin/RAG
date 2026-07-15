"""
AI Service — FastAPI server for RAG query, streaming, and indexing.

Endpoints
---------
GET  /health        → Health check
POST /query         → Synchronous RAG query
GET  /query/stream  → SSE streaming query
GET  /reindex       → Full re-index all documents
POST /process       → Index a single file
GET  /stats         → Knowledge base statistics
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from engine.pipeline import RAGPipeline

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ai_service")

# ---------------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------------

app = FastAPI(title="AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global pipeline instance
# ---------------------------------------------------------------------------

pipeline: RAGPipeline = RAGPipeline()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str = Field(..., description="The user's question")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of chunks to retrieve")


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]


class ProcessRequest(BaseModel):
    file_path: str = Field(..., description="Path to the document file")


class ProcessResponse(BaseModel):
    chunks_count: int
    indexed: int
    doc_id: str


# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("AI Service running on port 8003")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Sync query
# ---------------------------------------------------------------------------


@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest) -> dict[str, Any]:
    try:
        result = pipeline.run(query=body.question, top_k=body.top_k)
        return result
    except Exception as exc:
        logger.exception("Sync query failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# SSE streaming query
# ---------------------------------------------------------------------------


@app.get("/query/stream")
async def query_stream(
    question: str = Query(..., description="The user's question"),
    top_k: int = Query(default=5, ge=1, le=50),
) -> EventSourceResponse:
    async def event_generator():
        try:
            for event in pipeline.run_stream(query=question, top_k=top_k):
                event_type = event.pop("type", None)
                if event_type == "status":
                    yield {"event": "status", "data": event}
                elif event_type == "sources":
                    yield {"event": "sources", "data": event}
                elif event_type == "token":
                    yield {"event": "token", "data": event}
                elif event_type == "done":
                    yield {"event": "done", "data": event}
                else:
                    yield {"event": "unknown", "data": event}
        except Exception as exc:
            logger.exception("Streaming query failed")
            yield {"event": "error", "data": {"message": str(exc)}}

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Re-index
# ---------------------------------------------------------------------------


@app.get("/reindex")
async def reindex() -> dict[str, Any]:
    try:
        result = pipeline.index_documents()
        return result
    except Exception as exc:
        logger.exception("Re-index failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Process single file
# ---------------------------------------------------------------------------


@app.post("/process", response_model=ProcessResponse)
async def process(body: ProcessRequest) -> dict[str, Any]:
    try:
        result = pipeline.add_document(file_path=body.file_path)
        return result
    except Exception as exc:
        logger.exception("Process document failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@app.get("/stats")
async def stats() -> dict[str, Any]:
    try:
        return pipeline.get_stats()
    except Exception as exc:
        logger.exception("Get stats failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=False)
