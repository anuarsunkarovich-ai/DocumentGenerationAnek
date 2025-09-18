"""Tests for document request DTO validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.dtos.constructor import ConstructorBindingReference, DocumentConstructor, TextBlock
from app.dtos.document import DocumentJobCreateRequest


def build_constructor() -> DocumentConstructor:
    """Return a minimal valid constructor for request validation tests."""
    return DocumentConstructor(
        blocks=[
            TextBlock(
                id="text-1",
                binding=ConstructorBindingReference(key="student_name"),
            )
        ]
    )


def test_document_job_request_rejects_whitespace_key() -> None:
    """Ensure binding keys cannot hide whitespace mismatches."""
    with pytest.raises(ValidationError):
        DocumentJobCreateRequest(
            organization_id=uuid4(),
            template_id=uuid4(),
            data={" student_name ": "Anek"},
            constructor=build_constructor(),
        )


def test_document_job_request_rejects_unsafe_binding_key() -> None:
    """Ensure binding keys stay predictable for mapping and logging."""
    with pytest.raises(ValidationError):
        DocumentJobCreateRequest(
            organization_id=uuid4(),
            template_id=uuid4(),
            data={"../secret": "Anek"},
            constructor=build_constructor(),
        )
