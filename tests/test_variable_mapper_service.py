"""Tests for variable mapping in the generation pipeline."""

from uuid import uuid4

from app.dtos.constructor import (
    ConstructorBindingReference,
    DocumentConstructor,
    SignatureBlock,
    TableBlock,
    TableColumn,
    TextBlock,
)
from app.services.generation.models import ResolvedTemplateContext
from app.services.generation.variable_mapper_service import VariableMapperService


def test_variable_mapper_resolves_bound_blocks() -> None:
    """Ensure constructor bindings are mapped into renderable blocks."""
    constructor = DocumentConstructor(
        blocks=[
            TextBlock(
                id="text-1",
                binding=ConstructorBindingReference(key="student_name"),
            ),
            TableBlock(
                id="table-1",
                columns=[
                    TableColumn(key="subject", header="Subject"),
                    TableColumn(key="score", header="Score"),
                ],
                rows_binding=ConstructorBindingReference(key="scores"),
            ),
            SignatureBlock(
                id="signature-1",
                signer_name=ConstructorBindingReference(key="signer_name"),
            ),
        ]
    )
    context = ResolvedTemplateContext(
        template_id=uuid4(),
        template_version_id=uuid4(),
        organization_id=uuid4(),
        organization_code="math-dept",
        template_code="certificate",
        template_name="Certificate",
        template_version="1.0.0",
        original_filename="certificate.docx",
        variable_schema={},
    )

    service = VariableMapperService()
    resolved_document, normalized_payload, cache_key = service.map_document(
        context=context,
        constructor=constructor,
        data={
            "student_name": "Anek",
            "scores": [{"subject": "Math", "score": "95"}],
            "signer_name": "Dean Office",
        },
    )

    assert normalized_payload["student_name"] == "Anek"
    assert cache_key
    assert resolved_document.blocks[0].content["text"] == "Anek"
    assert resolved_document.blocks[1].content["rows"][0]["score"] == "95"
    assert resolved_document.blocks[2].content["signer_name"] == "Dean Office"
