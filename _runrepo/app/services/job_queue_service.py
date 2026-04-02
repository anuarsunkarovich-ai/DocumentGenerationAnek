"""Queue dispatch helpers for document generation jobs."""

from uuid import UUID

from app.core.request_context import get_context


class JobQueueService:
    """Dispatch document jobs to the background worker queue."""

    def enqueue_generation_job(
        self,
        job_id: UUID,
        *,
        organization_id: UUID | None = None,
        user_id: UUID | None = None,
        template_version_id: UUID | None = None,
    ) -> None:
        """Enqueue one document generation job for worker execution."""
        from app.workers.tasks import process_document_job

        headers = {
            "request_id": get_context()["request_id"],
            "correlation_id": get_context()["correlation_id"],
            "job_id": str(job_id),
            "organization_id": str(organization_id) if organization_id is not None else None,
            "user_id": str(user_id) if user_id is not None else None,
            "template_version_id": (
                str(template_version_id) if template_version_id is not None else None
            ),
        }
        headers = {key: value for key, value in headers.items() if value is not None}
        process_document_job.apply_async(args=[str(job_id)], headers=headers)

    def enqueue_stale_job_recovery(self) -> None:
        """Enqueue a stale-job recovery scan."""
        from app.workers.tasks import recover_stale_document_jobs

        recover_stale_document_jobs.delay()
