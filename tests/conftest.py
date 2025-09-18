"""Shared test fixtures."""

from contextlib import asynccontextmanager
from io import BytesIO
from typing import Any, AsyncIterator, cast
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
import app.services.health_service as health_service_module
from app.main import app
from app.services.storage.models import StorageObject


class InMemoryStorageService:
    """In-memory storage used for API tests that do not need real MinIO."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.bucket_ensured = False

    async def ensure_bucket(self) -> None:
        self.bucket_ensured = True

    async def upload_template(
        self,
        *,
        organization_code: str,
        template_code: str,
        version: str,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        key = f"templates/{organization_code}/{template_code}/{version}/{file_name}"
        self.objects[key] = content
        return StorageObject(
            bucket="documents",
            key=key,
            content_type=content_type,
            size_bytes=len(content),
        )

    async def upload_generated_artifact(
        self,
        *,
        organization_code: str,
        job_id: str,
        artifact_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        key = f"artifacts/{organization_code}/{job_id}/{artifact_name}"
        self.objects[key] = content
        return StorageObject(
            bucket="documents",
            key=key,
            content_type=content_type,
            size_bytes=len(content),
        )

    async def upload_preview(
        self,
        *,
        organization_code: str,
        job_id: str,
        preview_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        key = f"previews/{organization_code}/{job_id}/{preview_name}"
        self.objects[key] = content
        return StorageObject(
            bucket="documents",
            key=key,
            content_type=content_type,
            size_bytes=len(content),
        )

    async def upload_cached_artifact(
        self,
        *,
        organization_code: str,
        cache_key: str,
        artifact_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        key = f"cache/{organization_code}/{cache_key}/{artifact_name}"
        self.objects[key] = content
        return StorageObject(
            bucket="documents",
            key=key,
            content_type=content_type,
            size_bytes=len(content),
        )

    async def download_bytes(self, key: str) -> bytes:
        return self.objects[key]

    async def stat_object(self, key: str) -> StorageObject:
        return StorageObject(
            bucket="documents",
            key=key,
            content_type="application/octet-stream",
            size_bytes=len(self.objects[key]),
        )

    async def get_download_url(self, key: str) -> str:
        return f"https://storage.test/{key}"

    async def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


TEST_STORAGE_SERVICE = InMemoryStorageService()


class TestHealthSession:
    """Minimal async session for health-check database probes."""

    async def execute(self, statement) -> object:
        _ = statement
        return object()


@asynccontextmanager
async def fake_transaction_session() -> AsyncIterator[object]:
    """Provide a no-op transactional session for health checks in tests."""
    yield TestHealthSession()


cast(Any, health_service_module).get_storage_service = lambda: TEST_STORAGE_SERVICE
cast(Any, health_service_module).get_transaction_session = fake_transaction_session
cast(Any, main_module).get_storage_service = lambda: TEST_STORAGE_SERVICE


def create_test_client() -> TestClient:
    """Create a synchronous FastAPI test client."""
    return TestClient(app)


def build_docx_fixture(*document_text: str) -> bytes:
    """Build a minimal DOCX-like zip payload for tests."""
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


@pytest.fixture
def client() -> TestClient:
    """Provide a shared synchronous API client."""
    return create_test_client()
