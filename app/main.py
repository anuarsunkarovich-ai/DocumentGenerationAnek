"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import database_manager
from app.core.exceptions import (
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import configure_logging
from app.dtos.health import HealthResponse
from app.services.health_service import HealthService
from app.services.storage import get_storage_service


@asynccontextmanager
async def application_lifespan(application: FastAPI):
    """Initialize infrastructure dependencies required by the API runtime."""
    _ = application
    await get_storage_service().ensure_bucket()
    try:
        yield
    finally:
        await database_manager.dispose()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging()

    application = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description=settings.app.description,
        debug=settings.app.debug,
        docs_url=settings.app.docs_url,
        redoc_url=settings.app.redoc_url,
        openapi_url=settings.app.openapi_url,
        lifespan=application_lifespan,
    )
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.include_router(api_router, prefix=settings.app.api_prefix)

    @application.get("/health", response_model=HealthResponse)
    async def root_health(response: Response) -> HealthResponse:
        """Return an unprefixed health endpoint for infrastructure checks."""
        health = await HealthService().get_status()
        if health.status != "ok":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return health

    return application


async def application_error_handler(
    request: Request,
    error: Exception,
) -> JSONResponse:
    """Map domain-specific errors to stable HTTP responses."""
    _ = request

    if isinstance(error, NotFoundError):
        status_code = 404
    elif isinstance(error, ConflictError):
        status_code = 409
    elif isinstance(error, ValidationError):
        status_code = 422
    elif isinstance(error, AuthenticationError):
        status_code = 401
    elif isinstance(error, AuthorizationError):
        status_code = 403
    else:
        status_code = 400

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(error)},
    )


app = create_application()
