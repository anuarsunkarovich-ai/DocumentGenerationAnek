"""Organization-to-plan assignments for billing enforcement."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Current plan assignment and billing period boundaries for one organization."""

    __tablename__ = "organization_plans"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan_definition_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("plan_definitions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pending_plan_definition_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("plan_definitions.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    current_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    organization: Mapped["Organization"] = relationship(back_populates="organization_plan")
    plan: Mapped["PlanDefinition"] = relationship(
        back_populates="organization_plans",
        foreign_keys=[plan_definition_id],
    )
    pending_plan: Mapped["PlanDefinition | None"] = relationship(
        back_populates="pending_organization_plans",
        foreign_keys=[pending_plan_definition_id],
    )
    billing_invoices: Mapped[list["BillingInvoice"]] = relationship(back_populates="subscription")
