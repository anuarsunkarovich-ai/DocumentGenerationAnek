"""Shared domain enums for persistence models."""

from enum import StrEnum


class TemplateStatus(StrEnum):
    """Lifecycle states for a template."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserRole(StrEnum):
    """Application roles for organization members."""

    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


class DocumentJobStatus(StrEnum):
    """Lifecycle states for document generation jobs."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactKind(StrEnum):
    """Types of files produced by the generator."""

    DOCX = "docx"
    PDF = "pdf"
    PREVIEW = "preview"
    SOURCE = "source"


class AuditAction(StrEnum):
    """Tracked audit events for domain entities."""

    TEMPLATE_CREATED = "template_created"
    TEMPLATE_VERSION_CREATED = "template_version_created"
    DOCUMENT_JOB_CREATED = "document_job_created"
    DOCUMENT_JOB_COMPLETED = "document_job_completed"
    DOCUMENT_JOB_FAILED = "document_job_failed"
    ARTIFACT_CREATED = "artifact_created"
    API_KEY_CREATED = "api_key_created"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_REVOKED = "api_key_revoked"
