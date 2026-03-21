"""Repository for generated billing invoices."""

from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing_invoice import BillingInvoice


class BillingInvoiceRepository:
    """Access invoice history for organization billing periods."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_period(
        self,
        *,
        organization_id: UUID,
        period_start: date,
        period_end: date,
    ) -> BillingInvoice | None:
        """Return the invoice for one organization-period if it already exists."""
        statement: Select[tuple[BillingInvoice]] = (
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.plan))
            .where(
                BillingInvoice.organization_id == organization_id,
                BillingInvoice.period_start == period_start,
                BillingInvoice.period_end == period_end,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(self, invoice: BillingInvoice) -> BillingInvoice:
        """Persist one invoice."""
        self._session.add(invoice)
        await self._session.flush()
        await self._session.refresh(invoice)
        return invoice

    async def list_for_organization(
        self,
        *,
        organization_id: UUID,
        limit: int,
    ) -> list[BillingInvoice]:
        """Return recent invoices for one organization."""
        statement: Select[tuple[BillingInvoice]] = (
            select(BillingInvoice)
            .options(selectinload(BillingInvoice.plan))
            .where(BillingInvoice.organization_id == organization_id)
            .order_by(BillingInvoice.period_start.desc(), BillingInvoice.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())
