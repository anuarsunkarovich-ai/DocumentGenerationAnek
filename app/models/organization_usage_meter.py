"""Monthly usage meters for plan enforcement and future billing."""

from datetime import date
from uuid import UUID

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationUsageMeter(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Aggregated monthly usage for one organization."""

    __tablename__ = "organization_usage_meters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "period_start",
            name="uq_organization_usage_meters_org_period",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    generation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    template_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    premium_feature_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    organization: Mapped["Organization"] = relationship(back_populates="usage_meters")
