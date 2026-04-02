"""Invoice records generated from organization billing periods."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BIGINT,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BillingInvoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persist one finalized invoice for an organization-period."""

    __tablename__ = "billing_invoices"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "period_start",
            "period_end",
            name="uq_billing_invoices_org_period",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organization_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("plan_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    template_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BIGINT, nullable=False, default=0)
    premium_feature_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    line_items: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="billing_invoices")
    subscription: Mapped["OrganizationPlan"] = relationship(back_populates="billing_invoices")
    plan: Mapped["PlanDefinition"] = relationship(back_populates="billing_invoices")
