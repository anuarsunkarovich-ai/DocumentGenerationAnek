"""Template version persistence model."""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class TemplateVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Versioned file and schema snapshot for a template."""

    __tablename__ = "template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
    )

    template_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    variable_schema: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    component_schema: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    template: Mapped["Template"] = relationship(back_populates="versions")
    created_by_user: Mapped["User | None"] = relationship(back_populates="template_versions")
    document_jobs: Mapped[list["DocumentJob"]] = relationship(back_populates="template_version")
    artifacts: Mapped[list["DocumentArtifact"]] = relationship(back_populates="template_version")
