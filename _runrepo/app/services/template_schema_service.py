"""Services for extracting normalized schemas from DOCX templates."""

import re
import zipfile
from io import BytesIO
from typing import TypedDict
from xml.etree import ElementTree

from app.core.exceptions import ValidationError
from app.dtos.template import (
    TemplateComponentSchemaItem,
    TemplateSchemaResponse,
    TemplateVariableSchemaItem,
)

VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z0-9][A-Za-z0-9_.-]*)\s*}}")


class VariableEntry(TypedDict):
    """Typed accumulator for one extracted template variable."""

    label: str
    value_type: str
    component_type: str
    occurrences: int
    sources: set[str]


class TemplateSchemaService:
    """Extract variables and normalized component schemas from DOCX files."""

    def extract_schema(self, file_name: str, content: bytes) -> TemplateSchemaResponse:
        """Build a frontend-friendly schema from a DOCX template."""
        self._ensure_docx(file_name=file_name, content=content)

        variable_index: dict[str, VariableEntry] = {}
        for source_name, part_text in self._iter_docx_text_parts(content):
            for match in VARIABLE_PATTERN.finditer(part_text):
                key = match.group(1)
                entry = variable_index.setdefault(
                    key,
                    {
                        "label": self._label_from_key(key),
                        "value_type": self._infer_value_type(key),
                        "component_type": self._infer_component_type(key),
                        "occurrences": 0,
                        "sources": set(),
                    },
                )
                entry["occurrences"] = int(entry["occurrences"]) + 1
                entry["sources"].add(source_name)

        variables = [
            TemplateVariableSchemaItem(
                key=key,
                label=str(entry["label"]),
                placeholder=f"{{{{{key}}}}}",
                value_type=str(entry["value_type"]),
                component_type=str(entry["component_type"]),
                occurrences=int(entry["occurrences"]),
                sources=sorted(entry["sources"]),
            )
            for key, entry in sorted(variable_index.items())
        ]
        components = [
            TemplateComponentSchemaItem(
                id=variable.key,
                component=variable.component_type,
                binding=variable.key,
                label=variable.label,
                value_type=variable.value_type,
                required=variable.required,
            )
            for variable in variables
        ]

        return TemplateSchemaResponse(
            variable_count=len(variables),
            variables=variables,
            components=components,
        )

    def _ensure_docx(self, *, file_name: str, content: bytes) -> None:
        """Validate that the uploaded file is a DOCX payload."""
        if not file_name.lower().endswith(".docx"):
            raise ValidationError("Only .docx templates are supported.")
        if not zipfile.is_zipfile(BytesIO(content)):
            raise ValidationError("The uploaded file is not a valid DOCX archive.")

    def _iter_docx_text_parts(self, content: bytes) -> list[tuple[str, str]]:
        """Return text extracted from DOCX XML parts that may contain placeholders."""
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                parts: list[tuple[str, str]] = []
                for name in sorted(archive.namelist()):
                    if not name.startswith("word/") or not name.endswith(".xml"):
                        continue
                    with archive.open(name) as xml_file:
                        xml_bytes = xml_file.read()
                    parts.append((name, self._extract_text(xml_bytes)))
                return parts
        except zipfile.BadZipFile as error:
            raise ValidationError("The uploaded file could not be parsed as DOCX.") from error

    def _extract_text(self, xml_bytes: bytes) -> str:
        """Convert an XML part into plain text while preserving placeholder continuity."""
        try:
            root = ElementTree.fromstring(xml_bytes)
        except ElementTree.ParseError:
            return ""
        return "".join(root.itertext())

    def _label_from_key(self, key: str) -> str:
        """Convert a variable key into a UI-friendly label."""
        return key.replace(".", " ").replace("_", " ").replace("-", " ").title()

    def _infer_component_type(self, key: str) -> str:
        """Infer the best default UI component for a variable."""
        lowered = key.lower()
        if lowered.startswith(("image_", "photo_", "logo_", "signature_")):
            return "image"
        if lowered.startswith(("table_", "rows_", "items_", "list_")):
            return "table"
        return "text"

    def _infer_value_type(self, key: str) -> str:
        """Infer the expected value type for a variable."""
        component_type = self._infer_component_type(key)
        if component_type == "image":
            return "image"
        if component_type == "table":
            return "array"
        return "string"
