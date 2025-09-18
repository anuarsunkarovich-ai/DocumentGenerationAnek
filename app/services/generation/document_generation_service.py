"""Orchestrate background document generation jobs."""

from uuid import UUID

from app.core.database import get_transaction_session
from app.models.enums import AuditAction
from app.repositories.document_repository import DocumentRepository
from app.services.audit_service import AuditService
from app.services.generation.artifact_service import ArtifactService
from app.services.generation.document_composer_service import DocumentComposerService
from app.services.generation.pdf_render_service import PdfRenderService
from app.services.generation.template_resolver_service import TemplateResolverService
from app.services.generation.variable_mapper_service import VariableMapperService
from app.services.storage import get_storage_service


class DocumentGenerationService:
    """Run the full document generation pipeline for one job."""

    def __init__(self) -> None:
        """Create the stateless pipeline dependencies."""
        self._storage_service = get_storage_service()
        self._variable_mapper = VariableMapperService()
        self._composer = DocumentComposerService()
        self._pdf_renderer = PdfRenderService()

    async def process_job(self, job_id: UUID) -> None:
        """Process a queued job end to end in the background."""
        try:
            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                audit_service = AuditService(session)
                job = await repository.get_by_id(job_id)
                if job is None:
                    return

                resolver = TemplateResolverService(session)
                context = await resolver.resolve(
                    organization_id=job.organization_id,
                    template_id=job.template_id,
                    template_version_id=job.template_version_id,
                )
                constructor_payload = job.input_payload["constructor"]
                data_payload = job.input_payload.get("data", {})

                from app.dtos.constructor import DocumentConstructor

                constructor = DocumentConstructor.model_validate(constructor_payload)
                resolved_document, normalized_payload, cache_key = (
                    self._variable_mapper.map_document(
                        context=context,
                        constructor=constructor,
                        data=data_payload,
                    )
                )
                await repository.mark_processing(
                    job,
                    normalized_payload=normalized_payload,
                    cache_key=cache_key,
                )

            docx_bytes = self._composer.compose(resolved_document)
            pdf_bytes = self._pdf_renderer.render(resolved_document)

            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                job = await repository.get_by_id(job_id)
                if job is None:
                    return

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
        except Exception as error:
            async with get_transaction_session() as session:
                repository = DocumentRepository(session)
                audit_service = AuditService(session)
                job = await repository.get_by_id(job_id)
                if job is not None:
                    await repository.mark_failed(job, str(error))
                    await audit_service.log_event(
                        organization_id=job.organization_id,
                        user_id=job.requested_by_user_id,
                        action=AuditAction.DOCUMENT_JOB_FAILED,
                        entity_type="document_job",
                        entity_id=job.id,
                        payload={
                            "template_id": str(job.template_id),
                            "template_version_id": str(job.template_version_id),
                            "error_message": str(error),
                            "from_cache": False,
                        },
                    )
