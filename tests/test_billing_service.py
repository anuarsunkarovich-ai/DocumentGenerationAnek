"""Tests for plan provisioning, metering, and billing enforcement."""

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

import app.services.billing_service as billing_service_module
from app.core.exceptions import ConflictError
from app.dtos.constructor import DocumentConstructor
from app.services.billing_service import BillingService


def build_constructor(*, include_signature: bool = False) -> DocumentConstructor:
    """Build a minimal constructor payload for billing tests."""
    blocks: list[dict[str, object]] = [
        {
            "type": "text",
            "id": "text-1",
            "text": "Certificate body",
        }
    ]
    if include_signature:
        blocks.append(
            {
                "type": "signature",
                "id": "signature-1",
                "signer_name": {"key": "signer_name"},
            }
        )
    return DocumentConstructor.model_validate({"blocks": blocks})


def install_billing_test_doubles(monkeypatch, state: dict) -> None:
    """Patch billing repositories with in-memory doubles."""

    class FakeOrganizationRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, organization_id):
            organization = state["organizations"].get(organization_id)
            if organization is None:
                return None
            return SimpleNamespace(**organization)

    class FakePlanDefinitionRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_code(self, code: str):
            return state["plans_by_code"].get(code)

    class FakeOrganizationPlanRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_organization_id(self, organization_id):
            return state["subscriptions"].get(organization_id)

        async def create(self, organization_plan):
            created_plan = SimpleNamespace(
                organization_id=organization_plan.organization_id,
                plan_definition_id=organization_plan.plan_definition_id,
                status=organization_plan.status,
                current_period_start=organization_plan.current_period_start,
                current_period_end=organization_plan.current_period_end,
                plan=state["plans_by_id"][organization_plan.plan_definition_id],
            )
            state["subscriptions"][organization_plan.organization_id] = created_plan
            return created_plan

        async def update_period(self, organization_plan, *, period_start, period_end):
            organization_plan.current_period_start = period_start
            organization_plan.current_period_end = period_end
            return organization_plan

    class FakeOrganizationUsageMeterRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_period(self, *, organization_id, period_start):
            return state["usage_meters"].get((organization_id, period_start))

        async def create(self, usage_meter):
            state["usage_meters"][(usage_meter.organization_id, usage_meter.period_start)] = usage_meter
            return usage_meter

        async def increment_generation(self, usage_meter, amount: int = 1):
            usage_meter.generation_count += amount

        async def adjust_storage_bytes(self, usage_meter, *, delta_bytes: int):
            usage_meter.storage_bytes += delta_bytes

        async def set_template_count(self, usage_meter, *, template_count: int):
            usage_meter.template_count = template_count

        async def set_user_count(self, usage_meter, *, user_count: int):
            usage_meter.user_count = user_count

        async def increment_premium_feature(self, usage_meter, *, feature_key: str, amount: int = 1):
            usage_meter.premium_feature_usage[feature_key] = (
                int(usage_meter.premium_feature_usage.get(feature_key, 0)) + amount
            )

    class FakeTemplateRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def count_by_organization(self, organization_id):
            return int(state["template_counts"].get(organization_id, 0))

    class FakeUserRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def count_active_for_organization(self, organization_id):
            return int(state["user_counts"].get(organization_id, 0))

    class FakeTemplateVersionRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def sum_storage_bytes_for_organization(self, organization_id):
            return int(state["template_storage_bytes"].get(organization_id, 0))

    class FakeDocumentArtifactRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def sum_storage_bytes_for_organization(self, organization_id):
            return int(state["artifact_storage_bytes"].get(organization_id, 0))

    monkeypatch.setattr(
        billing_service_module,
        "OrganizationRepository",
        FakeOrganizationRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "PlanDefinitionRepository",
        FakePlanDefinitionRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "OrganizationPlanRepository",
        FakeOrganizationPlanRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "OrganizationUsageMeterRepository",
        FakeOrganizationUsageMeterRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "TemplateRepository",
        FakeTemplateRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "UserRepository",
        FakeUserRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "TemplateVersionRepository",
        FakeTemplateVersionRepository,
    )
    monkeypatch.setattr(
        billing_service_module,
        "DocumentArtifactRepository",
        FakeDocumentArtifactRepository,
    )


def build_billing_state() -> dict:
    """Build in-memory plan and usage state for billing tests."""
    organization_id = uuid4()
    starter_plan = SimpleNamespace(
        id=uuid4(),
        code="starter",
        name="Starter",
        billable_unit="per_organization",
        monthly_generation_cap=2,
        max_templates=3,
        max_users=2,
        storage_quota_bytes=1000,
        audit_retention_days=30,
        signature_support=False,
        is_active=True,
    )
    growth_plan = SimpleNamespace(
        id=uuid4(),
        code="growth",
        name="Growth",
        billable_unit="per_organization",
        monthly_generation_cap=20,
        max_templates=20,
        max_users=10,
        storage_quota_bytes=100000,
        audit_retention_days=180,
        signature_support=True,
        is_active=True,
    )
    return {
        "organization_id": organization_id,
        "organizations": {
            organization_id: {
                "id": organization_id,
                "name": "Math Department",
                "code": "math-dept",
                "is_active": True,
            }
        },
        "plans_by_code": {"starter": starter_plan, "growth": growth_plan},
        "plans_by_id": {starter_plan.id: starter_plan, growth_plan.id: growth_plan},
        "subscriptions": {},
        "usage_meters": {},
        "template_counts": {organization_id: 1},
        "user_counts": {organization_id: 1},
        "template_storage_bytes": {organization_id: 120},
        "artifact_storage_bytes": {organization_id: 80},
    }


@pytest.mark.anyio
async def test_billing_service_provisions_default_starter_plan(monkeypatch) -> None:
    """Organizations without a subscription should get the seeded starter plan on first access."""
    state = build_billing_state()
    install_billing_test_doubles(monkeypatch, state)

    snapshot = await BillingService().get_billing_snapshot(
        organization_id=state["organization_id"],
        session=cast(Any, object()),
    )

    assert snapshot.plan.code == "starter"
    assert snapshot.usage_meter.template_count == 1
    assert snapshot.usage_meter.user_count == 1
    assert snapshot.usage_meter.storage_bytes == 200


@pytest.mark.anyio
async def test_billing_service_rejects_generation_over_cap(monkeypatch) -> None:
    """Generation requests should stop once the monthly cap is reached."""
    state = build_billing_state()
    install_billing_test_doubles(monkeypatch, state)
    service = BillingService()
    snapshot = await service.get_billing_snapshot(
        organization_id=state["organization_id"],
        session=cast(Any, object()),
    )
    snapshot.usage_meter.generation_count = snapshot.plan.monthly_generation_cap

    with pytest.raises(ConflictError, match="Monthly document generation cap exceeded"):
        await service.enforce_generation_allowed(
            organization_id=state["organization_id"],
            constructor=build_constructor(),
            session=cast(Any, object()),
        )


@pytest.mark.anyio
async def test_billing_service_rejects_signature_feature_on_starter(monkeypatch) -> None:
    """Starter plans should not allow signature blocks."""
    state = build_billing_state()
    install_billing_test_doubles(monkeypatch, state)

    with pytest.raises(ConflictError, match="Signature blocks are not available"):
        await BillingService().enforce_generation_allowed(
            organization_id=state["organization_id"],
            constructor=build_constructor(include_signature=True),
            session=cast(Any, object()),
        )


@pytest.mark.anyio
async def test_billing_service_rejects_template_and_storage_limits(monkeypatch) -> None:
    """Template count and storage quota should both be enforced."""
    state = build_billing_state()
    install_billing_test_doubles(monkeypatch, state)
    service = BillingService()
    state["template_counts"][state["organization_id"]] = 3

    with pytest.raises(ConflictError, match="Template limit exceeded"):
        await service.enforce_template_creation_allowed(
            organization_id=state["organization_id"],
            session=cast(Any, object()),
        )

    with pytest.raises(ConflictError, match="Storage quota exceeded"):
        await service.enforce_storage_delta_allowed(
            organization_id=state["organization_id"],
            additional_bytes=1000,
            session=cast(Any, object()),
        )


@pytest.mark.anyio
async def test_billing_service_records_generation_storage_and_premium_usage(monkeypatch) -> None:
    """Accepted generation and storage writes should update the current usage meter."""
    state = build_billing_state()
    install_billing_test_doubles(monkeypatch, state)
    service = BillingService()

    await service.record_generation_request(
        organization_id=state["organization_id"],
        constructor=build_constructor(include_signature=True),
        session=cast(Any, object()),
    )
    await service.record_storage_usage(
        organization_id=state["organization_id"],
        delta_bytes=250,
        session=cast(Any, object()),
    )

    snapshot = await service.get_billing_snapshot(
        organization_id=state["organization_id"],
        session=cast(Any, object()),
    )

    assert snapshot.usage_meter.generation_count == 1
    assert snapshot.usage_meter.storage_bytes == 450
    assert snapshot.usage_meter.premium_feature_usage["signature_requests"] == 1
