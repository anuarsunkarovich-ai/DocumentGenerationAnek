"""Document artifact persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ArtifactKind
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Generated file stored for download, preview, or cache reuse."""

    __tablename__ = "document_artifacts"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_job_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("document_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_version_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("template_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[ArtifactKind] = mapped_column(
        Enum(ArtifactKind, name="artifact_kind"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="document_artifacts")
    document_job: Mapped["DocumentJob | None"] = relationship(back_populates="artifacts")
    template_version: Mapped["TemplateVersion"] = relationship(back_populates="artifacts")
