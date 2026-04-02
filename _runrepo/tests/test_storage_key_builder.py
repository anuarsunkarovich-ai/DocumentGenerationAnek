"""Tests for storage key construction."""

import pytest

from app.core.config import StorageSettings
from app.services.storage.key_builder import (
    InvalidStorageKeySegmentError,
    StorageKeyBuilder,
)


def test_template_key_uses_template_prefix() -> None:
    """Ensure template keys use the expected path structure."""
    settings = StorageSettings()
    builder = StorageKeyBuilder(settings)

    result = builder.template_key(
        organization_code="math-dept",
        template_code="certificate",
        version="1.0.0",
        file_name="certificate.docx",
    )

    assert result == "templates/math-dept/certificate/1.0.0/certificate.docx"


def test_cache_key_uses_cache_prefix() -> None:
    """Ensure cached artifact keys use the cache prefix."""
    settings = StorageSettings()
    builder = StorageKeyBuilder(settings)

    result = builder.cache_key(
        organization_code="math-dept",
        cache_key="abc123",
        artifact_name="certificate.pdf",
    )

    assert result == "cache/math-dept/abc123/certificate.pdf"


def test_template_key_strips_directory_from_file_name() -> None:
    """Ensure only the file base name is kept in template object keys."""
    settings = StorageSettings()
    builder = StorageKeyBuilder(settings)

    result = builder.template_key(
        organization_code="math-dept",
        template_code="certificate",
        version="1.0.0",
        file_name="../unsafe/certificate.docx",
    )

    assert result == "templates/math-dept/certificate/1.0.0/certificate.docx"


def test_cache_key_rejects_nested_segments() -> None:
    """Ensure nested path segments are rejected for tenant keys."""
    settings = StorageSettings()
    builder = StorageKeyBuilder(settings)

    with pytest.raises(InvalidStorageKeySegmentError):
        builder.cache_key(
            organization_code="math/dept",
            cache_key="abc123",
            artifact_name="certificate.pdf",
        )
