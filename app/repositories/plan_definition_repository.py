"""Repository for subscription plan definitions."""

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan_definition import PlanDefinition


class PlanDefinitionRepository:
    """Access plan definitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> PlanDefinition | None:
        """Return one active plan by code."""
        statement: Select[tuple[PlanDefinition]] = select(PlanDefinition).where(
            PlanDefinition.code == code
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
