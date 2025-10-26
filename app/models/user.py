"""User persistence model."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Organization member allowed to manage document workflows."""

    __tablename__ = "users"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.OPERATOR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="users")
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(back_populates="user")
    template_versions: Mapped[list["TemplateVersion"]] = relationship(
        back_populates="created_by_user"
    )
    document_jobs: Mapped[list["DocumentJob"]] = relationship(back_populates="requested_by_user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
