"""Release-readiness smoke tests for startup, generation, cache, and audit flows."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

import app.main as main_module
import app.services.document_service as document_service_module
import app.services.generation.document_generation_service as generation_module
import app.services.health_service as health_service_module
from app.dtos.document import DocumentJobCreateRequest
from app.models.document_artifact import DocumentArtifact
from app.models.enums import ArtifactKind, AuditAction, DocumentJobStatus
from app.services.document_service import DocumentService
from app.services.generation.document_generation_service import DocumentGenerationService
from app.services.generation.models import ResolvedTemplateContext
from app.services.template_schema_service import TemplateSchemaService
from tests.conftest import InMemoryStorageService, build_docx_fixture

pytestmark = pytest.mark.integration


def build_template_context() -> ResolvedTemplateContext:
    """Build a realistic generation context using a real DOCX schema extraction."""
    organization_id = uuid4()
    template_id = uuid4()
    template_version_id = uuid4()
    schema = TemplateSchemaService().extract_schema(
        "certificate.docx",
        build_docx_fixture("{{student_name}}", "{{signer_name}}"),
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


def build_job(context: ResolvedTemplateContext) -> SimpleNamespace:
    """Build a queued document job for generation tests."""
    return SimpleNamespace(
        id=uuid4(),
        organization_id=context.organization_id,
        template_id=context.template_id,
        template_version_id=context.template_version_id,
        requested_by_user_id=uuid4(),
        input_payload={
            "organization_id": str(context.organization_id),
            "template_id": str(context.template_id),
            "template_version_id": str(context.template_version_id),
            "requested_by_user_id": str(uuid4()),
            "data": {
                "student_name": "Anek",
                "signer_name": "Dean Office",
            },
            "constructor": {
                "locale": "ru-RU",
                "metadata": {"document_type": "certificate"},
                "blocks": [
                    {
                        "type": "header",
                        "id": "header-1",
                        "text": "Certificate",
                    },
                    {
                        "type": "text",
                        "id": "text-1",
                        "binding": {"key": "student_name"},
                    },
                    {
                        "type": "signature",
                        "id": "signature-1",
                        "signer_name": {"key": "signer_name"},
                    },
                ],
            },
        },
        status=DocumentJobStatus.QUEUED,
        normalized_payload=None,
        cache_key=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
        artifacts=[],
    )


def test_application_startup_ensures_minio_bucket(monkeypatch) -> None:
    """Ensure app startup provisions storage before serving requests."""
    storage = InMemoryStorageService()

    async def fake_dispose() -> None:
        return None

    monkeypatch.setattr(main_module, "get_storage_service", lambda: storage)
    monkeypatch.setattr(main_module.database_manager, "dispose", fake_dispose)
    monkeypatch.setattr(health_service_module, "get_storage_service", lambda: storage)

    with TestClient(main_module.create_application()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert storage.bucket_ensured is True


@pytest.mark.anyio
async def test_generation_pipeline_writes_artifacts_and_audit_logs(monkeypatch) -> None:
    """Ensure one real constructor-driven generation run completes end to end."""
    storage = InMemoryStorageService()
    context = build_template_context()
    job = build_job(context)
    state: dict[str, Any] = {
        "jobs": {job.id: job},
        "audit_events": [],
    }

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            self._state = state

        async def get_by_id(self, job_id, organization_id=None):
            return self._state["jobs"].get(job_id)

        async def mark_processing(self, job_obj, *, normalized_payload, cache_key):
            job_obj.status = DocumentJobStatus.PROCESSING
            job_obj.normalized_payload = normalized_payload
            job_obj.cache_key = cache_key
            job_obj.started_at = datetime.now(timezone.utc)
            return job_obj

        async def mark_completed(self, job_obj):
            job_obj.status = DocumentJobStatus.COMPLETED
            job_obj.completed_at = datetime.now(timezone.utc)
            return job_obj

        async def mark_failed(self, job_obj, error_message: str):
            job_obj.status = DocumentJobStatus.FAILED
            job_obj.error_message = error_message
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
            self._state = state

        async def log_event(self, **payload):
            self._state["audit_events"].append(payload)
            return SimpleNamespace(**payload)

    class FakeArtifactService:
        def __init__(self, session: object, storage_service: InMemoryStorageService) -> None:
            _ = session
            self._storage = storage_service
            self._state = state

        async def store_docx(self, *, context, job_id, user_id, content):
            stored = await self._storage.upload_generated_artifact(
                organization_code=context.organization_code,
                job_id=str(job_id),
                artifact_name=f"{context.template_code}-{context.template_version}.docx",
                content=content,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            artifact = SimpleNamespace(
                id=uuid4(),
                organization_id=context.organization_id,
                document_job_id=job_id,
                template_version_id=context.template_version_id,
                kind=ArtifactKind.DOCX,
                file_name=f"{context.template_code}-{context.template_version}.docx",
                content_type=stored.content_type,
                storage_key=stored.key,
                size_bytes=stored.size_bytes,
                is_cached=False,
            )
            self._state["jobs"][job_id].artifacts.append(artifact)
            self._state["audit_events"].append(
                {"action": AuditAction.ARTIFACT_CREATED, "kind": ArtifactKind.DOCX.value}
            )
            return artifact

        async def store_pdf(self, *, context, job_id, user_id, content):
            stored = await self._storage.upload_generated_artifact(
                organization_code=context.organization_code,
                job_id=str(job_id),
                artifact_name=f"{context.template_code}-{context.template_version}.pdf",
                content=content,
                content_type="application/pdf",
            )
            artifact = SimpleNamespace(
                id=uuid4(),
                organization_id=context.organization_id,
                document_job_id=job_id,
                template_version_id=context.template_version_id,
                kind=ArtifactKind.PDF,
                file_name=f"{context.template_code}-{context.template_version}.pdf",
                content_type=stored.content_type,
                storage_key=stored.key,
                size_bytes=stored.size_bytes,
                is_cached=False,
            )
            self._state["jobs"][job_id].artifacts.append(artifact)
            self._state["audit_events"].append(
                {"action": AuditAction.ARTIFACT_CREATED, "kind": ArtifactKind.PDF.value}
            )
            return artifact

    monkeypatch.setattr(generation_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(generation_module, "get_storage_service", lambda: storage)
    monkeypatch.setattr(generation_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(generation_module, "TemplateResolverService", FakeTemplateResolverService)
    monkeypatch.setattr(generation_module, "AuditService", FakeAuditService)
    monkeypatch.setattr(generation_module, "ArtifactService", FakeArtifactService)

    service = DocumentGenerationService()
    await service.process_job(job.id)

    assert state["jobs"][job.id].status == DocumentJobStatus.COMPLETED
    assert len(state["jobs"][job.id].artifacts) == 2
    assert any(artifact.kind == ArtifactKind.DOCX for artifact in state["jobs"][job.id].artifacts)
    assert any(artifact.kind == ArtifactKind.PDF for artifact in state["jobs"][job.id].artifacts)
    assert any(
        event["action"] == AuditAction.DOCUMENT_JOB_COMPLETED for event in state["audit_events"]
    )
    assert len(storage.objects) == 2


@pytest.mark.anyio
async def test_cached_generation_returns_cached_download_and_audit_logs(monkeypatch) -> None:
    """Ensure cache hits reuse artifacts, expose downloads, and write audit events."""
    storage = InMemoryStorageService()
    context = build_template_context()
    cached_job_id = uuid4()
    cached_artifact = DocumentArtifact(
        organization_id=context.organization_id,
        document_job_id=cached_job_id,
        template_version_id=context.template_version_id,
        kind=ArtifactKind.PDF,
        file_name="certificate-1.0.0.pdf",
        content_type="application/pdf",
        storage_key="artifacts/math-dept/cached/certificate-1.0.0.pdf",
        size_bytes=128,
        is_cached=False,
        checksum="abc123",
    )
    cached_artifact.id = uuid4()
    storage.objects[cached_artifact.storage_key] = b"cached-pdf"

    state: dict[str, Any] = {
        "jobs": {},
        "cache_hit": SimpleNamespace(id=cached_job_id, artifacts=[cached_artifact]),
        "audit_events": [],
    }

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeTemplateResolverService:
        def __init__(self, session: object) -> None:
            _ = session

        async def resolve(self, *, organization_id, template_id, template_version_id):
            return context

    class FakeDocumentRepository:
        def __init__(self, session: object) -> None:
            self._state = state

        async def create(self, job_obj):
            if getattr(job_obj, "id", None) is None:
                job_obj.id = uuid4()
            job_obj.created_at = datetime.now(timezone.utc)
            job_obj.artifacts = []
            self._state["jobs"][job_obj.id] = job_obj
            return job_obj

        async def find_completed_cache_hit(self, **kwargs):
            return self._state["cache_hit"]

        async def mark_processing(self, job_obj, *, normalized_payload, cache_key):
            job_obj.status = DocumentJobStatus.PROCESSING
            job_obj.normalized_payload = normalized_payload
            job_obj.cache_key = cache_key
            job_obj.started_at = datetime.now(timezone.utc)
            return job_obj

        async def mark_completed(self, job_obj):
            job_obj.status = DocumentJobStatus.COMPLETED
            job_obj.completed_at = datetime.now(timezone.utc)
            return job_obj

        async def get_by_id(self, job_id, organization_id=None):
            job_obj = self._state["jobs"].get(job_id)
            if job_obj is None:
                return None
            if organization_id is not None and job_obj.organization_id != organization_id:
                return None
            return job_obj

    class FakeDocumentArtifactRepository:
        def __init__(self, session: object) -> None:
            self._state = state

        async def list_reusable_by_job_id(self, job_id):
            if job_id == cached_job_id:
                return list(self._state["cache_hit"].artifacts)
            return []

        async def get_preferred_for_job(self, *, job_id, preferred_kinds):
            for artifact in self._state["jobs"][job_id].artifacts:
                if artifact.kind in preferred_kinds:
                    return artifact
            return None

    class FakeAuditService:
        def __init__(self, session: object) -> None:
            self._state = state

        async def log_event(self, **payload):
            self._state["audit_events"].append(payload)
            return SimpleNamespace(**payload)

    class FakeArtifactService:
        def __init__(self, session: object, storage_service: InMemoryStorageService) -> None:
            _ = session
            self._storage = storage_service
            self._state = state

        async def reuse_cached_artifacts(self, *, organization_code, job_id, user_id, artifacts):
            cloned = []
            for artifact in artifacts:
                content = await self._storage.download_bytes(artifact.storage_key)
                stored = await self._storage.upload_generated_artifact(
                    organization_code=organization_code,
                    job_id=str(job_id),
                    artifact_name=artifact.file_name,
                    content=content,
                    content_type=artifact.content_type,
                )
                clone = DocumentArtifact(
                    organization_id=artifact.organization_id,
                    document_job_id=job_id,
                    template_version_id=artifact.template_version_id,
                    kind=artifact.kind,
                    file_name=artifact.file_name,
                    content_type=artifact.content_type,
                    storage_key=stored.key,
                    size_bytes=stored.size_bytes,
                    is_cached=True,
                )
                clone.id = uuid4()
                self._state["jobs"][job_id].artifacts.append(clone)
                self._state["audit_events"].append(
                    {"action": AuditAction.ARTIFACT_CREATED, "from_cache": True}
                )
                cloned.append(clone)
            return cloned

    monkeypatch.setattr(document_service_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(document_service_module, "TemplateResolverService", FakeTemplateResolverService)
    monkeypatch.setattr(document_service_module, "DocumentRepository", FakeDocumentRepository)
    monkeypatch.setattr(
        document_service_module,
        "DocumentArtifactRepository",
        FakeDocumentArtifactRepository,
    )
    monkeypatch.setattr(document_service_module, "AuditService", FakeAuditService)
    monkeypatch.setattr(document_service_module, "ArtifactService", FakeArtifactService)

    service = DocumentService()
    service._storage_service = cast(Any, storage)

    payload = DocumentJobCreateRequest.model_validate(
        {
            "organization_id": str(context.organization_id),
            "template_id": str(context.template_id),
            "template_version_id": str(context.template_version_id),
            "requested_by_user_id": str(uuid4()),
            "data": {"student_name": "Anek", "signer_name": "Dean Office"},
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

    response = await service.create_job(payload, BackgroundTasks())
    download = await service.get_download_artifact(
        organization_id=context.organization_id,
        job_id=response.task_id,
    )

    assert response.from_cache is True
    assert response.status == DocumentJobStatus.COMPLETED.value
    assert download.artifact.kind == ArtifactKind.PDF.value
    assert download.artifact.download_url is not None
    assert any(
        event["action"] == AuditAction.DOCUMENT_JOB_CREATED for event in state["audit_events"]
    )
    assert any(
        event["action"] == AuditAction.DOCUMENT_JOB_COMPLETED
        and event["payload"]["from_cache"] is True
        for event in state["audit_events"]
        if "payload" in event
    )
