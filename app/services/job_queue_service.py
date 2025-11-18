"""Queue dispatch helpers for document generation jobs."""

from uuid import UUID


class JobQueueService:
    """Dispatch document jobs to the background worker queue."""

    def enqueue_generation_job(self, job_id: UUID) -> None:
        """Enqueue one document generation job for worker execution."""
        from app.workers.tasks import process_document_job

        process_document_job.delay(str(job_id))

    def enqueue_stale_job_recovery(self) -> None:
        """Enqueue a stale-job recovery scan."""
        from app.workers.tasks import recover_stale_document_jobs

        recover_stale_document_jobs.delay()
