"""Health-check API routes."""

from fastapi import APIRouter, Response, status

from app.api.controllers.health_controller import HealthController
from app.dtos.health import HealthResponse
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
