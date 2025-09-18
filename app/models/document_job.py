"""Document job persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import DocumentJobStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Request to generate one document from a template version."""

    __tablename__ = "document_jobs"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("template_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[DocumentJobStatus] = mapped_column(
        Enum(DocumentJobStatus, name="document_job_status"),
        default=DocumentJobStatus.QUEUED,
        nullable=False,
    )
    input_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cache_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="document_jobs")
    template: Mapped["Template"] = relationship(back_populates="document_jobs")
    template_version: Mapped["TemplateVersion"] = relationship(back_populates="document_jobs")
    requested_by_user: Mapped["User | None"] = relationship(back_populates="document_jobs")
    artifacts: Mapped[list["DocumentArtifact"]] = relationship(back_populates="document_job")
