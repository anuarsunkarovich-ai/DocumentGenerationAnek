"""Integration tests for billing plan, snapshot, and invoice routes."""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.services.billing_service as billing_service_module
from app.services.billing_service import BillingCycleRunResult, BillingSnapshot

pytestmark = pytest.mark.integration


def test_admin_billing_routes_return_expected_payloads(
    monkeypatch,
    authenticated_client: TestClient,
    authenticated_membership,
) -> None:
    """Billing routes should proxy plan catalog, snapshot, invoice history, and mutations."""
    organization_id = authenticated_membership.organization_id
    issued_at = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
    starter_plan = SimpleNamespace(
        id=uuid4(),
        code="starter",
        name="Starter",
        billable_unit="per_organization",
        monthly_generation_cap=100,
        max_templates=5,
        max_users=3,
        storage_quota_bytes=104857600,
        monthly_price_cents=0,
        currency_code="USD",
        audit_retention_days=30,
        signature_support=False,
        is_active=True,
    )
    growth_plan = SimpleNamespace(
        id=uuid4(),
        code="growth",
        name="Growth",
        billable_unit="per_organization",
        monthly_generation_cap=1000,
        max_templates=50,
        max_users=15,
        storage_quota_bytes=5368709120,
        monthly_price_cents=19900,
        currency_code="USD",
        audit_retention_days=180,
        signature_support=True,
        is_active=True,
    )

    async def fake_list_plans(self, *, session=None):
        _ = session
        return [starter_plan, growth_plan]

    async def fake_get_snapshot(self, *, organization_id, session=None):
        _ = session
        assert organization_id == authenticated_membership.organization_id
        return BillingSnapshot(
            plan=cast(Any, starter_plan),
            subscription=cast(
                Any,
                SimpleNamespace(
                organization_id=organization_id,
                status="active",
                current_period_start=date(2026, 3, 1),
                current_period_end=date(2026, 4, 1),
                pending_plan=growth_plan,
                ),
            ),
            usage_meter=cast(
                Any,
                SimpleNamespace(
                period_start=date(2026, 3, 1),
                period_end=date(2026, 4, 1),
                generation_count=12,
                storage_bytes=4096,
                template_count=4,
                user_count=2,
                premium_feature_usage={"signature_requests": 1},
                ),
            ),
        )

    async def fake_list_invoices(self, *, organization_id, limit, session=None):
        _ = session
        assert organization_id == authenticated_membership.organization_id
        assert limit == 10
        return [
            SimpleNamespace(
                id=uuid4(),
                organization_id=organization_id,
                organization_plan_id=uuid4(),
                plan_definition_id=starter_plan.id,
                plan_code="starter",
                currency_code="USD",
                status="issued",
                period_start=date(2026, 2, 1),
                period_end=date(2026, 3, 1),
                subtotal_cents=0,
                generation_count=9,
                template_count=4,
                user_count=2,
                storage_bytes=4096,
                premium_feature_usage={},
                line_items=[],
                issued_at=issued_at,
                due_at=issued_at,
                paid_at=None,
                created_at=issued_at,
            )
        ]

    async def fake_schedule_plan_change(self, *, organization_id, target_plan_code, session=None):
        _ = session
        assert organization_id == authenticated_membership.organization_id
        assert target_plan_code == "growth"
        return BillingSnapshot(
            plan=cast(Any, starter_plan),
            subscription=cast(
                Any,
                SimpleNamespace(
                organization_id=organization_id,
                status="active",
                current_period_start=date(2026, 3, 1),
                current_period_end=date(2026, 4, 1),
                pending_plan=growth_plan,
                ),
            ),
            usage_meter=cast(
                Any,
                SimpleNamespace(
                period_start=date(2026, 3, 1),
                period_end=date(2026, 4, 1),
                generation_count=12,
                storage_bytes=4096,
                template_count=4,
                user_count=2,
                premium_feature_usage={},
                ),
            ),
        )

    async def fake_run_billing_cycle(self, *, organization_id=None, as_of=None, session=None):
        _ = as_of, session
        assert organization_id == authenticated_membership.organization_id
        return BillingCycleRunResult(
            finalized_invoice_count=1,
            renewed_subscription_count=1,
            billed_organization_ids=[organization_id],
        )

    monkeypatch.setattr(billing_service_module.BillingService, "list_plans", fake_list_plans)
    monkeypatch.setattr(
        billing_service_module.BillingService,
        "get_billing_snapshot",
        fake_get_snapshot,
    )
    monkeypatch.setattr(
        billing_service_module.BillingService,
        "list_invoices",
        fake_list_invoices,
    )
    monkeypatch.setattr(
        billing_service_module.BillingService,
        "schedule_plan_change",
        fake_schedule_plan_change,
    )
    monkeypatch.setattr(
        billing_service_module.BillingService,
        "run_billing_cycle",
        fake_run_billing_cycle,
    )

    plans_response = authenticated_client.get(
        "/api/v1/admin/billing/plans",
        params={"organization_id": str(organization_id)},
    )
    snapshot_response = authenticated_client.get(
        "/api/v1/admin/billing/snapshot",
        params={"organization_id": str(organization_id)},
    )
    invoices_response = authenticated_client.get(
        "/api/v1/admin/billing/invoices",
        params={"organization_id": str(organization_id), "limit": 10},
    )
    change_response = authenticated_client.post(
        "/api/v1/admin/billing/subscription/change",
        json={"organization_id": str(organization_id), "target_plan_code": "growth"},
    )
    cycle_response = authenticated_client.post(
        "/api/v1/admin/billing/cycle/run",
        json={"organization_id": str(organization_id)},
    )

    assert plans_response.status_code == 200
    assert [item["code"] for item in plans_response.json()["items"]] == ["starter", "growth"]
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["subscription"]["pending_plan"]["code"] == "growth"
    assert invoices_response.status_code == 200
    assert invoices_response.json()["items"][0]["plan_code"] == "starter"
    assert change_response.status_code == 200
    assert change_response.json()["subscription"]["pending_plan"]["code"] == "growth"
    assert cycle_response.status_code == 200
    assert cycle_response.json()["finalized_invoice_count"] == 1
