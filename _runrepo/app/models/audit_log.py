"""Audit log persistence model."""

from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AuditAction
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit event for operational and compliance tracking."""

    __tablename__ = "audit_logs"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="audit_logs")
    user: Mapped["User | None"] = relationship(back_populates="audit_logs")
