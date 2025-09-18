"""Service-level models for the document generation pipeline."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.dtos.constructor import (
    DocumentConstructor,
    GOSTFormattingRules,
)


@dataclass(slots=True)
class ResolvedTemplateContext:
    """Resolved template and version context for generation jobs."""

    template_id: UUID
    template_version_id: UUID
    organization_id: UUID
    organization_code: str
    template_code: str
    template_name: str
    template_version: str
    original_filename: str
    variable_schema: dict[str, Any]


@dataclass(slots=True)
class ResolvedBlock:
    """Block content after variable binding has been applied."""

    id: str
    type: str
    content: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResolvedDocument:
    """Normalized document ready for rendering."""

    constructor: DocumentConstructor
    formatting: GOSTFormattingRules
    blocks: list[ResolvedBlock]
    data: dict[str, Any]
