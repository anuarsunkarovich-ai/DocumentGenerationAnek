"""Application services for health checks."""

from app.dtos.health import HealthResponse, LiveHealthResponse
from app.services.operations_service import OperationsService


class HealthService:
    """Handle backend health reporting."""

    def __init__(self) -> None:
        self._operations_service = OperationsService()

    async def get_liveness(self) -> LiveHealthResponse:
        """Return a process-only liveness result."""
        return await self._operations_service.get_liveness()

    async def get_readiness(self) -> HealthResponse:
        """Return dependency readiness."""
        return await self._operations_service.get_readiness()

    async def get_status(self) -> HealthResponse:
        """Return a summary health result."""
        return await self._operations_service.get_readiness()
