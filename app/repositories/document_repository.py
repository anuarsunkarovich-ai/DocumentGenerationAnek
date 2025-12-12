"""Repository for document job persistence."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Select, desc, distinct, func, select
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

    async def claim_for_processing(
        self,
        *,
        job_id: UUID,
        normalized_payload: dict,
        cache_key: str,
        stale_before: datetime | None = None,
    ) -> DocumentJob | None:
        """Claim one queued or stale-processing job for worker execution."""
        statement: Select[tuple[DocumentJob]] = (
            select(DocumentJob)
            .where(DocumentJob.id == job_id)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(statement)
        job = result.scalar_one_or_none()
        if job is None:
            return None

        is_stale_processing = (
            stale_before is not None
            and job.status == DocumentJobStatus.PROCESSING
            and job.started_at is not None
            and job.started_at <= stale_before
        )
        if job.status != DocumentJobStatus.QUEUED and not is_stale_processing:
            return None

        job.status = DocumentJobStatus.PROCESSING
        job.normalized_payload = normalized_payload
        job.cache_key = cache_key
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None
        job.error_message = None
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

    async def requeue(self, job: DocumentJob, *, error_message: str | None = None) -> DocumentJob:
        """Move a job back to queued after a transient worker failure."""
        job.status = DocumentJobStatus.QUEUED
        job.started_at = None
        job.completed_at = None
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

    async def list_failed_jobs(
        self,
        *,
        organization_id: UUID,
        limit: int,
    ) -> list[DocumentJob]:
        """Return recent failed jobs for one organization."""
        statement: Select[tuple[DocumentJob]] = (
            select(DocumentJob)
            .options(
                selectinload(DocumentJob.artifacts),
                selectinload(DocumentJob.template),
                selectinload(DocumentJob.template_version),
            )
            .where(
                DocumentJob.organization_id == organization_id,
                DocumentJob.status == DocumentJobStatus.FAILED,
            )
            .order_by(desc(DocumentJob.completed_at), desc(DocumentJob.created_at))
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_cache_stats(
        self,
        *,
        organization_id: UUID,
    ) -> dict[str, int]:
        """Return basic cache usage stats for one organization."""
        from app.models.document_artifact import DocumentArtifact

        completed_jobs_query = await self._session.execute(
            select(func.count(DocumentJob.id)).where(
                DocumentJob.organization_id == organization_id,
                DocumentJob.status == DocumentJobStatus.COMPLETED,
            )
        )
        cached_jobs_query = await self._session.execute(
            select(func.count(distinct(DocumentJob.id)))
            .join(DocumentArtifact, DocumentArtifact.document_job_id == DocumentJob.id)
            .where(
                DocumentJob.organization_id == organization_id,
                DocumentJob.status == DocumentJobStatus.COMPLETED,
                DocumentArtifact.is_cached.is_(True),
            )
        )
        cached_artifacts_query = await self._session.execute(
            select(func.count(DocumentArtifact.id)).where(
                DocumentArtifact.organization_id == organization_id,
                DocumentArtifact.is_cached.is_(True),
            )
        )

        return {
            "completed_jobs": int(completed_jobs_query.scalar_one() or 0),
            "cached_jobs": int(cached_jobs_query.scalar_one() or 0),
            "cached_artifacts": int(cached_artifacts_query.scalar_one() or 0),
        }

    async def recover_stale_processing_jobs(
        self,
        *,
        stale_before: datetime,
        limit: int,
    ) -> list[UUID]:
        """Reset stale processing jobs back to queued and return their identifiers."""
        statement: Select[tuple[DocumentJob]] = (
            select(DocumentJob)
            .where(
                DocumentJob.status == DocumentJobStatus.PROCESSING,
                DocumentJob.started_at.is_not(None),
                DocumentJob.started_at <= stale_before,
            )
            .order_by(DocumentJob.started_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(statement)
        jobs = list(result.scalars().all())
        recovered_job_ids: list[UUID] = []
        for job in jobs:
            job.status = DocumentJobStatus.QUEUED
            job.started_at = None
            job.completed_at = None
            job.error_message = "Recovered stale processing job."
            recovered_job_ids.append(job.id)
        if jobs:
            await self._session.flush()
        return recovered_job_ids
