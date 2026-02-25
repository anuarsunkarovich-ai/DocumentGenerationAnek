"""Repository for generated document artifacts."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_artifact import DocumentArtifact
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
