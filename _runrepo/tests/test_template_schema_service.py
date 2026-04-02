"""Tests for DOCX template schema extraction."""

import zipfile
from io import BytesIO

from app.services.template_schema_service import TemplateSchemaService


def test_extract_schema_collects_variables_from_docx_parts() -> None:
    """Ensure the extractor finds placeholders across document and header XML."""
    docx_bytes = _build_docx(
        {
            "word/document.xml": (
                "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                "<w:body><w:p><w:r><w:t>{{student_name}}</w:t></w:r>"
                "<w:r><w:t>{{table_scores}}</w:t></w:r></w:p></w:body></w:document>"
            ),
            "word/header1.xml": (
                "<w:hdr xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                "<w:p><w:r><w:t>{{student_name}}</w:t></w:r>"
                "<w:r><w:t>{{image_signature}}</w:t></w:r></w:p></w:hdr>"
            ),
        }
    )

    service = TemplateSchemaService()

    schema = service.extract_schema("certificate.docx", docx_bytes)

    assert schema.variable_count == 3
    assert [item.key for item in schema.variables] == [
        "image_signature",
        "student_name",
        "table_scores",
    ]
    assert next(item for item in schema.variables if item.key == "student_name").occurrences == 2
    assert (
        next(item for item in schema.variables if item.key == "table_scores").component_type
        == "table"
    )
    assert (
        next(item for item in schema.variables if item.key == "image_signature").value_type
        == "image"
    )


def _build_docx(parts: dict[str, str]) -> bytes:
    """Create a minimal DOCX archive for extractor tests."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        for name, content in parts.items():
            archive.writestr(name, content)
    return buffer.getvalue()
