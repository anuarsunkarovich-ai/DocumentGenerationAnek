"""Controller helpers for service health endpoints."""

from app.dtos.health import HealthResponse, LiveHealthResponse
from app.services.health_service import HealthService


class HealthController:
    """Coordinate health-check requests."""

    def __init__(self, service: HealthService) -> None:
        self._service = service

    async def get_liveness(self) -> LiveHealthResponse:
        """Return process liveness."""
        return await self._service.get_liveness()

    async def get_readiness(self) -> HealthResponse:
        """Return dependency readiness."""
        return await self._service.get_readiness()

    async def get_status(self) -> HealthResponse:
        """Return the current API health status."""
        return await self._service.get_status()
