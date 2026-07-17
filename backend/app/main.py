from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import admin, auth, chat, documents, system
from app.core.config import settings
from app.core.database import SessionLocal, init_database
from app.core.responses import success
from app.models.enums import DocumentStatus, MessageStatus
from app.models.orm import Document, Message, QaEntry
from app.rag.index import index_manager
from app.rag.qa_index import qa_index_manager
from app.rag.retrieval import retrieval_service
from app.services.answer_corrections import answer_correction_service
from app.services.documents import document_service

logger = logging.getLogger("uvicorn.error")


class SPAStaticFiles(StaticFiles):
    """Serve React Router routes from index.html while preserving real asset 404s."""

    async def get_response(self, path: str, scope):  # type: ignore[no-untyped-def]
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    document_service.recover_stuck_jobs()
    answer_correction_service.recover_stuck_corrections()
    with SessionLocal() as db:
        for message in db.query(Message).filter(Message.status == MessageStatus.STREAMING).all():
            message.status = MessageStatus.ERROR
            if not message.content:
                message.content = "服务重启中断了本次回答，请重试。"
        db.commit()
        valid_document_ids = set(
            db.scalars(
                select(Document.id).where(Document.status != DocumentStatus.DELETING)
            ).all()
        )
        valid_qa_entry_ids = set(
            db.scalars(select(QaEntry.id).where(QaEntry.is_active.is_(True))).all()
        )
    index_started = time.perf_counter()
    index_count = index_manager.load(valid_document_ids=valid_document_ids)
    logger.info(
        "Knowledge index loaded chunks=%d elapsed=%.2fs",
        index_count,
        time.perf_counter() - index_started,
    )
    qa_count = qa_index_manager.load(valid_entry_ids=valid_qa_entry_ids)
    logger.info("Hidden QA index loaded entries=%d", qa_count)
    if settings.rag_prewarm and index_count:
        retrieval_service.warmup()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于本地混合检索与 DeepSeek 的引用式校园知识问答 API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=success(None, str(exc.detail), exc.status_code),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {"field": ".".join(str(part) for part in item["loc"]), "message": item["msg"]}
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=success({"errors": errors}, "请求参数校验失败", 422),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理的请求异常", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=success(None, "服务暂时不可用，请稍后重试", 500),
    )


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(system.router)


frontend = Path(settings.frontend_dist)
if frontend.is_dir():
    app.mount("/", SPAStaticFiles(directory=frontend, html=True), name="frontend")
