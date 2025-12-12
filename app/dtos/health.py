"""DTOs for health-check responses."""

from pydantic import Field

from app.dtos.common import BaseDTO


class HealthDependencyResponse(BaseDTO):
    """Health state for one infrastructure dependency."""

    status: str
    detail: str | None = None


class HealthResponse(BaseDTO):
    """Health endpoint response model."""

    status: str
    service: str
    checks: dict[str, HealthDependencyResponse] = Field(default_factory=dict)


class LiveHealthResponse(BaseDTO):
    """Liveness response model."""

    status: str
    service: str
