"""Integration tests for template-related API routes."""

import pytest
from fastapi.testclient import TestClient

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
