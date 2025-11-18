"""Celery tasks for document-generation work."""

import asyncio
from typing import Any, Protocol
from uuid import UUID

from celery.signals import worker_ready

from app.core.config import get_settings
from app.services.generation.document_generation_service import (
    DocumentGenerationService,
    RetryableGenerationError,
)
from app.workers.celery_app import celery_app


class ProcessJobService(Protocol):
    """Protocol for services that can process one job."""

    async def process_job(self, job_id: UUID) -> bool: ...


class RecoverStaleJobsService(Protocol):
    """Protocol for services that can recover stale jobs."""

    async def recover_stale_jobs(self) -> list[UUID]: ...


def retry_delay_for_attempt(retry_count: int) -> int:
    """Return the retry delay using exponential backoff."""
    base_delay = get_settings().worker.retry_backoff_seconds
    return base_delay * (2**retry_count)


def _enqueue_process_document_job(job_id: UUID) -> None:
    """Queue one document generation task."""
    process_document_job.delay(str(job_id))


def _run_process_document_job(
    task: Any,
    *,
    job_id: UUID,
    service: ProcessJobService | None = None,
) -> bool:
    """Execute one document generation task and translate retryable failures."""
    generation_service = service or DocumentGenerationService()
    try:
        return asyncio.run(generation_service.process_job(job_id))
    except RetryableGenerationError as error:
        countdown = retry_delay_for_attempt(task.request.retries)
        raise task.retry(
            exc=error,
            countdown=countdown,
            max_retries=get_settings().worker.max_retries,
        ) from error


def _run_recover_stale_document_jobs(
    *,
    service: RecoverStaleJobsService | None = None,
    enqueue_job: Any = _enqueue_process_document_job,
) -> list[str]:
    """Recover stale jobs and re-enqueue them for processing."""
    generation_service = service or DocumentGenerationService()
    recovered_job_ids = asyncio.run(generation_service.recover_stale_jobs())
    for job_id in recovered_job_ids:
        enqueue_job(job_id)
    return [str(job_id) for job_id in recovered_job_ids]


@celery_app.task(
    bind=True,
    name="document_jobs.process",
    max_retries=get_settings().worker.max_retries,
)
def process_document_job(self, job_id: str) -> bool:
    """Process one document generation job in the worker."""
    return _run_process_document_job(self, job_id=UUID(job_id))


@celery_app.task(bind=True, name="document_jobs.recover_stale")
def recover_stale_document_jobs(self) -> list[str]:
    """Requeue stale processing jobs after worker restarts or interruptions."""
    _ = self
    return _run_recover_stale_document_jobs()


@worker_ready.connect
def queue_stale_document_job_recovery(sender, **kwargs) -> None:
    """Trigger stale-job recovery when a worker comes online."""
    _ = sender, kwargs
    recover_stale_document_jobs.delay()
