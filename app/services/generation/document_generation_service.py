"""Orchestrate background document generation jobs."""

import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.metrics import record_job_result
from app.core.request_context import bind_context
from app.dtos.constructor import DocumentConstructor
from app.models.enums import AuditAction
from app.repositories.document_repository import DocumentRepository
from app.services.audit_service import AuditService
from app.services.generation.artifact_service import ArtifactService
from app.services.generation.document_composer_service import DocumentComposerService
from app.services.generation.pdf_render_service import PdfRenderService
from app.services.generation.template_resolver_service import TemplateResolverService
from app.services.generation.variable_mapper_service import VariableMapperService
from app.services.storage import get_storage_service
from app.services.storage.minio import StorageError

logger = logging.getLogger(__name__)


class RetryableGenerationError(Exception):
    """Raised when a job should be retried by the worker."""


class PermanentGenerationError(Exception):
    """Raised when a job has failed permanently."""


class DocumentGenerationService:
    """Run the full document generation pipeline for one job."""

    def __init__(self) -> None:
        """Create the stateless pipeline dependencies."""
        self._storage_service = get_storage_service()
        self._variable_mapper = VariableMapperService()
        self._composer = DocumentComposerService()
        self._pdf_renderer = PdfRenderService()
        self._settings = get_settings()

    async def process_job(self, job_id: UUID) -> bool:
        """Process a queued job end to end in the background."""
        started_at = time.perf_counter()
        try:
            context = None
            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                job = await repository.get_by_id(job_id)
                if job is None:
                    return False
                bind_context(
                    job_id=job.id,
                    organization_id=job.organization_id,
                    user_id=job.requested_by_user_id,
                    template_version_id=job.template_version_id,
                )

                resolver = TemplateResolverService(session)
                context = await resolver.resolve(
                    organization_id=job.organization_id,
                    template_id=job.template_id,
                    template_version_id=job.template_version_id,
                )
                constructor_payload = job.input_payload["constructor"]
                data_payload = job.input_payload.get("data", {})

                constructor = DocumentConstructor.model_validate(constructor_payload)
                resolved_document, normalized_payload, cache_key = (
                    self._variable_mapper.map_document(
                        context=context,
                        constructor=constructor,
                        data=data_payload,
                    )
                )
                stale_before = datetime.now(timezone.utc) - timedelta(
                    seconds=self._settings.worker.stale_job_timeout_seconds
                )
                claimed_job = await repository.claim_for_processing(
                    job_id=job.id,
                    normalized_payload=normalized_payload,
                    cache_key=cache_key,
                    stale_before=stale_before,
                )
                if claimed_job is None:
                    logger.info(
                        "document job claim skipped",
                        extra={"event": "document_job.claim_skipped"},
                    )
                    return False
                logger.info(
                    "document job claimed",
                    extra={"event": "document_job.processing_started"},
                )

            docx_bytes = self._composer.compose(resolved_document)
            pdf_bytes = self._pdf_renderer.render(resolved_document)

            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                job = await repository.get_by_id(job_id)
                if job is None:
                    return False

                audit_service = AuditService(session)
                artifact_service = ArtifactService(session, self._storage_service)
                await artifact_service.store_docx(
                    context=context,
                    job_id=job.id,
                    user_id=job.requested_by_user_id,
                    content=docx_bytes,
                )
                await artifact_service.store_pdf(
                    context=context,
                    job_id=job.id,
                    user_id=job.requested_by_user_id,
                    content=pdf_bytes,
                )
                await repository.mark_completed(job)
                await audit_service.log_event(
                    organization_id=job.organization_id,
                    user_id=job.requested_by_user_id,
                    action=AuditAction.DOCUMENT_JOB_COMPLETED,
                    entity_type="document_job",
                    entity_id=job.id,
                    payload={
                        "template_id": str(job.template_id),
                        "template_version_id": str(job.template_version_id),
                        "from_cache": False,
                    },
                )
            duration_seconds = time.perf_counter() - started_at
            record_job_result(result="success", duration_seconds=duration_seconds)
            logger.info(
                "document job completed",
                extra={
                    "event": "document_job.completed",
                    "duration_ms": round(duration_seconds * 1000, 2),
                },
            )
            return True
        except Exception as error:
            if self._is_retryable_error(error):
                await self._requeue_job(job_id, str(error))
                duration_seconds = time.perf_counter() - started_at
                record_job_result(result="retryable_failure", duration_seconds=duration_seconds)
                logger.warning(
                    "document job hit retryable failure",
                    extra={
                        "event": "document_job.retryable_failure",
                        "duration_ms": round(duration_seconds * 1000, 2),
                        "error": str(error),
                    },
                )
                raise RetryableGenerationError(str(error)) from error
            await self._mark_failed_job(job_id, str(error))
            duration_seconds = time.perf_counter() - started_at
            record_job_result(result="failure", duration_seconds=duration_seconds)
            logger.error(
                "document job failed permanently",
                extra={
                    "event": "document_job.failed",
                    "duration_ms": round(duration_seconds * 1000, 2),
                    "error": str(error),
                },
            )
            raise PermanentGenerationError(str(error)) from error

    async def recover_stale_jobs(self) -> list[UUID]:
        """Reset stale processing jobs back to queued so workers can pick them up again."""
        stale_before = datetime.now(timezone.utc) - timedelta(
            seconds=self._settings.worker.stale_job_timeout_seconds
        )
        async with get_transaction_session() as session:
            repository = DocumentRepository(session)
            recovered_job_ids = await repository.recover_stale_processing_jobs(
                stale_before=stale_before,
                limit=self._settings.worker.stale_job_recovery_batch_size,
            )
            if recovered_job_ids:
                logger.warning(
                    "recovered stale document jobs",
                    extra={
                        "event": "document_job.stale_recovered",
                        "recovered_count": len(recovered_job_ids),
                    },
                )
            return recovered_job_ids

    def _is_retryable_error(self, error: Exception) -> bool:
        """Return whether a generation failure is likely transient."""
        if isinstance(
            error,
            (
                AuthenticationError,
                AuthorizationError,
                ConflictError,
                NotFoundError,
                ValidationError,
                PermanentGenerationError,
            ),
        ):
            return False
        return isinstance(error, (StorageError, TimeoutError, ConnectionError, OSError))

    async def _requeue_job(self, job_id: UUID, error_message: str) -> None:
        """Move a transiently failed job back to queued."""
        async with get_transaction_session() as session:
            repository = DocumentRepository(session)
            job = await repository.get_by_id(job_id)
            if job is not None:
                await repository.requeue(job, error_message=error_message)

    async def _mark_failed_job(self, job_id: UUID, error_message: str) -> None:
        """Persist a permanent job failure and write the audit log."""
        async with get_transaction_session() as session:
            repository = DocumentRepository(session)
            audit_service = AuditService(session)
            job = await repository.get_by_id(job_id)
            if job is not None:
                await repository.mark_failed(job, error_message)
                await audit_service.log_event(
                    organization_id=job.organization_id,
                    user_id=job.requested_by_user_id,
                    action=AuditAction.DOCUMENT_JOB_FAILED,
                    entity_type="document_job",
                    entity_id=job.id,
                    payload={
                        "template_id": str(job.template_id),
                        "template_version_id": str(job.template_version_id),
                        "error_message": error_message,
                        "from_cache": False,
                    },
                )
