"""Repository for document job persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document_job import DocumentJob
from app.models.enums import DocumentJobStatus


class DocumentRepository:
    """Access document job records."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the active database session."""
        self._session = session

    async def create(self, job: DocumentJob) -> DocumentJob:
        """Persist a document job."""
        self._session.add(job)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def get_by_id(
        self,
        job_id: UUID,
        *,
        organization_id: UUID | None = None,
    ) -> DocumentJob | None:
        """Return a document job with related artifacts and template version."""
        statement: Select[tuple[DocumentJob]] = (
            select(DocumentJob)
            .options(
                selectinload(DocumentJob.artifacts),
                selectinload(DocumentJob.template),
                selectinload(DocumentJob.template_version),
                selectinload(DocumentJob.organization),
            )
            .where(DocumentJob.id == job_id)
        )
        if organization_id is not None:
            statement = statement.where(DocumentJob.organization_id == organization_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def mark_processing(
        self,
        job: DocumentJob,
        *,
        normalized_payload: dict,
        cache_key: str,
    ) -> DocumentJob:
        """Mark a queued job as processing."""
        job.status = DocumentJobStatus.PROCESSING
        job.normalized_payload = normalized_payload
        job.cache_key = cache_key
        job.started_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_completed(self, job: DocumentJob) -> DocumentJob:
        """Mark a job as completed."""
        job.status = DocumentJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = None
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def mark_failed(self, job: DocumentJob, error_message: str) -> DocumentJob:
        """Mark a job as failed and store the failure message."""
        job.status = DocumentJobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        await self._session.flush()
        await self._session.refresh(job)
        return job

    async def find_completed_cache_hit(
        self,
        *,
        organization_id: UUID,
        template_version_id: UUID,
        cache_key: str,
    ) -> DocumentJob | None:
        """Return the most recent completed job with the same cache key."""
        statement: Select[tuple[DocumentJob]] = (
            select(DocumentJob)
            .options(selectinload(DocumentJob.artifacts))
            .where(
                DocumentJob.organization_id == organization_id,
                DocumentJob.template_version_id == template_version_id,
                DocumentJob.cache_key == cache_key,
                DocumentJob.status == DocumentJobStatus.COMPLETED,
            )
            .order_by(desc(DocumentJob.completed_at))
        )
        result = await self._session.execute(statement)
        return result.scalars().first()
