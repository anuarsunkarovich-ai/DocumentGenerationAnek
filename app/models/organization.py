"""Organization persistence model."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tenant boundary for templates, jobs, and users."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(back_populates="organization")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="organization")
    api_key_usage_logs: Mapped[list["ApiKeyUsageLog"]] = relationship(
        back_populates="organization"
    )
    organization_plan: Mapped["OrganizationPlan | None"] = relationship(
        back_populates="organization",
        uselist=False,
    )
    usage_meters: Mapped[list["OrganizationUsageMeter"]] = relationship(
        back_populates="organization"
    )
    billing_invoices: Mapped[list["BillingInvoice"]] = relationship(
        back_populates="organization"
    )
    templates: Mapped[list["Template"]] = relationship(back_populates="organization")
    document_jobs: Mapped[list["DocumentJob"]] = relationship(back_populates="organization")
    document_artifacts: Mapped[list["DocumentArtifact"]] = relationship(
        back_populates="organization"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="organization")
