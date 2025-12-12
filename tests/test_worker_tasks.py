"""Worker and queue orchestration tests for document generation."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi import BackgroundTasks

import app.services.document_service as document_service_module
import app.services.generation.document_generation_service as generation_module
import app.workers.tasks as worker_tasks
from app.core.exceptions import ValidationError
from app.dtos.document import DocumentJobCreateRequest
from app.models.enums import DocumentJobStatus
from app.services.document_service import DocumentService
from app.services.generation.document_generation_service import (
    DocumentGenerationService,
    PermanentGenerationError,
    RetryableGenerationError,
)
from app.services.generation.models import ResolvedTemplateContext
from app.services.storage.minio import StorageError
from app.services.template_schema_service import TemplateSchemaService
from tests.conftest import build_docx_fixture


def build_template_context() -> ResolvedTemplateContext:
    """Build a realistic template context for queue-orchestration tests."""
    organization_id = uuid4()
    template_id = uuid4()
    template_version_id = uuid4()
    schema = TemplateSchemaService().extract_schema(
        "certificate.docx",
        build_docx_fixture("{{student_name}}"),
    )
    return ResolvedTemplateContext(
        template_id=template_id,
        template_version_id=template_version_id,
        organization_id=organization_id,
        organization_code="math-dept",
        template_code="certificate",
        template_name="Certificate",
        template_version="1.0.0",
        original_filename="certificate.docx",
        variable_schema=schema.model_dump(mode="json"),
    )


def build_payload(context: ResolvedTemplateContext) -> DocumentJobCreateRequest:
    """Build a minimal valid job payload."""
    return DocumentJobCreateRequest.model_validate(
        {
            "organization_id": str(context.organization_id),
            "template_id": str(context.template_id),
            "template_version_id": str(context.template_version_id),
            "data": {"student_name": "Anek"},
            "constructor": {
                "blocks": [
                    {
                        "type": "text",
                        "id": "text-1",
                        "binding": {"key": "student_name"},
                    }
                ]
            },
        }
    )


class FakeTask:
    """Minimal Celery task stub for retry assertions."""

    def __init__(self, retries: int = 0) -> None:
        self.request = SimpleNamespace(retries=retries)
        self.retry_kwargs: dict[str, object] | None = None

    def retry(self, **kwargs: object) -> None:
        """Capture retry details and raise a sentinel error."""
        self.retry_kwargs = kwargs
        raise RuntimeError("retry requested")


def test_process_document_job_succeeds_without_retry() -> None:
    """Worker task should return the generation result on success."""

    class FakeService:
        async def process_job(self, job_id: UUID) -> bool:
            assert isinstance(job_id, UUID)
            return True

    result = worker_tasks._run_process_document_job(
        FakeTask(),
        job_id=uuid4(),
        service=FakeService(),
    )

    assert result is True


def test_process_document_job_retries_retryable_failure() -> None:
    """Retryable generation failures should map to Celery retry calls."""

    class FakeService:
        async def process_job(self, job_id: UUID) -> bool:
            _ = job_id
            raise RetryableGenerationError("temporary storage issue")

    task = FakeTask(retries=2)

    with pytest.raises(RuntimeError, match="retry requested"):
        worker_tasks._run_process_document_job(task, job_id=uuid4(), service=FakeService())

    assert task.retry_kwargs is not None
    assert task.retry_kwargs["countdown"] == worker_tasks.retry_delay_for_attempt(2)
    assert task.retry_kwargs["max_retries"] == worker_tasks.get_settings().worker.max_retries


def test_process_document_job_propagates_permanent_failure() -> None:
    """Permanent generation failures should not be retried by the task wrapper."""

    class FakeService:
        async def process_job(self, job_id: UUID) -> bool:
            _ = job_id
            raise PermanentGenerationError("template data is invalid")

    with pytest.raises(PermanentGenerationError, match="template data is invalid"):
        worker_tasks._run_process_document_job(FakeTask(), job_id=uuid4(), service=FakeService())


def test_recover_stale_document_jobs_requeues_recovered_ids() -> None:
    """Recovered stale jobs should be returned and re-enqueued for processing."""
    recovered_job_ids = [uuid4(), uuid4()]
    enqueued_job_ids: list[UUID] = []

    class FakeService:
        async def recover_stale_jobs(self) -> list[UUID]:
            return recovered_job_ids

    result = worker_tasks._run_recover_stale_document_jobs(
        service=FakeService(),
        enqueue_job=enqueued_job_ids.append,
    )

    assert result == [str(job_id) for job_id in recovered_job_ids]
    assert enqueued_job_ids == recovered_job_ids


@pytest.mark.anyio
async def test_document_generation_service_skips_duplicate_claim(monkeypatch) -> None:
    """Duplicate worker deliveries should no-op when the job cannot be claimed."""
    context = build_template_context()
    job = SimpleNamespace(
        id=uuid4(),
        organization_id=context.organization_id,
        template_id=context.template_id,
        template_version_id=context.template_version_id,
        requested_by_user_id=uuid4(),
        input_payload=build_payload(context).model_dump(mode="json"),
        status=DocumentJobStatus.PROCESSING,
        normalized_payload=None,
        cache_key=None,
        error_message=None,
        started_at=datetime.now(timezone.utc),
        completed_at=None,
        artifacts=[],
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, job_id, organization_id=None):
            _ = organization_id
            if job_id == job.id:
                return job
            return None

        async def claim_for_processing(self, *, job_id, normalized_payload, cache_key, stale_before):
            _ = job_id, normalized_payload, cache_key, stale_before
            return None

    class FakeTemplateResolverService:
        def __init__(self, session: object) -> None:
            _ = session

        async def resolve(self, *, organization_id, template_id, template_version_id):
            assert organization_id == context.organization_id
            assert template_id == context.template_id
            assert template_version_id == context.template_version_id
            return context

    monkeypatch.setattr(generation_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(generation_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(generation_module, "TemplateResolverService", FakeTemplateResolverService)

    service = DocumentGenerationService()
    result = await service.process_job(job.id)

    assert result is False


@pytest.mark.anyio
async def test_document_generation_service_requeues_retryable_failure(monkeypatch) -> None:
    """Transient generation errors should move the job back to queued."""
    context = build_template_context()
    job = SimpleNamespace(
        id=uuid4(),
        organization_id=context.organization_id,
        template_id=context.template_id,
        template_version_id=context.template_version_id,
        requested_by_user_id=uuid4(),
        input_payload=build_payload(context).model_dump(mode="json"),
        status=DocumentJobStatus.QUEUED,
        normalized_payload=None,
        cache_key=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        artifacts=[],
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, job_id, organization_id=None):
            _ = organization_id
            if job_id == job.id:
                return job
            return None

        async def claim_for_processing(self, *, job_id, normalized_payload, cache_key, stale_before):
            _ = stale_before
            if job_id != job.id:
                return None
            job.status = DocumentJobStatus.PROCESSING
            job.normalized_payload = normalized_payload
            job.cache_key = cache_key
            job.started_at = datetime.now(timezone.utc)
            return job

        async def requeue(self, job_obj, *, error_message=None):
            job_obj.status = DocumentJobStatus.QUEUED
            job_obj.error_message = error_message
            job_obj.started_at = None
            return job_obj

    class FakeTemplateResolverService:
        def __init__(self, session: object) -> None:
            _ = session

        async def resolve(self, *, organization_id, template_id, template_version_id):
            assert organization_id == context.organization_id
            assert template_id == context.template_id
            assert template_version_id == context.template_version_id
            return context

    class RetryableComposer:
        def compose(self, resolved_document: object) -> bytes:
            _ = resolved_document
            raise StorageError("temporary storage issue")

    monkeypatch.setattr(generation_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(generation_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(generation_module, "TemplateResolverService", FakeTemplateResolverService)

    service = DocumentGenerationService()
    service._composer = RetryableComposer()  # type: ignore[assignment]

    with pytest.raises(RetryableGenerationError, match="temporary storage issue"):
        await service.process_job(job.id)

    assert job.status == DocumentJobStatus.QUEUED
    assert job.error_message == "temporary storage issue"
    assert job.started_at is None


@pytest.mark.anyio
async def test_document_generation_service_marks_permanent_failure(monkeypatch) -> None:
    """Deterministic validation errors should fail the job permanently."""
    context = build_template_context()
    job = SimpleNamespace(
        id=uuid4(),
        organization_id=context.organization_id,
        template_id=context.template_id,
        template_version_id=context.template_version_id,
        requested_by_user_id=uuid4(),
        input_payload=build_payload(context).model_dump(mode="json"),
        status=DocumentJobStatus.QUEUED,
        normalized_payload=None,
        cache_key=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        artifacts=[],
    )
    audit_events: list[dict[str, object]] = []

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, job_id, organization_id=None):
            _ = organization_id
            if job_id == job.id:
                return job
            return None

        async def claim_for_processing(self, *, job_id, normalized_payload, cache_key, stale_before):
            _ = stale_before
            if job_id != job.id:
                return None
            job.status = DocumentJobStatus.PROCESSING
            job.normalized_payload = normalized_payload
            job.cache_key = cache_key
            job.started_at = datetime.now(timezone.utc)
            return job

        async def mark_failed(self, job_obj, error_message: str):
            job_obj.status = DocumentJobStatus.FAILED
            job_obj.error_message = error_message
            job_obj.completed_at = datetime.now(timezone.utc)
            return job_obj

    class FakeTemplateResolverService:
        def __init__(self, session: object) -> None:
            _ = session

        async def resolve(self, *, organization_id, template_id, template_version_id):
            assert organization_id == context.organization_id
            assert template_id == context.template_id
            assert template_version_id == context.template_version_id
            return context

    class FakeAuditService:
        def __init__(self, session: object) -> None:
            _ = session

        async def log_event(self, **payload):
            audit_events.append(payload)
            return SimpleNamespace(**payload)

    class PermanentFailureComposer:
        def compose(self, resolved_document: object) -> bytes:
            _ = resolved_document
            raise ValidationError("template data is invalid")

    monkeypatch.setattr(generation_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(generation_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(generation_module, "TemplateResolverService", FakeTemplateResolverService)
    monkeypatch.setattr(generation_module, "AuditService", FakeAuditService)

    service = DocumentGenerationService()
    service._composer = PermanentFailureComposer()  # type: ignore[assignment]

    with pytest.raises(PermanentGenerationError, match="template data is invalid"):
        await service.process_job(job.id)

    assert job.status == DocumentJobStatus.FAILED
    assert job.error_message == "template data is invalid"
    assert job.completed_at is not None
    assert any(getattr(event["action"], "value", None) == "document_job_failed" for event in audit_events)


@pytest.mark.anyio
async def test_document_service_enqueues_generation_job(monkeypatch) -> None:
    """DocumentService should enqueue Celery work while preserving the API contract."""
    context = build_template_context()
    payload = build_payload(context)
    enqueued_job_ids: list[UUID] = []
    state: dict[str, object] = {}

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeTemplateResolverService:
        def __init__(self, session: object) -> None:
            _ = session

        async def resolve(self, *, organization_id, template_id, template_version_id):
            assert organization_id == context.organization_id
            assert template_id == context.template_id
            assert template_version_id == context.template_version_id
            return context

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def create(self, job_obj):
            if getattr(job_obj, "id", None) is None:
                job_obj.id = uuid4()
            job_obj.created_at = datetime.now(timezone.utc)
            job_obj.artifacts = []
            state["job"] = job_obj
            return job_obj

        async def find_completed_cache_hit(self, **kwargs):
            _ = kwargs
            return None

    class FakeAuditService:
        def __init__(self, session: object) -> None:
            _ = session

        async def log_event(self, **payload):
            _ = payload
            return SimpleNamespace(**payload)

    class FakeQueueService:
        def enqueue_generation_job(
            self,
            job_id: UUID,
            *,
            organization_id=None,
            user_id=None,
            template_version_id=None,
        ) -> None:
            _ = organization_id, user_id, template_version_id
            enqueued_job_ids.append(job_id)

    monkeypatch.setattr(document_service_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(document_service_module, "TemplateResolverService", FakeTemplateResolverService)
    monkeypatch.setattr(document_service_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(document_service_module, "AuditService", FakeAuditService)

    service = DocumentService()
    cast(Any, service)._job_queue_service = FakeQueueService()

    response = await service.create_job(
        payload,
        BackgroundTasks(),
        current_user_id=uuid4(),
    )

    assert response.status == DocumentJobStatus.QUEUED.value
    assert response.from_cache is False
    assert enqueued_job_ids == [response.task_id]
