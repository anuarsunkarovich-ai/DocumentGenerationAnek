"""Health-check API routes."""

from fastapi import APIRouter, Response, status

from app.api.controllers.health_controller import HealthController
from app.dtos.health import HealthResponse, LiveHealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health(response: Response) -> HealthResponse:
    """Return the backend health status."""
    controller = HealthController(service=HealthService())
    health = await controller.get_status()
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health


@router.get("/health/live", response_model=LiveHealthResponse)
async def get_health_live() -> LiveHealthResponse:
    """Return a liveness-only health response."""
    controller = HealthController(service=HealthService())
    return await controller.get_liveness()


@router.get("/health/ready", response_model=HealthResponse)
async def get_health_ready(response: Response) -> HealthResponse:
    """Return dependency readiness for the API process."""
    controller = HealthController(service=HealthService())
    health = await controller.get_readiness()
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health
