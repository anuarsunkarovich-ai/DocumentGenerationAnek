"""Repository for API-key persistence and lookup."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey


class ApiKeyRepository:
    """Access API-key records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, api_key: ApiKey) -> ApiKey:
        """Persist one API key."""
        self._session.add(api_key)
        await self._session.flush()
        await self._session.refresh(api_key)
        return api_key

    async def list_for_organization(self, organization_id: UUID) -> list[ApiKey]:
        """Return API keys for one organization."""
        statement: Select[tuple[ApiKey]] = (
            select(ApiKey)
            .where(ApiKey.organization_id == organization_id)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, api_key_id: UUID, *, organization_id: UUID | None = None) -> ApiKey | None:
        """Return one API key by identifier."""
        statement: Select[tuple[ApiKey]] = select(ApiKey).where(ApiKey.id == api_key_id)
        if organization_id is not None:
            statement = statement.where(ApiKey.organization_id == organization_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_hashed_key(self, hashed_key: str) -> ApiKey | None:
        """Return one API key by its hashed secret."""
        statement: Select[tuple[ApiKey]] = (
            select(ApiKey)
            .options(selectinload(ApiKey.organization))
            .where(ApiKey.hashed_key == hashed_key)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def revoke(self, api_key: ApiKey) -> ApiKey:
        """Mark one API key as revoked."""
        api_key.status = "revoked"
        api_key.revoked_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(api_key)
        return api_key

    async def set_status(self, api_key: ApiKey, *, status: str) -> ApiKey:
        """Update the operational status for one API key."""
        api_key.status = status
        if status != "revoked":
            api_key.revoked_at = None
        await self._session.flush()
        await self._session.refresh(api_key)
        return api_key

    async def rotate(
        self,
        api_key: ApiKey,
        *,
        key_prefix: str,
        hashed_key: str,
    ) -> ApiKey:
        """Replace the stored secret material for one API key."""
        api_key.key_prefix = key_prefix
        api_key.hashed_key = hashed_key
        api_key.rotated_at = datetime.now(timezone.utc)
        api_key.status = "active"
        api_key.revoked_at = None
        api_key.last_used_at = None
        await self._session.flush()
        await self._session.refresh(api_key)
        return api_key

    async def touch(self, api_key: ApiKey) -> ApiKey:
        """Update the last-used timestamp for one API key."""
        api_key.last_used_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(api_key)
        return api_key
