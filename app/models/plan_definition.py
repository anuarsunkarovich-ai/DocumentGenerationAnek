"""Subscription plan definitions for per-organization billing."""

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PlanDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Commercial plan limits and feature flags."""

    __tablename__ = "plan_definitions"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    billable_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="per_organization")
    monthly_generation_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    max_templates: Mapped[int] = mapped_column(Integer, nullable=False)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    audit_retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_support: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization_plans: Mapped[list["OrganizationPlan"]] = relationship(back_populates="plan")
