"""Persist generated artifacts and expose download URLs."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.document_artifact import DocumentArtifact
from app.models.enums import ArtifactKind, AuditAction
from app.repositories.document_artifact_repository import DocumentArtifactRepository
from app.services.audit_service import AuditService
from app.services.billing_service import BillingService
from app.services.generation.models import ResolvedTemplateContext
from app.services.storage import StorageService


class ArtifactService:
    """Store artifacts in object storage and persist their metadata."""

    def __init__(self, session: AsyncSession, storage_service: StorageService) -> None:
        """Store service dependencies."""
        self._session = session
        self._repository = DocumentArtifactRepository(session)
        self._audit_service = AuditService(session)
        self._storage_service = storage_service
        self._settings = get_settings()
        self._billing_service = BillingService()

    async def store_docx(
        self,
        *,
        context: ResolvedTemplateContext,
        job_id: UUID,
        user_id: UUID | None,
        content: bytes,
    ) -> DocumentArtifact:
        """Store the generated DOCX artifact."""
        file_name = f"{context.template_code}-{context.template_version}.docx"
        stored = await self._storage_service.upload_generated_artifact(
            organization_code=context.organization_code,
            job_id=str(job_id),
            artifact_name=file_name,
            content=content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        artifact = await self._repository.create(
            DocumentArtifact(
                organization_id=context.organization_id,
                document_job_id=job_id,
                template_version_id=context.template_version_id,
                kind=ArtifactKind.DOCX,
                file_name=file_name,
                content_type=stored.content_type,
                storage_key=stored.key,
                checksum=sha256(content).hexdigest(),
                size_bytes=stored.size_bytes,
                is_cached=False,
                expires_at=self.cache_expiration(),
            )
        )
        await self._log_artifact_created(
            artifact=artifact,
            user_id=user_id,
            from_cache=False,
        )
        await self._billing_service.record_storage_usage(
            organization_id=context.organization_id,
            delta_bytes=int(stored.size_bytes or len(content)),
            session=self._session,
        )
        return artifact

    async def store_pdf(
        self,
        *,
        context: ResolvedTemplateContext,
        job_id: UUID,
        user_id: UUID | None,
        content: bytes,
    ) -> DocumentArtifact:
        """Store the generated PDF artifact."""
        file_name = f"{context.template_code}-{context.template_version}.pdf"
        stored = await self._storage_service.upload_generated_artifact(
            organization_code=context.organization_code,
            job_id=str(job_id),
            artifact_name=file_name,
            content=content,
            content_type="application/pdf",
        )
        artifact = await self._repository.create(
            DocumentArtifact(
                organization_id=context.organization_id,
                document_job_id=job_id,
                template_version_id=context.template_version_id,
                kind=ArtifactKind.PDF,
                file_name=file_name,
                content_type=stored.content_type,
                storage_key=stored.key,
                checksum=sha256(content).hexdigest(),
                size_bytes=stored.size_bytes,
                is_cached=False,
                expires_at=self.cache_expiration(),
            )
        )
        await self._log_artifact_created(
            artifact=artifact,
            user_id=user_id,
            from_cache=False,
        )
        await self._billing_service.record_storage_usage(
            organization_id=context.organization_id,
            delta_bytes=int(stored.size_bytes or len(content)),
            session=self._session,
        )
        return artifact

    async def reuse_cached_artifacts(
        self,
        *,
        organization_code: str,
        job_id: UUID,
        user_id: UUID | None,
        artifacts: list[DocumentArtifact],
    ) -> list[DocumentArtifact]:
        """Copy existing artifacts into a new job without regenerating content."""
        cloned_artifacts: list[DocumentArtifact] = []
        for artifact in artifacts:
            content = await self._storage_service.download_bytes(artifact.storage_key)
            stored = await self._storage_service.upload_generated_artifact(
                organization_code=organization_code,
                job_id=str(job_id),
                artifact_name=artifact.file_name,
                content=content,
                content_type=artifact.content_type,
            )
            cloned_artifacts.append(
                await self._repository.create(
                    DocumentArtifact(
                        organization_id=artifact.organization_id,
                        document_job_id=job_id,
                        template_version_id=artifact.template_version_id,
                        kind=artifact.kind,
                        file_name=artifact.file_name,
                        content_type=artifact.content_type,
                        storage_key=stored.key,
                        checksum=artifact.checksum or sha256(content).hexdigest(),
                        size_bytes=stored.size_bytes,
                        is_cached=True,
                        expires_at=artifact.expires_at or self.cache_expiration(),
                    )
                )
            )
            await self._log_artifact_created(
                artifact=cloned_artifacts[-1],
                user_id=user_id,
                from_cache=True,
            )
            await self._billing_service.record_storage_usage(
                organization_id=artifact.organization_id,
                delta_bytes=int(stored.size_bytes or len(content)),
                session=self._session,
            )
        return cloned_artifacts

    async def build_download_url(self, storage_key: str) -> str:
        """Return a temporary download URL for an artifact."""
        return await self._storage_service.get_download_url(storage_key)

    def cache_expiration(self) -> datetime:
        """Return the cache expiration timestamp for generated artifacts."""
        return datetime.now(timezone.utc) + timedelta(
            hours=self._settings.generation.cache_ttl_hours
        )

    async def _log_artifact_created(
        self,
        *,
        artifact: DocumentArtifact,
        user_id: UUID | None,
        from_cache: bool,
    ) -> None:
        """Write an audit entry for one created artifact."""
        await self._audit_service.log_event(
            organization_id=artifact.organization_id,
            user_id=user_id,
            action=AuditAction.ARTIFACT_CREATED,
            entity_type="document_artifact",
            entity_id=artifact.id,
            payload={
                "document_job_id": str(artifact.document_job_id)
                if artifact.document_job_id
                else None,
                "template_version_id": str(artifact.template_version_id),
                "kind": artifact.kind.value,
                "file_name": artifact.file_name,
                "authenticity_hash": artifact.checksum,
                "authenticity_algorithm": "sha256",
                "from_cache": from_cache,
            },
        )
