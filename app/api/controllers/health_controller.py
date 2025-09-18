"""Controller helpers for service health endpoints."""

from app.dtos.health import HealthResponse
from app.services.health_service import HealthService


class HealthController:
    """Coordinate health-check requests."""

    def __init__(self, service: HealthService) -> None:
        self._service = service

    async def get_status(self) -> HealthResponse:
        """Return the current API health status."""
        return await self._service.get_status()
