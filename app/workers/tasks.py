"""Celery tasks for document-generation work."""

import asyncio
import logging
from typing import Any, Protocol
from uuid import UUID

from celery.signals import worker_process_init, worker_ready

from app.core.config import get_settings
from app.core.database import reset_database_manager
from app.core.request_context import bind_context, clear_context
from app.services.generation.document_generation_service import (
    DocumentGenerationService,
    RetryableGenerationError,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


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
    reset_database_manager()
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
    reset_database_manager()
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
    headers = getattr(self.request, "headers", {}) or {}
    bind_context(
        request_id=headers.get("request_id"),
        correlation_id=headers.get("correlation_id"),
        job_id=headers.get("job_id") or job_id,
        organization_id=headers.get("organization_id"),
        user_id=headers.get("user_id"),
        template_version_id=headers.get("template_version_id"),
    )
    logger.info(
        "worker received document job",
        extra={
            "event": "document_job.worker_received",
        },
    )
    try:
        return _run_process_document_job(self, job_id=UUID(job_id))
    finally:
        clear_context()


@celery_app.task(bind=True, name="document_jobs.recover_stale")
def recover_stale_document_jobs(self) -> list[str]:
    """Requeue stale processing jobs after worker restarts or interruptions."""
    _ = self
    try:
        return _run_recover_stale_document_jobs()
    finally:
        clear_context()


@worker_ready.connect
def queue_stale_document_job_recovery(sender, **kwargs) -> None:
    """Trigger stale-job recovery when a worker comes online."""
    _ = sender, kwargs
    recover_stale_document_jobs.delay()


@worker_process_init.connect
def reinitialize_worker_process_state(**kwargs) -> None:
    """Recreate process-local database resources for Celery child workers."""
    _ = kwargs
    reset_database_manager()
