"""Central API router registry."""

from fastapi import APIRouter

from app.api.routers.auth import router as auth_router
from app.api.routers.documents import router as documents_router
from app.api.routers.health import router as health_router
from app.api.routers.templates import router as templates_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
