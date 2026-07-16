from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def success(data: Any = None, message: str = "ok", code: int = 200) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
        "timestamp": datetime.now(UTC).isoformat(),
    }
