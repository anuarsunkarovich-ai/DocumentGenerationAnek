"""Repository for generated document artifacts."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_artifact import DocumentArtifact
from app.models.document_job import DocumentJob
from app.models.enums import ArtifactKind


class DocumentArtifactRepository:
    """Access document artifact records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, artifact: DocumentArtifact) -> DocumentArtifact:
        """Persist an artifact record."""
        self._session.add(artifact)
        await self._session.flush()
        await self._session.refresh(artifact)
        return artifact

    async def list_by_job_id(self, job_id: UUID) -> list[DocumentArtifact]:
        """Return all artifacts produced for a job."""
        statement: Select[tuple[DocumentArtifact]] = select(DocumentArtifact).where(
            DocumentArtifact.document_job_id == job_id
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_reusable_by_job_id(self, job_id: UUID) -> list[DocumentArtifact]:
        """Return non-expired artifacts that can be reused from cache."""
        now = datetime.now(timezone.utc)
        statement: Select[tuple[DocumentArtifact]] = select(DocumentArtifact).where(
            DocumentArtifact.document_job_id == job_id,
            or_(
                DocumentArtifact.expires_at.is_(None),
                DocumentArtifact.expires_at >= now,
            ),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_preferred_for_job(
        self,
        *,
        job_id: UUID,
        preferred_kinds: list[ArtifactKind],
    ) -> DocumentArtifact | None:
        """Return the first matching artifact based on preferred kind order."""
        artifacts = await self.list_by_job_id(job_id)
        for kind in preferred_kinds:
            for artifact in artifacts:
                if artifact.kind == kind:
                    return artifact
        return None

    async def sum_storage_bytes_for_organization(self, organization_id: UUID) -> int:
        """Return the total stored artifact bytes for one organization."""
        statement = select(func.coalesce(func.sum(DocumentArtifact.size_bytes), 0)).where(
            DocumentArtifact.organization_id == organization_id
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def list_by_checksum(
        self,
        *,
        organization_id: UUID,
        checksum: str,
    ) -> list[DocumentArtifact]:
        """Return artifacts whose stored fingerprint matches the provided checksum."""
        statement: Select[tuple[DocumentArtifact]] = (
            select(DocumentArtifact)
            .where(
                DocumentArtifact.organization_id == organization_id,
                DocumentArtifact.checksum == checksum,
            )
            .order_by(desc(DocumentArtifact.created_at))
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def list_expired(
        self,
        *,
        expired_before: datetime,
        limit: int,
    ) -> list[DocumentArtifact]:
        """Return artifacts whose retention window has elapsed."""
        statement: Select[tuple[DocumentArtifact]] = (
            select(DocumentArtifact)
            .where(
                DocumentArtifact.expires_at.is_not(None),
                DocumentArtifact.expires_at < expired_before,
            )
            .order_by(DocumentArtifact.expires_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def expire_for_cache_key(
        self,
        *,
        organization_id: UUID,
        template_version_id: UUID,
        cache_key: str,
        expires_at: datetime,
    ) -> list[DocumentArtifact]:
        """Expire artifacts tied to a cache key so they can no longer be reused."""
        statement: Select[tuple[DocumentArtifact]] = (
            select(DocumentArtifact)
            .join(DocumentJob, DocumentArtifact.document_job_id == DocumentJob.id)
            .where(
                DocumentArtifact.organization_id == organization_id,
                DocumentArtifact.template_version_id == template_version_id,
                DocumentJob.cache_key == cache_key,
            )
        )
        result = await self._session.execute(statement)
        artifacts = list(result.scalars().all())
        for artifact in artifacts:
            artifact.expires_at = expires_at
        if artifacts:
            await self._session.flush()
        return artifacts

    async def delete_artifacts(self, artifacts: list[DocumentArtifact]) -> int:
        """Delete artifact records and return how many were removed."""
        deleted = 0
        for artifact in artifacts:
            await self._session.delete(artifact)
            deleted += 1
        if deleted:
            await self._session.flush()
        return deleted
