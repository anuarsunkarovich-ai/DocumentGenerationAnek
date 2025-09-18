"""Application services for health checks."""

from sqlalchemy import text

from app.core.database import get_transaction_session
from app.dtos.health import HealthDependencyResponse, HealthResponse
from app.services.storage import get_storage_service


class HealthService:
    """Handle backend health reporting."""

    async def get_status(self) -> HealthResponse:
        """Return health status for the API, database, and storage layer."""
        checks: dict[str, HealthDependencyResponse] = {}

        try:
            async with get_transaction_session() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = HealthDependencyResponse(status="ok")
        except Exception as error:
            checks["database"] = HealthDependencyResponse(
                status="error",
                detail=str(error),
            )

        try:
            await get_storage_service().ensure_bucket()
            checks["storage"] = HealthDependencyResponse(status="ok")
        except Exception as error:
            checks["storage"] = HealthDependencyResponse(
                status="error",
                detail=str(error),
            )

        overall_status = (
            "ok" if all(item.status == "ok" for item in checks.values()) else "degraded"
        )
        return HealthResponse(
            status=overall_status,
            service="lean-generator-backend",
            checks=checks,
        )
