"""Central API router registry."""

from fastapi import APIRouter

from app.api.routers.admin import router as admin_router
from app.api.routers.api_keys import router as api_keys_router
from app.api.routers.auth import router as auth_router
from app.api.routers.documents import router as documents_router
from app.api.routers.health import router as health_router
from app.api.routers.public_audit import router as public_audit_router
from app.api.routers.public_documents import router as public_documents_router
from app.api.routers.public_templates import router as public_templates_router
from app.api.routers.templates import router as templates_router

api_router = APIRouter()
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(api_keys_router)
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(public_templates_router)
api_router.include_router(public_documents_router)
api_router.include_router(public_audit_router)
api_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
