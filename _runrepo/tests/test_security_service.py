"""Tests for request-boundary security validation."""

from base64 import b64encode
from io import BytesIO
from zipfile import ZipFile

import pytest

from app.core.exceptions import ValidationError
from app.services.security_service import SecurityService


def build_docx_like_bytes() -> bytes:
    """Return a minimal zip payload that looks like a DOCX package."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", "<w:document></w:document>")
    return buffer.getvalue()


def test_validate_template_upload_sanitizes_name() -> None:
    """Ensure upload validation strips unsafe path segments from file names."""
    service = SecurityService()

    result = service.validate_template_upload(
        file_name="../unsafe/final-template.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=build_docx_like_bytes(),
    )

    assert result == "final-template.docx"


def test_validate_template_upload_rejects_non_docx_bytes() -> None:
    """Ensure renamed non-zip uploads are rejected early."""
    service = SecurityService()

    with pytest.raises(ValidationError):
        service.validate_template_upload(
            file_name="fake.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=b"not-a-real-docx",
        )


def test_validate_template_storage_key_rejects_foreign_prefix() -> None:
    """Ensure callers cannot register files outside their tenant template area."""
    service = SecurityService()

    with pytest.raises(ValidationError):
        service.validate_template_storage_key(
            storage_key="templates/other-org/certificate/1.0/file.docx",
            organization_code="math-dept",
        )


def test_validate_image_data_url_rejects_plain_path() -> None:
    """Ensure image references cannot point at filesystem paths."""
    service = SecurityService()

    with pytest.raises(ValidationError):
        service.validate_image_data_url("C:/temp/signature.png")


def test_validate_image_data_url_accepts_small_png() -> None:
    """Ensure valid inline images remain supported."""
    service = SecurityService()
    encoded = b64encode(b"fake-png-bytes").decode("ascii")

    result = service.validate_image_data_url(f"data:image/png;base64,{encoded}")

    assert result.startswith("data:image/png;base64,")
