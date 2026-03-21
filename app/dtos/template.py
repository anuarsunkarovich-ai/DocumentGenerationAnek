"""DTOs for template discovery and ingestion flows."""

import re
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from app.dtos.common import BaseDTO

SAFE_TEMPLATE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")
SAFE_TEMPLATE_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
SAFE_BINDING_KEY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,119}$")


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
    render_strategy: str = "constructor"
    imported_binding_count: int = 0
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


class TemplateImportFieldCandidate(BaseDTO):
    """One likely fillable field detected in a regular DOCX document."""

    id: str
    label: str
    suggested_binding: str
    raw_fragment: str
    paragraph_path: str
    source_type: str
    detection_kind: str
    confidence: float
    preview_text: str
    value_type: str = "string"
    component_type: str = "text"
    required: bool = True
    fragment_start: int
    fragment_end: int


class TemplateImportAnalysisResponse(BaseDTO):
    """Structured analysis returned for a regular DOCX import attempt."""

    analysis_checksum: str
    candidate_count: int
    candidates: list[TemplateImportFieldCandidate]
    schema_payload: TemplateSchemaResponse = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )


class TemplateImportParagraphItem(BaseDTO):
    """One inspectable paragraph or table-cell paragraph in a DOCX file."""

    path: str
    source_type: str
    text: str
    char_count: int
    table_header_label: str | None = None


class TemplateImportInspectionResponse(BaseDTO):
    """Structured paragraph inventory for assisted templateization."""

    inspection_checksum: str
    paragraph_count: int
    paragraphs: list[TemplateImportParagraphItem]


class TemplateImportAnalyzeStoredRequest(BaseDTO):
    """Tenant-scoped request to analyze an already stored template."""

    organization_id: UUID


class TemplateImportBindingConfirmationItem(BaseDTO):
    """One user-confirmed binding for an imported DOCX field."""

    candidate_id: str = Field(min_length=1, max_length=120)
    binding_key: str = Field(min_length=1, max_length=120)
    label: str | None = Field(default=None, max_length=255)
    component_type: str | None = Field(default=None, max_length=50)
    value_type: str | None = Field(default=None, max_length=50)
    required: bool = True
    sample_value: str | None = Field(default=None, max_length=2000)

    @field_validator("candidate_id", "binding_key")
    @classmethod
    def strip_required_binding_text(cls, value: str) -> str:
        """Trim binding confirmation fields before validation."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty.")
        return normalized

    @field_validator("label", "component_type", "value_type", "sample_value")
    @classmethod
    def strip_optional_binding_text(cls, value: str | None) -> str | None:
        """Trim optional binding metadata fields."""
        return value.strip() if value is not None else None

    @field_validator("binding_key")
    @classmethod
    def validate_binding_key(cls, value: str) -> str:
        """Keep imported DOCX binding keys predictable for generation."""
        if not SAFE_BINDING_KEY_PATTERN.fullmatch(value):
            raise ValueError("Binding key contains unsupported characters.")
        return value


class TemplateImportConfirmRequest(BaseDTO):
    """Persist user-confirmed bindings for a stored imported DOCX template."""

    organization_id: UUID
    analysis_checksum: str = Field(min_length=64, max_length=64)
    bindings: list[TemplateImportBindingConfirmationItem] = Field(min_length=1)

    @field_validator("analysis_checksum")
    @classmethod
    def normalize_analysis_checksum(cls, value: str) -> str:
        """Normalize the analysis checksum to a lowercase hex digest."""
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValueError("Analysis checksum must be a sha256 hex digest.")
        return normalized

    @field_validator("bindings")
    @classmethod
    def validate_binding_items(cls, value: list[TemplateImportBindingConfirmationItem]) -> list[TemplateImportBindingConfirmationItem]:
        """Ensure candidate ids and binding keys stay unique."""
        candidate_ids = [item.candidate_id for item in value]
        binding_keys = [item.binding_key for item in value]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("Confirmed bindings contain duplicate candidate ids.")
        if len(binding_keys) != len(set(binding_keys)):
            raise ValueError("Confirmed bindings contain duplicate binding keys.")
        return value


class TemplateImportBindingResponse(BaseDTO):
    """Stored binding metadata for one confirmed DOCX import field."""

    id: str
    candidate_id: str
    binding_key: str
    label: str
    raw_fragment: str
    paragraph_path: str
    source_type: str
    detection_kind: str
    confidence: float
    preview_text: str
    value_type: str = "string"
    component_type: str = "text"
    required: bool = True
    sample_value: str | None = None
    fragment_start: int
    fragment_end: int


class TemplateImportManualSelectionItem(BaseDTO):
    """One user-selected span for assisted DOCX templateization."""

    paragraph_path: str = Field(min_length=1, max_length=255)
    fragment_start: int = Field(ge=0)
    fragment_end: int = Field(gt=0)
    binding_key: str = Field(min_length=1, max_length=120)
    label: str | None = Field(default=None, max_length=255)
    component_type: str | None = Field(default=None, max_length=50)
    value_type: str | None = Field(default=None, max_length=50)
    required: bool = True
    sample_value: str | None = Field(default=None, max_length=2000)

    @field_validator("paragraph_path", "binding_key")
    @classmethod
    def strip_required_selection_text(cls, value: str) -> str:
        """Trim required manual-selection fields before validation."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field cannot be empty.")
        return normalized

    @field_validator("label", "component_type", "value_type", "sample_value")
    @classmethod
    def strip_optional_selection_text(cls, value: str | None) -> str | None:
        """Trim optional manual-selection metadata fields."""
        return value.strip() if value is not None else None

    @field_validator("binding_key")
    @classmethod
    def validate_selection_binding_key(cls, value: str) -> str:
        """Keep manual templateization binding keys predictable."""
        if not SAFE_BINDING_KEY_PATTERN.fullmatch(value):
            raise ValueError("Binding key contains unsupported characters.")
        return value

    @field_validator("fragment_end")
    @classmethod
    def validate_fragment_bounds(cls, value: int, info) -> int:
        """Require selections to cover at least one character."""
        start = info.data.get("fragment_start")
        if start is not None and value <= start:
            raise ValueError("fragment_end must be greater than fragment_start.")
        return value


class TemplateImportTemplateizeRequest(BaseDTO):
    """Persist manual span selections for assisted DOCX templateization."""

    organization_id: UUID
    inspection_checksum: str = Field(min_length=64, max_length=64)
    selections: list[TemplateImportManualSelectionItem] = Field(min_length=1)

    @field_validator("inspection_checksum")
    @classmethod
    def normalize_inspection_checksum(cls, value: str) -> str:
        """Normalize the inspection checksum to a lowercase hex digest."""
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-f0-9]{64}", normalized):
            raise ValueError("Inspection checksum must be a sha256 hex digest.")
        return normalized

    @field_validator("selections")
    @classmethod
    def validate_manual_selections(
        cls, value: list[TemplateImportManualSelectionItem]
    ) -> list[TemplateImportManualSelectionItem]:
        """Ensure manual selections do not duplicate the same source span."""
        spans = [
            (item.paragraph_path, item.fragment_start, item.fragment_end)
            for item in value
        ]
        if len(spans) != len(set(spans)):
            raise ValueError("Manual selections contain duplicate paragraph spans.")
        return value


class TemplateImportConfirmationResponse(BaseDTO):
    """Response returned after binding confirmation is persisted."""

    organization_id: UUID
    template_id: UUID
    template_version_id: UUID
    render_strategy: str
    analysis_payload: TemplateImportAnalysisResponse = Field(
        validation_alias="analysis",
        serialization_alias="analysis",
    )
    schema_payload: TemplateSchemaResponse = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    confirmed_binding_count: int
    bindings: list[TemplateImportBindingResponse]


class TemplateTemplateizationConfirmationResponse(BaseDTO):
    """Response returned after assisted templateization is persisted."""

    organization_id: UUID
    template_id: UUID
    template_version_id: UUID
    render_strategy: str
    inspection_payload: TemplateImportInspectionResponse = Field(
        validation_alias="inspection",
        serialization_alias="inspection",
    )
    schema_payload: TemplateSchemaResponse = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    confirmed_binding_count: int
    bindings: list[TemplateImportBindingResponse]
