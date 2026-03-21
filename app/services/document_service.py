"""Application services for document generation."""

import logging
from uuid import UUID

from fastapi import BackgroundTasks

from app.core.database import get_transaction_session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.metrics import record_cache_event
from app.core.request_context import bind_context
from app.dtos.constructor import DocumentConstructor, GOSTFormattingRules
from app.dtos.document import (
    ConstructorSchemaResponse,
    DocumentArtifactAccessResponse,
    DocumentArtifactResponse,
    DocumentJobCreateRequest,
    DocumentJobResponse,
    DocumentJobStatusResponse,
    DocumentVerificationResponse,
    ImportedTemplateDocumentJobCreateRequest,
)
from app.models.document_job import DocumentJob
from app.models.enums import ArtifactKind, AuditAction, DocumentJobStatus
from app.repositories.document_artifact_repository import DocumentArtifactRepository
from app.repositories.document_repository import DocumentRepository
from app.services.audit_service import AuditService
from app.services.billing_service import BillingService
from app.services.document_verification_service import DocumentVerificationService
from app.services.generation.artifact_service import ArtifactService
from app.services.generation.docx_template_render_service import DocxTemplateRenderService
from app.services.generation.template_resolver_service import TemplateResolverService
from app.services.generation.variable_mapper_service import VariableMapperService
from app.services.job_queue_service import JobQueueService
from app.services.storage import get_storage_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Handle document generation orchestration."""

    def __init__(self) -> None:
        """Configure background pipeline dependencies."""
        self._storage_service = get_storage_service()
        self._variable_mapper = VariableMapperService()
        self._import_renderer = DocxTemplateRenderService()
        self._job_queue_service = JobQueueService()
        self._billing_service = BillingService()
        self._verification_service = DocumentVerificationService()

    async def create_job(
        self,
        payload: DocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id: UUID | None,
        current_api_key_id: UUID | None = None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        """Queue a document job and return the task metadata immediately."""
        _ = background_tasks
        async with get_transaction_session() as session:
            resolver = TemplateResolverService(session)
            context = await resolver.resolve(
                organization_id=payload.organization_id,
                template_id=payload.template_id,
                template_version_id=payload.template_version_id,
                require_published=require_published_template,
            )
            if context.render_strategy == "docx_import":
                raise ValidationError(
                    "This template version requires imported-DOCX generation."
                )
            constructor = DocumentConstructor.model_validate(payload.constructor)
            await self._billing_service.enforce_generation_allowed(
                organization_id=payload.organization_id,
                constructor=constructor,
                session=session,
            )
            _, normalized_payload, cache_key = self._variable_mapper.map_document(
                context=context,
                constructor=constructor,
                data=payload.data,
            )

            repository = DocumentRepository(session)
            audit_service = AuditService(session)
            job = await repository.create(
                DocumentJob(
                    organization_id=context.organization_id,
                    template_id=context.template_id,
                    template_version_id=context.template_version_id,
                    requested_by_user_id=current_user_id,
                    status=DocumentJobStatus.QUEUED,
                    input_payload=payload.model_dump(mode="json"),
                    normalized_payload=normalized_payload,
                    cache_key=cache_key,
                )
            )
            await self._billing_service.record_generation_request(
                organization_id=job.organization_id,
                constructor=constructor,
                session=session,
            )
            bind_context(
                job_id=job.id,
                organization_id=job.organization_id,
                user_id=current_user_id,
                api_key_id=current_api_key_id,
                template_version_id=job.template_version_id,
            )
            await audit_service.log_event(
                organization_id=job.organization_id,
                user_id=current_user_id,
                action=AuditAction.DOCUMENT_JOB_CREATED,
                entity_type="document_job",
                entity_id=job.id,
                payload={
                    "template_id": str(job.template_id),
                    "template_version_id": str(job.template_version_id),
                    "cache_key": cache_key,
                    "from_cache": False,
                    "api_key_id": str(current_api_key_id) if current_api_key_id else None,
                },
            )

            cached_job = await repository.find_completed_cache_hit(
                organization_id=context.organization_id,
                template_version_id=context.template_version_id,
                cache_key=cache_key,
            )
            if cached_job is not None and cached_job.id != job.id:
                artifact_repository = DocumentArtifactRepository(session)
                cached_artifacts = await artifact_repository.list_reusable_by_job_id(cached_job.id)
                if cached_artifacts:
                    cached_storage_bytes = sum(int(artifact.size_bytes or 0) for artifact in cached_artifacts)
                    await self._billing_service.enforce_storage_delta_allowed(
                        organization_id=job.organization_id,
                        additional_bytes=cached_storage_bytes,
                        session=session,
                    )
                    artifact_service = ArtifactService(session, self._storage_service)
                    await artifact_service.reuse_cached_artifacts(
                        organization_code=context.organization_code,
                        job_id=job.id,
                        user_id=current_user_id,
                        artifacts=cached_artifacts,
                    )
                    await repository.mark_processing(
                        job,
                        normalized_payload=normalized_payload,
                        cache_key=cache_key,
                    )
                    await repository.mark_completed(job)
                    await audit_service.log_event(
                        organization_id=job.organization_id,
                        user_id=current_user_id,
                        action=AuditAction.DOCUMENT_JOB_COMPLETED,
                        entity_type="document_job",
                        entity_id=job.id,
                        payload={
                            "template_id": str(job.template_id),
                            "template_version_id": str(job.template_version_id),
                            "from_cache": True,
                            "reused_from_job_id": str(cached_job.id),
                            "api_key_id": str(current_api_key_id) if current_api_key_id else None,
                        },
                    )
                    record_cache_event(hit=True)
                    logger.info(
                        "document job completed from cache",
                        extra={
                            "event": "document_job.cache_hit",
                            "reused_from_job_id": str(cached_job.id),
                        },
                    )
                    return DocumentJobResponse(
                        task_id=job.id,
                        organization_id=job.organization_id,
                        status=job.status.value,
                        template_id=job.template_id,
                        template_version_id=job.template_version_id,
                        requested_by_user_id=current_user_id,
                        from_cache=True,
                    )

        record_cache_event(hit=False)
        logger.info(
            "document job queued",
            extra={
                "event": "document_job.queued",
            },
        )
        self._job_queue_service.enqueue_generation_job(
            job.id,
            organization_id=job.organization_id,
            user_id=current_user_id,
            template_version_id=job.template_version_id,
        )
        return DocumentJobResponse(
            task_id=job.id,
            organization_id=job.organization_id,
            status=job.status.value,
            template_id=job.template_id,
            template_version_id=job.template_version_id,
            requested_by_user_id=current_user_id,
            from_cache=False,
        )

    async def get_job_status(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentJobStatusResponse:
        """Return the current lifecycle state and produced artifacts."""
        async with get_transaction_session() as session:
            repository = DocumentRepository(session)
            job = await repository.get_by_id(job_id, organization_id=organization_id)
            if job is None:
                raise NotFoundError("Document job was not found.")

            artifacts = []
            for artifact in job.artifacts:
                artifacts.append(
                    DocumentArtifactResponse(
                        id=artifact.id,
                        kind=artifact.kind.value,
                        file_name=artifact.file_name,
                        content_type=artifact.content_type,
                        size_bytes=artifact.size_bytes,
                        download_url=await self._storage_service.get_download_url(
                            artifact.storage_key
                        ),
                    )
                )

            return DocumentJobStatusResponse(
                task_id=job.id,
                organization_id=job.organization_id,
                status=job.status.value,
                template_id=job.template_id,
                template_version_id=job.template_version_id,
                requested_by_user_id=job.requested_by_user_id,
                from_cache=any(artifact.is_cached for artifact in job.artifacts),
                error_message=job.error_message,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                artifacts=artifacts,
            )

    async def create_imported_job(
        self,
        payload: ImportedTemplateDocumentJobCreateRequest,
        background_tasks: BackgroundTasks,
        *,
        current_user_id: UUID | None,
        current_api_key_id: UUID | None = None,
        require_published_template: bool = False,
    ) -> DocumentJobResponse:
        """Queue a generation job that preserves the uploaded DOCX layout."""
        _ = background_tasks
        async with get_transaction_session() as session:
            resolver = TemplateResolverService(session)
            context = await resolver.resolve(
                organization_id=payload.organization_id,
                template_id=payload.template_id,
                template_version_id=payload.template_version_id,
                require_published=require_published_template,
            )
            if context.render_strategy != "docx_import":
                raise ValidationError(
                    "This template version is not configured for imported-DOCX generation."
                )

            empty_constructor = self._build_metering_constructor()
            await self._billing_service.enforce_generation_allowed(
                organization_id=payload.organization_id,
                constructor=empty_constructor,
                session=session,
            )
            normalized_payload, cache_key = self._import_renderer.prepare_payload(
                context=context,
                data=payload.data,
            )

            repository = DocumentRepository(session)
            audit_service = AuditService(session)
            job = await repository.create(
                DocumentJob(
                    organization_id=context.organization_id,
                    template_id=context.template_id,
                    template_version_id=context.template_version_id,
                    requested_by_user_id=current_user_id,
                    status=DocumentJobStatus.QUEUED,
                    input_payload={
                        "generation_mode": "docx_import",
                        "organization_id": str(payload.organization_id),
                        "template_id": str(payload.template_id),
                        "template_version_id": (
                            str(payload.template_version_id)
                            if payload.template_version_id is not None
                            else None
                        ),
                        "data": payload.data,
                    },
                    normalized_payload=normalized_payload,
                    cache_key=cache_key,
                )
            )
            await self._billing_service.record_generation_request(
                organization_id=job.organization_id,
                constructor=empty_constructor,
                session=session,
            )
            bind_context(
                job_id=job.id,
                organization_id=job.organization_id,
                user_id=current_user_id,
                api_key_id=current_api_key_id,
                template_version_id=job.template_version_id,
            )
            await audit_service.log_event(
                organization_id=job.organization_id,
                user_id=current_user_id,
                action=AuditAction.DOCUMENT_JOB_CREATED,
                entity_type="document_job",
                entity_id=job.id,
                payload={
                    "template_id": str(job.template_id),
                    "template_version_id": str(job.template_version_id),
                    "cache_key": cache_key,
                    "from_cache": False,
                    "generation_mode": "docx_import",
                    "api_key_id": str(current_api_key_id) if current_api_key_id else None,
                },
            )

            cached_job = await repository.find_completed_cache_hit(
                organization_id=context.organization_id,
                template_version_id=context.template_version_id,
                cache_key=cache_key,
            )
            if cached_job is not None and cached_job.id != job.id:
                artifact_repository = DocumentArtifactRepository(session)
                cached_artifacts = await artifact_repository.list_reusable_by_job_id(cached_job.id)
                if cached_artifacts:
                    cached_storage_bytes = sum(int(artifact.size_bytes or 0) for artifact in cached_artifacts)
                    await self._billing_service.enforce_storage_delta_allowed(
                        organization_id=job.organization_id,
                        additional_bytes=cached_storage_bytes,
                        session=session,
                    )
                    artifact_service = ArtifactService(session, self._storage_service)
                    await artifact_service.reuse_cached_artifacts(
                        organization_code=context.organization_code,
                        job_id=job.id,
                        user_id=current_user_id,
                        artifacts=cached_artifacts,
                    )
                    await repository.mark_processing(
                        job,
                        normalized_payload=normalized_payload,
                        cache_key=cache_key,
                    )
                    await repository.mark_completed(job)
                    await audit_service.log_event(
                        organization_id=job.organization_id,
                        user_id=current_user_id,
                        action=AuditAction.DOCUMENT_JOB_COMPLETED,
                        entity_type="document_job",
                        entity_id=job.id,
                        payload={
                            "template_id": str(job.template_id),
                            "template_version_id": str(job.template_version_id),
                            "from_cache": True,
                            "reused_from_job_id": str(cached_job.id),
                            "generation_mode": "docx_import",
                            "api_key_id": str(current_api_key_id) if current_api_key_id else None,
                        },
                    )
                    record_cache_event(hit=True)
                    logger.info(
                        "document job completed from imported-template cache",
                        extra={
                            "event": "document_job.cache_hit",
                            "reused_from_job_id": str(cached_job.id),
                        },
                    )
                    return DocumentJobResponse(
                        task_id=job.id,
                        organization_id=job.organization_id,
                        status=job.status.value,
                        template_id=job.template_id,
                        template_version_id=job.template_version_id,
                        requested_by_user_id=current_user_id,
                        from_cache=True,
                    )

        record_cache_event(hit=False)
        logger.info(
            "imported document job queued",
            extra={"event": "document_job.queued"},
        )
        self._job_queue_service.enqueue_generation_job(
            job.id,
            organization_id=job.organization_id,
            user_id=current_user_id,
            template_version_id=job.template_version_id,
        )
        return DocumentJobResponse(
            task_id=job.id,
            organization_id=job.organization_id,
            status=job.status.value,
            template_id=job.template_id,
            template_version_id=job.template_version_id,
            requested_by_user_id=current_user_id,
            from_cache=False,
        )

    def _build_metering_constructor(self) -> DocumentConstructor:
        """Return a minimal constructor object for plan metering paths."""
        # Imported-DOCX generation bypasses constructor rendering, but billing hooks
        # still expect a DocumentConstructor-shaped object to count premium blocks.
        return DocumentConstructor.model_construct(
            locale="ru-RU",
            formatting=GOSTFormattingRules(),
            metadata={},
            blocks=[],
        )

    async def get_constructor_schema(self) -> ConstructorSchemaResponse:
        """Return the supported constructor contract."""
        return ConstructorSchemaResponse()

    async def get_download_artifact(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentArtifactAccessResponse:
        """Return the preferred downloadable artifact for a job."""
        return await self._get_artifact_access(
            organization_id=organization_id,
            job_id=job_id,
            preferred_kinds=[ArtifactKind.PDF, ArtifactKind.DOCX],
        )

    async def get_preview_artifact(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
    ) -> DocumentArtifactAccessResponse:
        """Return the preferred preview artifact for a job."""
        return await self._get_artifact_access(
            organization_id=organization_id,
            job_id=job_id,
            preferred_kinds=[ArtifactKind.PDF, ArtifactKind.DOCX],
        )

    async def verify_artifact(
        self,
        *,
        organization_id: UUID,
        authenticity_hash: str | None = None,
        file_bytes: bytes | None = None,
    ) -> DocumentVerificationResponse:
        """Return whether a file or hash matches a generated artifact."""
        return await self._verification_service.verify(
            organization_id=organization_id,
            authenticity_hash=authenticity_hash,
            file_bytes=file_bytes,
        )

    async def _get_artifact_access(
        self,
        *,
        organization_id: UUID,
        job_id: UUID,
        preferred_kinds: list[ArtifactKind],
    ) -> DocumentArtifactAccessResponse:
        """Resolve one artifact access response for a job."""
        async with get_transaction_session() as session:
            job_repository = DocumentRepository(session)
            artifact_repository = DocumentArtifactRepository(session)

            job = await job_repository.get_by_id(job_id, organization_id=organization_id)
            if job is None:
                raise NotFoundError("Document job was not found.")

            artifact = await artifact_repository.get_preferred_for_job(
                job_id=job.id,
                preferred_kinds=preferred_kinds,
            )
            if artifact is None:
                raise NotFoundError("Document artifact was not found.")

            return DocumentArtifactAccessResponse(
                organization_id=job.organization_id,
                task_id=job.id,
                artifact=DocumentArtifactResponse(
                    id=artifact.id,
                    kind=artifact.kind.value,
                    file_name=artifact.file_name,
                    content_type=artifact.content_type,
                    size_bytes=artifact.size_bytes,
                    download_url=await self._storage_service.get_download_url(artifact.storage_key),
                ),
            )
