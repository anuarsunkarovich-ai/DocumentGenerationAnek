"""Application services for template workflows."""

from hashlib import sha256
from uuid import UUID

from fastapi import UploadFile

from app.core.database import get_transaction_session
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.dtos.template import (
    TemplateDetailResponse,
    TemplateIngestionResponse,
    TemplateListResponse,
    TemplateRegisterRequest,
    TemplateResponse,
    TemplateSchemaExtractionResponse,
    TemplateSchemaResponse,
    TemplateVersionResponse,
    TemplateVersionSummary,
)
from app.models.enums import TemplateStatus
from app.models.template import Template
from app.models.template_version import TemplateVersion
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.template_version_repository import TemplateVersionRepository
from app.services.billing_service import BillingService
from app.services.security_service import SecurityService
from app.services.storage import StorageService, get_storage_service
from app.services.template_schema_service import TemplateSchemaService


class TemplateService:
    """Handle template discovery and ingestion workflows."""

    def __init__(
        self,
        storage_service: StorageService | None = None,
        schema_service: TemplateSchemaService | None = None,
        security_service: SecurityService | None = None,
    ) -> None:
        """Configure service dependencies."""
        self._storage_service = storage_service or get_storage_service()
        self._schema_service = schema_service or TemplateSchemaService()
        self._security_service = security_service or SecurityService()
        self._billing_service = BillingService()

    async def list_templates(
        self,
        organization_id: UUID,
        *,
        published_only: bool = False,
    ) -> TemplateListResponse:
        """Return templates visible to the selected tenant."""
        async with get_transaction_session() as session:
            template_repository = TemplateRepository(session)
            templates = await template_repository.list_all(
                organization_id=organization_id,
                published_only=published_only,
            )
            return TemplateListResponse(
                items=[self._serialize_template(template) for template in templates]
            )

    async def get_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
        published_only: bool = False,
    ) -> TemplateDetailResponse:
        """Return one template with version details."""
        async with get_transaction_session() as session:
            template_repository = TemplateRepository(session)
            template = await template_repository.get_by_id(
                template_id=template_id,
                organization_id=organization_id,
                published_only=published_only,
            )
            if template is None:
                raise NotFoundError("Template was not found.")
            if published_only:
                template.versions = [version for version in template.versions if version.is_published]
            return self._serialize_template_detail(template)

    async def extract_schema_for_template(
        self,
        *,
        organization_id: UUID,
        template_id: UUID,
    ) -> TemplateSchemaExtractionResponse:
        """Re-extract and persist schema for the current template version."""
        async with get_transaction_session() as session:
            template_repository = TemplateRepository(session)
            version_repository = TemplateVersionRepository(session)

            template = await template_repository.get_by_id(
                template_id=template_id,
                organization_id=organization_id,
            )
            if template is None:
                raise NotFoundError("Template was not found.")

            current_version = next(
                (version for version in template.versions if version.is_current), None
            )
            if current_version is None:
                raise NotFoundError("Current template version was not found.")

            content = await self._storage_service.download_bytes(current_version.storage_key)
            schema = self._schema_service.extract_schema(current_version.original_filename, content)
            await version_repository.update_schema(
                current_version,
                variable_schema=schema.model_dump(mode="json"),
                component_schema=[
                    component.model_dump(mode="json") for component in schema.components
                ],
            )

            return TemplateSchemaExtractionResponse(
                organization_id=template.organization_id,
                template_id=template.id,
                template_version_id=current_version.id,
                schema_payload=schema,
            )

    async def upload_template(
        self,
        *,
        organization_id: UUID,
        name: str,
        code: str,
        version: str,
        file: UploadFile,
        description: str | None = None,
        notes: str | None = None,
        current_user_id: UUID,
        publish: bool = True,
    ) -> TemplateIngestionResponse:
        """Upload, parse, store, and register a DOCX template."""
        content = await file.read()
        safe_file_name = self._security_service.validate_template_upload(
            file_name=file.filename or "template.docx",
            content_type=file.content_type,
            content=content,
        )

        schema = self._schema_service.extract_schema(safe_file_name, content)
        checksum = sha256(content).hexdigest()
        storage_object_key: str | None = None

        try:
            async with get_transaction_session() as session:
                organization_repository = OrganizationRepository(session)
                template_repository = TemplateRepository(session)
                version_repository = TemplateVersionRepository(session)

                organization = await organization_repository.get_by_id(organization_id)
                if organization is None:
                    raise NotFoundError("Organization was not found.")
                await self._billing_service.enforce_storage_delta_allowed(
                    organization_id=organization_id,
                    additional_bytes=len(content),
                    session=session,
                )

                template = await self._get_or_create_template(
                    template_repository=template_repository,
                    session=session,
                    organization_id=organization_id,
                    name=name,
                    code=code,
                    description=description,
                )

                existing_version = await version_repository.get_by_template_and_version(
                    template_id=template.id,
                    version=version,
                )
                if existing_version is not None:
                    raise ConflictError("Template version already exists.")

                storage_object = await self._storage_service.upload_template(
                    organization_code=organization.code,
                    template_code=template.code,
                    version=version,
                    file_name=safe_file_name,
                    content=content,
                    content_type=file.content_type
                    or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                storage_object_key = storage_object.key

                await version_repository.unset_current_versions(template.id)
                template_version = await version_repository.create(
                    TemplateVersion(
                        template_id=template.id,
                        created_by_user_id=current_user_id,
                        version=version,
                        original_filename=safe_file_name,
                        storage_key=storage_object.key,
                        size_bytes=len(content),
                        checksum=checksum,
                        variable_schema=schema.model_dump(mode="json"),
                        component_schema=[
                            component.model_dump(mode="json") for component in schema.components
                        ],
                        notes=notes,
                        is_published=publish,
                        is_current=True,
                    )
                )
                await self._billing_service.record_storage_usage(
                    organization_id=organization_id,
                    delta_bytes=len(content),
                    session=session,
                )
                await self._billing_service.sync_template_count(
                    organization_id=organization_id,
                    session=session,
                )
        except Exception:
            if storage_object_key is not None:
                await self._storage_service.delete_object(storage_object_key)
            raise

        return self._build_ingestion_response(
            template=template,
            version=template_version,
            schema=schema,
        )

    async def register_template(
        self,
        payload: TemplateRegisterRequest,
        *,
        current_user_id: UUID,
    ) -> TemplateIngestionResponse:
        """Register a template version from an already stored DOCX file."""
        async with get_transaction_session() as session:
            organization_repository = OrganizationRepository(session)
            template_repository = TemplateRepository(session)
            version_repository = TemplateVersionRepository(session)

            organization = await organization_repository.get_by_id(payload.organization_id)
            if organization is None:
                raise NotFoundError("Organization was not found.")

            safe_storage_key = self._security_service.validate_template_storage_key(
                storage_key=payload.storage_key,
                organization_code=organization.code,
            )
            content = await self._storage_service.download_bytes(safe_storage_key)
            await self._billing_service.enforce_storage_delta_allowed(
                organization_id=payload.organization_id,
                additional_bytes=len(content),
                session=session,
            )
            safe_file_name = self._security_service.validate_template_upload(
                file_name=payload.original_filename,
                content_type=None,
                content=content,
            )
            schema = self._schema_service.extract_schema(safe_file_name, content)
            checksum = sha256(content).hexdigest()

            template = await self._get_or_create_template(
                template_repository=template_repository,
                session=session,
                organization_id=payload.organization_id,
                name=payload.name,
                code=payload.code,
                description=payload.description,
            )

            existing_version = await version_repository.get_by_template_and_version(
                template_id=template.id,
                version=payload.version,
            )
            if existing_version is not None:
                raise ConflictError("Template version already exists.")

            await version_repository.unset_current_versions(template.id)
            template_version = await version_repository.create(
                TemplateVersion(
                    template_id=template.id,
                    created_by_user_id=current_user_id,
                    version=payload.version,
                    original_filename=safe_file_name,
                    storage_key=safe_storage_key,
                    size_bytes=len(content),
                    checksum=checksum,
                    variable_schema=schema.model_dump(mode="json"),
                    component_schema=[
                        component.model_dump(mode="json") for component in schema.components
                    ],
                    notes=payload.notes,
                    is_published=payload.publish,
                    is_current=True,
                )
            )
            await self._billing_service.record_storage_usage(
                organization_id=payload.organization_id,
                delta_bytes=len(content),
                session=session,
            )
            await self._billing_service.sync_template_count(
                organization_id=payload.organization_id,
                session=session,
            )

        return self._build_ingestion_response(
            template=template,
            version=template_version,
            schema=schema,
        )

    async def extract_schema_from_upload(
        self,
        file: UploadFile,
    ) -> TemplateSchemaResponse:
        """Extract a normalized schema without persisting the template."""
        content = await file.read()
        safe_file_name = self._security_service.validate_template_upload(
            file_name=file.filename or "template.docx",
            content_type=file.content_type,
            content=content,
        )
        return self._schema_service.extract_schema(safe_file_name, content)

    async def _get_or_create_template(
        self,
        *,
        template_repository: TemplateRepository,
        session,
        organization_id: UUID,
        name: str,
        code: str,
        description: str | None,
    ) -> Template:
        """Return an existing template or create a new one."""
        normalized_code = self._normalize_code(code)
        template = await template_repository.get_by_code(
            organization_id=organization_id,
            code=normalized_code,
        )
        if template is not None:
            template.name = name.strip()
            template.description = description
            template.status = TemplateStatus.ACTIVE
            return template

        await self._billing_service.enforce_template_creation_allowed(
            organization_id=organization_id,
            session=session,
        )

        return await template_repository.create(
            Template(
                organization_id=organization_id,
                name=name.strip(),
                code=normalized_code,
                description=description,
                status=TemplateStatus.ACTIVE,
            )
        )

    def _build_ingestion_response(
        self,
        *,
        template: Template,
        version: TemplateVersion,
        schema: TemplateSchemaResponse,
    ) -> TemplateIngestionResponse:
        """Build the API response after a template is ingested."""
        return TemplateIngestionResponse(
            template=TemplateResponse(
                id=template.id,
                organization_id=template.organization_id,
                name=template.name,
                code=template.code,
                status=template.status.value,
                description=template.description,
                current_version=TemplateVersionSummary(
                    id=version.id,
                    version=version.version,
                    is_current=version.is_current,
                    is_published=version.is_published,
                ),
            ),
            version=TemplateVersionResponse(
                id=version.id,
                version=version.version,
                is_current=version.is_current,
                is_published=version.is_published,
                original_filename=version.original_filename,
                storage_key=version.storage_key,
                checksum=version.checksum,
                notes=version.notes,
                schema_payload=schema,
            ),
        )

    def _serialize_template(self, template: Template) -> TemplateResponse:
        """Serialize a template ORM object into the public DTO."""
        current_version = next(
            (version for version in template.versions if version.is_current),
            None,
        )
        return TemplateResponse(
            id=template.id,
            organization_id=template.organization_id,
            name=template.name,
            code=template.code,
            status=template.status.value,
            description=template.description,
            current_version=(
                TemplateVersionSummary(
                    id=current_version.id,
                    version=current_version.version,
                    is_current=current_version.is_current,
                    is_published=current_version.is_published,
                )
                if current_version is not None
                else None
            ),
        )

    def _serialize_template_detail(self, template: Template) -> TemplateDetailResponse:
        """Serialize a detailed template payload."""
        current_version = next(
            (version for version in template.versions if version.is_current),
            None,
        )
        return TemplateDetailResponse(
            id=template.id,
            organization_id=template.organization_id,
            name=template.name,
            code=template.code,
            status=template.status.value,
            description=template.description,
            current_version=(
                TemplateVersionSummary(
                    id=current_version.id,
                    version=current_version.version,
                    is_current=current_version.is_current,
                    is_published=current_version.is_published,
                )
                if current_version is not None
                else None
            ),
            versions=[
                TemplateVersionSummary(
                    id=version.id,
                    version=version.version,
                    is_current=version.is_current,
                    is_published=version.is_published,
                )
                for version in sorted(
                    template.versions, key=lambda item: item.created_at, reverse=True
                )
            ],
            current_version_details=(
                TemplateVersionResponse(
                    id=current_version.id,
                    version=current_version.version,
                    is_current=current_version.is_current,
                    is_published=current_version.is_published,
                    original_filename=current_version.original_filename,
                    storage_key=current_version.storage_key,
                    checksum=current_version.checksum,
                    notes=current_version.notes,
                    schema_payload=TemplateSchemaResponse.model_validate(
                        current_version.variable_schema
                    ),
                )
                if current_version is not None
                else None
            ),
        )

    def _normalize_code(self, code: str) -> str:
        """Normalize a template code into a stable slug."""
        normalized = code.strip().lower().replace(" ", "-").replace("_", "-")
        while "--" in normalized:
            normalized = normalized.replace("--", "-")
        normalized = normalized.strip("-")
        if not normalized:
            raise ValidationError("Template code cannot be empty.")
        return normalized
