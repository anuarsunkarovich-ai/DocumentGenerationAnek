"""Tests for artifact authenticity verification."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest

import app.services.document_verification_service as verification_module
from app.core.exceptions import ValidationError
from app.models.enums import ArtifactKind
from app.services.document_verification_service import DocumentVerificationService


@pytest.mark.anyio
async def test_verify_matches_uploaded_file(monkeypatch) -> None:
    """Uploaded file bytes should resolve to a matching artifact fingerprint."""
    organization_id = uuid4()
    task_id = uuid4()
    artifact_id = uuid4()
    file_bytes = b"generated-certificate"
    authenticity_hash = sha256(file_bytes).hexdigest()
    artifact = SimpleNamespace(
        id=artifact_id,
        document_job_id=task_id,
        kind=ArtifactKind.PDF,
        file_name="certificate-1.0.0.pdf",
        content_type="application/pdf",
        size_bytes=len(file_bytes),
        created_at=datetime(2026, 2, 21, 9, 30, tzinfo=timezone.utc),
        checksum=authenticity_hash,
    )

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeDocumentArtifactRepository:
        def __init__(self, session: object) -> None:
            _ = session

        async def list_by_checksum(self, *, organization_id: object, checksum: str):
            assert organization_id == expected_organization_id
            assert checksum == authenticity_hash
            return [artifact]

    expected_organization_id = organization_id

    monkeypatch.setattr(verification_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(
        verification_module,
        "DocumentArtifactRepository",
        FakeDocumentArtifactRepository,
    )

    response = await DocumentVerificationService().verify(
        organization_id=organization_id,
        file_bytes=file_bytes,
    )

    assert response.matched is True
    assert response.provided_hash == authenticity_hash
    assert response.matched_artifact_count == 1
    assert response.artifact is not None
    assert response.artifact.artifact_id == artifact_id
    assert response.artifact.task_id == task_id
    assert response.artifact.authenticity_hash == authenticity_hash
    assert response.artifact.verification_code.startswith("VER-")


@pytest.mark.anyio
async def test_verify_rejects_both_file_and_hash() -> None:
    """Verification should reject ambiguous inputs."""
    with pytest.raises(ValidationError, match="either a file or an authenticity hash"):
        await DocumentVerificationService().verify(
            organization_id=uuid4(),
            authenticity_hash="a" * 64,
            file_bytes=b"data",
        )
