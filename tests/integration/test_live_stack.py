"""Live backend smoke tests against a running Docker stack."""

from __future__ import annotations

import os
import time
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.live_stack]


def build_docx_fixture(*document_text: str) -> bytes:
    """Build a minimal DOCX fixture for live upload and generation checks."""
    body = "".join(f"<w:t>{text}</w:t>" for text in document_text)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def live_stack_config() -> dict[str, str]:
    """Return the environment required to run live-stack smoke tests."""
    if os.getenv("RUN_LIVE_STACK") != "1":
        pytest.skip("Set RUN_LIVE_STACK=1 to run live stack smoke tests.")

    required = {
        "api_base_url": os.getenv("LIVE_API_BASE_URL", "http://127.0.0.1:8000"),
        "email": os.getenv("LIVE_ADMIN_EMAIL"),
        "password": os.getenv("LIVE_ADMIN_PASSWORD"),
        "organization_id": os.getenv("LIVE_ORGANIZATION_ID"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        pytest.fail(f"Missing live stack environment values: {', '.join(sorted(missing))}")
    return {key: value for key, value in required.items() if value is not None}


def wait_for_job_completion(
    client: httpx.Client,
    *,
    task_id: str,
    organization_id: str,
    headers: dict[str, str],
    timeout_seconds: float = 30.0,
) -> dict:
    """Poll one generation job until it reaches a terminal state."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(
            f"/api/v1/documents/jobs/{task_id}",
            params={"organization_id": organization_id},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.5)
    pytest.fail(f"Timed out waiting for job {task_id} to complete.")


def test_live_stack_end_to_end_flow(live_stack_config: dict[str, str]) -> None:
    """Verify the live Docker stack from health checks through cached generation."""
    unique_suffix = uuid4().hex[:8]
    template_code = f"smoke-certificate-{unique_suffix}"
    template_name = f"Smoke Certificate {unique_suffix}"
    template_version = "1.0.0"
    constructor = {
        "locale": "en-US",
        "metadata": {"document_type": "certificate"},
        "blocks": [
            {
                "type": "header",
                "id": "header-1",
                "text": "Certificate",
            },
            {
                "type": "text",
                "id": "text-1",
                "binding": {"key": "student_name"},
            },
        ],
    }
    data_payload = {
        "student_name": "Anek",
    }

    with httpx.Client(base_url=live_stack_config["api_base_url"], timeout=30.0) as client:
        live_response = client.get("/health/live")
        assert live_response.status_code == 200
        assert live_response.json()["status"] == "ok"

        ready_response = client.get("/health/ready")
        assert ready_response.status_code == 200
        ready_payload = ready_response.json()
        assert ready_payload["checks"]["database"]["status"] == "ok"
        assert ready_payload["checks"]["storage"]["status"] == "ok"
        assert ready_payload["checks"]["redis"]["status"] == "ok"

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": live_stack_config["email"],
                "password": live_stack_config["password"],
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        schema_response = client.post(
            "/api/v1/templates/extract-schema",
            headers=headers,
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert schema_response.status_code == 200
        schema_payload = schema_response.json()
        assert schema_payload["variable_count"] == 1

        upload_response = client.post(
            "/api/v1/templates/upload",
            headers=headers,
            data={
                "organization_id": live_stack_config["organization_id"],
                "name": template_name,
                "code": template_code,
                "version": template_version,
                "description": "Live smoke test upload",
                "publish": "true",
            },
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()
        template_id = upload_payload["template"]["id"]
        template_version_id = upload_payload["version"]["id"]

        stored_schema_response = client.post(
            f"/api/v1/templates/{template_id}/extract-schema",
            headers=headers,
            params={"organization_id": live_stack_config["organization_id"]},
        )
        assert stored_schema_response.status_code == 200
        assert stored_schema_response.json()["schema"]["variable_count"] == 1

        generate_response = client.post(
            "/api/v1/documents/generate",
            headers=headers,
            json={
                "organization_id": live_stack_config["organization_id"],
                "template_id": template_id,
                "template_version_id": template_version_id,
                "data": data_payload,
                "constructor": constructor,
            },
        )
        assert generate_response.status_code == 202
        assert generate_response.headers["X-Request-ID"]
        assert generate_response.headers["X-Correlation-ID"]
        generate_payload = generate_response.json()
        assert generate_payload["from_cache"] is False
        assert generate_payload["status"] == "queued"

        completed_job = wait_for_job_completion(
            client,
            task_id=generate_payload["task_id"],
            organization_id=live_stack_config["organization_id"],
            headers=headers,
        )
        assert completed_job["status"] == "completed"
        assert completed_job["from_cache"] is False
        assert completed_job["artifacts"]

        download_response = client.get(
            f"/api/v1/documents/jobs/{generate_payload['task_id']}/download",
            params={"organization_id": live_stack_config["organization_id"]},
            headers=headers,
        )
        assert download_response.status_code == 200
        download_payload = download_response.json()
        assert download_payload["artifact"]["download_url"]
        downloaded_artifact = httpx.get(download_payload["artifact"]["download_url"], timeout=30.0)
        assert downloaded_artifact.status_code == 200
        assert len(downloaded_artifact.content) > 0

        verify_response = client.post(
            "/api/v1/documents/verify",
            headers=headers,
            data={"organization_id": live_stack_config["organization_id"]},
            files={
                "file": (
                    download_payload["artifact"]["file_name"],
                    downloaded_artifact.content,
                    download_payload["artifact"]["content_type"],
                )
            },
        )
        assert verify_response.status_code == 200
        verify_payload = verify_response.json()
        assert verify_payload["matched"] is True
        assert verify_payload["artifact"]["artifact_id"] == download_payload["artifact"]["id"]
        assert verify_payload["artifact"]["task_id"] == generate_payload["task_id"]
        assert verify_payload["artifact"]["verification_code"]

        preview_response = client.get(
            f"/api/v1/documents/jobs/{generate_payload['task_id']}/preview",
            params={"organization_id": live_stack_config["organization_id"]},
            headers=headers,
        )
        assert preview_response.status_code == 200
        preview_url = preview_response.json()["artifact"]["download_url"]
        preview_artifact = httpx.get(preview_url, timeout=30.0)
        assert preview_artifact.status_code == 200
        assert len(preview_artifact.content) > 0

        audit_response = client.get(
            "/api/v1/admin/diagnostics/audit-events",
            params={
                "organization_id": live_stack_config["organization_id"],
                "limit": 25,
            },
            headers=headers,
        )
        assert audit_response.status_code == 200
        audit_payload = audit_response.json()
        assert any(
            event["action"] == "document_job_completed" for event in audit_payload["items"]
        )

        cache_before_response = client.get(
            "/api/v1/admin/diagnostics/cache-stats",
            params={"organization_id": live_stack_config["organization_id"]},
            headers=headers,
        )
        assert cache_before_response.status_code == 200
        assert cache_before_response.json()["completed_jobs"] >= 1

        cached_generate_response = client.post(
            "/api/v1/documents/generate",
            headers=headers,
            json={
                "organization_id": live_stack_config["organization_id"],
                "template_id": template_id,
                "template_version_id": template_version_id,
                "data": data_payload,
                "constructor": constructor,
            },
        )
        assert cached_generate_response.status_code == 202
        cached_payload = cached_generate_response.json()
        assert cached_payload["from_cache"] is True
        assert cached_payload["status"] == "completed"

        cache_after_response = client.get(
            "/api/v1/admin/diagnostics/cache-stats",
            params={"organization_id": live_stack_config["organization_id"]},
            headers=headers,
        )
        assert cache_after_response.status_code == 200
        cache_after_payload = cache_after_response.json()
        assert cache_after_payload["cached_jobs"] >= 1
        assert cache_after_payload["cached_artifacts"] >= 1

        worker_response = client.get(
            "/api/v1/admin/diagnostics/worker-status",
            params={"organization_id": live_stack_config["organization_id"]},
            headers=headers,
        )
        assert worker_response.status_code == 200
        worker_payload = worker_response.json()
        assert worker_payload["queue_depth"] >= 0
        assert worker_payload["workers"]
        assert any(worker["is_online"] for worker in worker_payload["workers"])

        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        assert "document_job_result_total" in metrics_response.text
        assert "http_request_latency_seconds" in metrics_response.text
