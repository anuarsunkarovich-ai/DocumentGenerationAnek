"""Template persistence model."""

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TemplateStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Template(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Logical template container with multiple file versions."""

    __tablename__ = "templates"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_templates_org_code"),)

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus, name="template_status"),
        default=TemplateStatus.DRAFT,
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="templates")
    versions: Mapped[list["TemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )
    document_jobs: Mapped[list["DocumentJob"]] = relationship(back_populates="template")
