"""DTOs for document generation."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.core.config import get_settings
from app.dtos.common import BaseDTO
from app.dtos.constructor import ConstructorSchemaDescriptor, DocumentConstructor

SAFE_BINDING_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,119}$")


class DocumentJobCreateRequest(BaseDTO):
    """Payload for creating a document generation job."""

    organization_id: UUID
    template_id: UUID
    template_version_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    constructor: DocumentConstructor

    @field_validator("data")
    @classmethod
    def validate_data_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Validate incoming bound data size and key shape."""
        settings = get_settings()
        if len(value) > settings.generation.max_template_variables:
            raise ValueError("Document data exceeds the configured variable limit.")
        for key in value:
            if not isinstance(key, str):
                raise ValueError("Document data contains a non-string binding key.")
            normalized_key = key.strip()
            if normalized_key != key:
                raise ValueError("Document data keys must not include surrounding whitespace.")
            if not SAFE_BINDING_KEY_PATTERN.fullmatch(key):
                raise ValueError("Document data contains an invalid binding key.")
        return value


class PublicDocumentJobCreateRequest(BaseDTO):
    """Public machine-auth payload for creating one generation job."""

    template_id: UUID
    template_version_id: UUID | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    constructor: DocumentConstructor

    @field_validator("data")
    @classmethod
    def validate_data_payload(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Validate incoming bound data size and key shape."""
        return DocumentJobCreateRequest.validate_data_payload(value)


class DocumentArtifactResponse(BaseDTO):
    """Artifact metadata returned to the frontend."""

    id: UUID
    kind: str
    file_name: str
    content_type: str
    size_bytes: int | None = None
    download_url: str | None = None


class DocumentArtifactAccessResponse(BaseDTO):
    """Response for download and preview access endpoints."""

    organization_id: UUID
    task_id: UUID
    artifact: DocumentArtifactResponse


class DocumentVerificationArtifactResponse(BaseDTO):
    """Artifact metadata returned by authenticity verification endpoints."""

    artifact_id: UUID
    task_id: UUID | None = None
    kind: str
    file_name: str
    content_type: str
    size_bytes: int | None = None
    issued_at: datetime
    authenticity_hash: str
    authenticity_algorithm: str = "sha256"
    verification_code: str


class DocumentVerificationResponse(BaseDTO):
    """Response for authenticity verification requests."""

    organization_id: UUID
    matched: bool
    provided_hash: str
    authenticity_algorithm: str = "sha256"
    matched_artifact_count: int = 0
    artifact: DocumentVerificationArtifactResponse | None = None


class DocumentJobAccessQuery(BaseDTO):
    """Tenant-scoped query for one document job."""

    organization_id: UUID


class DocumentJobResponse(BaseDTO):
    """Response returned after a job is queued."""

    task_id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    status: str = "queued"
    template_id: UUID | None = None
    template_version_id: UUID | None = None
    requested_by_user_id: UUID | None = None
    from_cache: bool = False


class DocumentJobStatusResponse(BaseDTO):
    """Polling response for a document generation job."""

    task_id: UUID
    organization_id: UUID
    status: str
    template_id: UUID
    template_version_id: UUID
    requested_by_user_id: UUID | None = None
    from_cache: bool = False
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifacts: list[DocumentArtifactResponse] = Field(default_factory=list)


class ConstructorSchemaResponse(BaseDTO):
    """Response that documents the supported constructor model."""

    descriptor: ConstructorSchemaDescriptor = Field(default_factory=ConstructorSchemaDescriptor)
