"""Tests for persisting confirmed imported-DOCX bindings."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.template_service as template_service_module
from app.dtos.template import TemplateImportConfirmRequest, TemplateImportTemplateizeRequest
from app.services.template_service import TemplateService
from tests.test_docx_template_import_service import _build_import_docx


@pytest.mark.anyio
async def test_template_service_confirms_import_bindings_for_current_version(monkeypatch) -> None:
    """Confirmed bindings should be persisted onto the current template version."""
    organization_id = uuid4()
    template_id = uuid4()
    version_id = uuid4()
    docx_bytes = _build_import_docx()
    state: dict[str, object] = {"updated": None}

    current_version = SimpleNamespace(
        id=version_id,
        version="1.0.0",
        is_current=True,
        is_published=True,
        original_filename="invoice.docx",
        storage_key="templates/finance/invoice/1.0.0/invoice.docx",
        checksum=None,
        notes=None,
        render_strategy="constructor",
        import_bindings=[],
        variable_schema={},
    )
    template = SimpleNamespace(
        id=template_id,
        organization_id=organization_id,
        code="invoice",
        name="Invoice",
        versions=[current_version],
    )

    service = TemplateService()
    analysis = service._import_service.analyze("invoice.docx", docx_bytes)  # noqa: SLF001
    payload = TemplateImportConfirmRequest(
        organization_id=organization_id,
        analysis_checksum=analysis.analysis_checksum,
        bindings=[
            {
                "candidate_id": candidate.id,
                "binding_key": candidate.suggested_binding,
                "label": candidate.label,
            }
            for candidate in analysis.candidates
        ],
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeTemplateRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, *, template_id, organization_id, published_only=False):
            _ = published_only
            if template_id == template.id and organization_id == template.organization_id:
                return template
            return None

    class FakeTemplateVersionRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def update_import_configuration(
            self,
            template_version,
            *,
            render_strategy,
            import_analysis,
            import_bindings,
            variable_schema,
            component_schema,
        ):
            template_version.render_strategy = render_strategy
            template_version.import_bindings = import_bindings
            template_version.variable_schema = variable_schema
            state["updated"] = {
                "template_version": template_version,
                "render_strategy": render_strategy,
                "import_analysis": import_analysis,
                "import_bindings": import_bindings,
                "variable_schema": variable_schema,
                "component_schema": component_schema,
            }
            return template_version

    class FakeStorageService:
        async def download_bytes(self, key: str) -> bytes:
            assert key == current_version.storage_key
            return docx_bytes

    monkeypatch.setattr(template_service_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(template_service_module, "TemplateRepository", FakeTemplateRepository)
    monkeypatch.setattr(
        template_service_module,
        "TemplateVersionRepository",
        FakeTemplateVersionRepository,
    )

    service._storage_service = FakeStorageService()  # type: ignore[assignment]
    response = await service.confirm_import_for_template(
        organization_id=organization_id,
        template_id=template_id,
        payload=payload,
    )

    assert response.template_id == template_id
    assert response.template_version_id == version_id
    assert response.render_strategy == "docx_import"
    assert response.confirmed_binding_count == 3
    assert response.schema_payload.variable_count == 3
    assert state["updated"] is not None


@pytest.mark.anyio
async def test_template_service_templateizes_manual_selections_for_current_version(
    monkeypatch,
) -> None:
    """Manual selections should persist as imported-DOCX bindings on the current version."""
    organization_id = uuid4()
    template_id = uuid4()
    version_id = uuid4()
    docx_bytes = _build_import_docx()
    state: dict[str, object] = {"updated": None}

    current_version = SimpleNamespace(
        id=version_id,
        version="1.0.0",
        is_current=True,
        is_published=True,
        original_filename="invoice.docx",
        storage_key="templates/finance/invoice/1.0.0/invoice.docx",
        checksum=None,
        notes=None,
        render_strategy="constructor",
        import_bindings=[],
        variable_schema={},
    )
    template = SimpleNamespace(
        id=template_id,
        organization_id=organization_id,
        code="invoice",
        name="Invoice",
        versions=[current_version],
    )

    service = TemplateService()
    inspection = service._import_service.inspect("invoice.docx", docx_bytes)  # noqa: SLF001
    payload = TemplateImportTemplateizeRequest(
        organization_id=organization_id,
        inspection_checksum=inspection.inspection_checksum,
        selections=[
            {
                "paragraph_path": "body/p/0",
                "fragment_start": 13,
                "fragment_end": 23,
                "binding_key": "client_name",
                "label": "Client Name",
            }
        ],
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeTemplateRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def get_by_id(self, *, template_id, organization_id, published_only=False):
            _ = published_only
            if template_id == template.id and organization_id == template.organization_id:
                return template
            return None

    class FakeTemplateVersionRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def update_import_configuration(
            self,
            template_version,
            *,
            render_strategy,
            import_analysis,
            import_bindings,
            variable_schema,
            component_schema,
        ):
            template_version.render_strategy = render_strategy
            template_version.import_bindings = import_bindings
            template_version.variable_schema = variable_schema
            state["updated"] = {
                "template_version": template_version,
                "render_strategy": render_strategy,
                "import_analysis": import_analysis,
                "import_bindings": import_bindings,
                "variable_schema": variable_schema,
                "component_schema": component_schema,
            }
            return template_version

    class FakeStorageService:
        async def download_bytes(self, key: str) -> bytes:
            assert key == current_version.storage_key
            return docx_bytes

    monkeypatch.setattr(template_service_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(template_service_module, "TemplateRepository", FakeTemplateRepository)
    monkeypatch.setattr(
        template_service_module,
        "TemplateVersionRepository",
        FakeTemplateVersionRepository,
    )

    service._storage_service = FakeStorageService()  # type: ignore[assignment]
    response = await service.templateize_import_for_template(
        organization_id=organization_id,
        template_id=template_id,
        payload=payload,
    )

    assert response.template_id == template_id
    assert response.template_version_id == version_id
    assert response.render_strategy == "docx_import"
    assert response.confirmed_binding_count == 1
    assert response.bindings[0].binding_key == "client_name"
    assert response.bindings[0].raw_fragment == "__________"
    assert state["updated"] is not None
