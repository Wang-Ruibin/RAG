from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

TEST_ROOT = Path(tempfile.mkdtemp(prefix="campusqa-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.db'}"
os.environ["DB_BACKEND"] = "sqlite"
os.environ["DATA_DIR"] = str(TEST_ROOT / "data")
os.environ["FRONTEND_DIST"] = str(TEST_ROOT / "frontend-dist")
os.environ["JWT_SECRET"] = "test-only-secret-at-least-32-characters"
os.environ["RERANK_ENABLED"] = "false"

from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.rag.index import index_manager  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    shutil.rmtree(settings.data_dir, ignore_errors=True)
    settings.ensure_directories()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    index_manager.rebuild()
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
