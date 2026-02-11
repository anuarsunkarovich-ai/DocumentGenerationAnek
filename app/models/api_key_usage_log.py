"""Usage-log persistence model for API-key requests."""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ApiKeyUsageLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Trace one API-key-authenticated request."""

    __tablename__ = "api_key_usage_logs"

    api_key_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    rate_limited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    api_key: Mapped["ApiKey"] = relationship(back_populates="usage_logs")
    organization: Mapped["Organization"] = relationship(back_populates="api_key_usage_logs")
