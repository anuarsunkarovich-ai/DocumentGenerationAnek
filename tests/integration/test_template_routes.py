"""Integration tests for template-related API routes."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.services.template_service import TemplateService
from tests.conftest import build_docx_fixture

pytestmark = pytest.mark.integration


def test_extract_schema_endpoint_returns_normalized_schema(
    authenticated_client: TestClient,
) -> None:
    """Ensure the template schema extraction route parses DOCX uploads end to end."""
    response = authenticated_client.post(
        "/api/v1/templates/extract-schema",
        files={
            "file": (
                "certificate.docx",
                build_docx_fixture("{{student_name}}", "{{table_scores}}"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["variable_count"] == 2
    assert {item["key"] for item in payload["variables"]} == {
        "student_name",
        "table_scores",
    }


def test_import_analyze_endpoint_returns_detected_candidates(
    authenticated_client: TestClient,
) -> None:
    """Ensure the DOCX import analysis route finds likely fields in normal documents."""
    from tests.test_docx_template_import_service import _build_import_docx

    response = authenticated_client.post(
        "/api/v1/templates/import/analyze",
        files={
            "file": (
                "invoice.docx",
                _build_import_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["candidate_count"] == 3
    assert {item["suggested_binding"] for item in payload["candidates"]} == {
        "amount",
        "client_name",
        "invoice_date",
    }


def test_import_inspect_endpoint_returns_paragraph_inventory(
    authenticated_client: TestClient,
) -> None:
    """Ensure the assisted templateization inspect route returns addressable text regions."""
    from tests.test_docx_template_import_service import _build_import_docx

    response = authenticated_client.post(
        "/api/v1/templates/import/inspect",
        files={
            "file": (
                "invoice.docx",
                _build_import_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["paragraph_count"] >= 3
    assert payload["paragraphs"][0]["text"] == "Client Name: __________"


def test_import_templateize_endpoint_returns_confirmed_bindings(
    authenticated_client: TestClient,
    authenticated_membership,
    monkeypatch,
) -> None:
    """Ensure the manual templateization route accepts explicit selections."""
    organization_id = authenticated_membership.organization_id
    template_id = uuid4()

    async def fake_templateize_import_for_template(
        self: TemplateService,
        *,
        organization_id,
        template_id,
        payload,
    ):
        assert organization_id == authenticated_membership.organization_id
        assert payload.selections[0].binding_key == "client_name"
        return {
            "organization_id": str(organization_id),
            "template_id": str(template_id),
            "template_version_id": str(template_id),
            "render_strategy": "docx_import",
            "inspection": {
                "inspection_checksum": payload.inspection_checksum,
                "paragraph_count": 1,
                "paragraphs": [
                    {
                        "path": "body/p/0",
                        "source_type": "body",
                        "text": "Client Name: __________",
                        "char_count": 23,
                        "table_header_label": None,
                    }
                ],
            },
            "schema": {
                "variable_count": 1,
                "variables": [
                    {
                        "key": "client_name",
                        "label": "Client Name",
                        "placeholder": "__________",
                        "value_type": "string",
                        "component_type": "text",
                        "required": True,
                        "sample_value": None,
                        "occurrences": 1,
                        "sources": ["body/p/0"],
                    }
                ],
                "components": [
                    {
                        "id": "binding-manual",
                        "component": "text",
                        "binding": "client_name",
                        "label": "Client Name",
                        "value_type": "string",
                        "required": True,
                    }
                ],
            },
            "confirmed_binding_count": 1,
            "bindings": [
                {
                    "id": "binding-manual",
                    "candidate_id": "manual-manual",
                    "binding_key": "client_name",
                    "label": "Client Name",
                    "raw_fragment": "__________",
                    "paragraph_path": "body/p/0",
                    "source_type": "body",
                    "detection_kind": "manual_selection",
                    "confidence": 1.0,
                    "preview_text": "Client Name: __________",
                    "value_type": "string",
                    "component_type": "text",
                    "required": True,
                    "sample_value": None,
                    "fragment_start": 13,
                    "fragment_end": 23,
                }
            ],
        }

    monkeypatch.setattr(
        TemplateService,
        "templateize_import_for_template",
        fake_templateize_import_for_template,
    )

    response = authenticated_client.post(
        f"/api/v1/templates/{template_id}/import/templateize",
        json={
            "organization_id": str(organization_id),
            "inspection_checksum": "a" * 64,
            "selections": [
                {
                    "paragraph_path": "body/p/0",
                    "fragment_start": 13,
                    "fragment_end": 23,
                    "binding_key": "client_name",
                    "label": "Client Name",
                }
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["render_strategy"] == "docx_import"
    assert payload["confirmed_binding_count"] == 1
    assert payload["bindings"][0]["binding_key"] == "client_name"
