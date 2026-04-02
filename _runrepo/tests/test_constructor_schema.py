"""Tests for the component-driven document constructor schema."""

import pytest
from pydantic import ValidationError

from app.dtos.constructor import (
    ConstructorBindingReference,
    DocumentConstructor,
    HeaderBlock,
    ImageBlock,
    PageBreakBlock,
    SignatureBlock,
    SpacerBlock,
    TableBlock,
    TableColumn,
    TextBlock,
)


def test_constructor_accepts_supported_block_types() -> None:
    """Ensure a mixed constructor payload validates successfully."""
    constructor = DocumentConstructor(
        metadata={"document_type": "certificate"},
        blocks=[
            HeaderBlock(id="header-1", text="Certificate of Completion"),
            TextBlock(
                id="text-1",
                binding=ConstructorBindingReference(key="student_name"),
            ),
            TableBlock(
                id="table-1",
                columns=[
                    TableColumn(key="subject", header="Subject", width_percent=60),
                    TableColumn(key="score", header="Score", width_percent=40),
                ],
                rows_binding=ConstructorBindingReference(key="table_scores"),
            ),
            ImageBlock(
                id="image-1",
                binding=ConstructorBindingReference(key="image_signature"),
                width_mm=40,
                alignment="right",
            ),
            SignatureBlock(
                id="signature-1",
                signer_name=ConstructorBindingReference(key="signer_name"),
                signer_role=ConstructorBindingReference(key="signer_role"),
            ),
            SpacerBlock(id="spacer-1", height_mm=8),
            PageBreakBlock(id="page-break-1"),
        ],
    )

    assert len(constructor.blocks) == 7
    assert constructor.formatting.page.margin_left_mm == 30.0
    assert constructor.formatting.typography.font_family == "Times New Roman"


def test_constructor_rejects_duplicate_block_ids() -> None:
    """Ensure block identifiers stay unique across the constructor."""
    with pytest.raises(ValidationError):
        DocumentConstructor(
            blocks=[
                TextBlock(id="same-id", text="One"),
                SpacerBlock(id="same-id", height_mm=5),
            ]
        )


def test_table_block_rejects_excessive_width_percent() -> None:
    """Ensure table column widths cannot exceed the available page width."""
    with pytest.raises(ValidationError):
        TableBlock(
            id="table-1",
            columns=[
                TableColumn(key="left", header="Left", width_percent=70),
                TableColumn(key="right", header="Right", width_percent=40),
            ],
            rows=[{"left": "A", "right": "B"}],
        )


def test_header_block_requires_text_or_binding() -> None:
    """Ensure header blocks cannot be empty."""
    with pytest.raises(ValidationError):
        HeaderBlock(id="header-1")
