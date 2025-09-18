"""DTOs for template discovery and ingestion flows."""

import re
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.dtos.common import BaseDTO

SAFE_TEMPLATE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")
SAFE_TEMPLATE_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class TemplateVariableSchemaItem(BaseDTO):
    """Normalized variable extracted from a DOCX template."""

    key: str
    label: str
    placeholder: str
    value_type: str
    component_type: str
    required: bool = True
    sample_value: str | None = None
    occurrences: int = 1
    sources: list[str] = Field(default_factory=list)


class TemplateComponentSchemaItem(BaseDTO):
    """Frontend-facing component description derived from a variable."""

    id: str
    component: str
    binding: str
    label: str
    value_type: str
    required: bool = True


class TemplateSchemaResponse(BaseDTO):
    """Normalized schema returned to the frontend."""

    variable_count: int
    variables: list[TemplateVariableSchemaItem]
    components: list[TemplateComponentSchemaItem]


class TemplateVersionSummary(BaseDTO):
    """Public summary for a template version."""

    id: UUID = Field(default_factory=uuid4)
    version: str
    is_current: bool = True
    is_published: bool = False


class TemplateVersionResponse(TemplateVersionSummary):
    """Detailed template version payload."""

    original_filename: str
    storage_key: str
    checksum: str | None = None
    notes: str | None = None
    schema_payload: TemplateSchemaResponse = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )


class TemplateResponse(BaseDTO):
    """Public template representation."""

    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID = Field(default_factory=uuid4)
    name: str
    code: str
    status: str
    description: str | None = None
    current_version: TemplateVersionSummary | None = None


class TemplateDetailResponse(TemplateResponse):
    """Detailed template response for frontend screens."""

    versions: list[TemplateVersionSummary] = Field(default_factory=list)
    current_version_details: TemplateVersionResponse | None = None


class TemplateListResponse(BaseDTO):
    """Collection of public templates."""

    items: list[TemplateResponse]


class TemplateListQuery(BaseDTO):
    """Tenant-scoped query for listing templates."""

    organization_id: UUID


class TemplateAccessQuery(BaseDTO):
    """Tenant-scoped query for one template resource."""

    organization_id: UUID


class TemplateUploadRequest(BaseDTO):
    """Validated metadata for multipart template upload."""

    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9 _-]+$")
    version: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    description: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    created_by_user_id: UUID | None = None
    publish: bool = True

    @field_validator("name", "code", "version")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Trim required text inputs before downstream processing."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty.")
        return normalized

    @field_validator("description", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        """Trim optional long-form text fields."""
        return value.strip() if value is not None else None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        """Ensure template codes stay slug-friendly before normalization."""
        if not SAFE_TEMPLATE_CODE_PATTERN.fullmatch(value):
            raise ValueError("Template code contains unsupported characters.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        """Ensure template versions stay predictable and file-safe."""
        if not SAFE_TEMPLATE_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Template version contains unsupported characters.")
        return value


class TemplateRegisterRequest(BaseDTO):
    """Payload for registering a template from existing storage."""

    organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9 _-]+$")
    version: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    storage_key: str = Field(min_length=1, max_length=500)
    original_filename: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    created_by_user_id: UUID | None = None
    publish: bool = True

    @field_validator("name", "code", "version", "original_filename")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Trim required text inputs before downstream processing."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty.")
        return normalized

    @field_validator("description", "notes")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        """Trim optional long-form text fields."""
        return value.strip() if value is not None else None

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        """Ensure template codes stay slug-friendly before normalization."""
        if not SAFE_TEMPLATE_CODE_PATTERN.fullmatch(value):
            raise ValueError("Template code contains unsupported characters.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        """Ensure template versions stay predictable and file-safe."""
        if not SAFE_TEMPLATE_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Template version contains unsupported characters.")
        return value

    @field_validator("storage_key")
    @classmethod
    def normalize_storage_key(cls, value: str) -> str:
        """Normalize user-provided storage keys early."""
        return value.strip()


class TemplateIngestionResponse(BaseDTO):
    """Response returned after a template version is ingested."""

    template: TemplateResponse
    version: TemplateVersionResponse


class TemplateSchemaExtractionResponse(BaseDTO):
    """Response returned after extracting schema from a stored template."""

    organization_id: UUID
    template_id: UUID
    template_version_id: UUID
    schema_payload: TemplateSchemaResponse = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
