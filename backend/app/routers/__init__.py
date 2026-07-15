"""API 路由"""

from app.routers.admin import router as admin_router
from app.routers.ai import router as ai_router
from app.routers.user import router as user_router
from app.routers.document import router as document_router
from app.routers.qa import router as qa_router

__all__ = ["admin_router", "ai_router", "user_router", "document_router", "qa_router"]
