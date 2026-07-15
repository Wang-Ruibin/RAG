"""API 路由"""

from app.routers.user import router as user_router
from app.routers.document import router as document_router
from app.routers.qa import router as qa_router

__all__ = ["user_router", "document_router", "qa_router"]
