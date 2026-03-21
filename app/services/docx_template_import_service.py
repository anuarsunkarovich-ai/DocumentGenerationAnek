"""Analyze regular DOCX files and build confirmed import bindings."""

from __future__ import annotations

import hashlib
import re
import zipfile
from collections import Counter
from io import BytesIO

from app.core.exceptions import ValidationError
from app.dtos.template import (
    TemplateComponentSchemaItem,
    TemplateImportAnalysisResponse,
    TemplateImportBindingConfirmationItem,
    TemplateImportBindingResponse,
    TemplateImportFieldCandidate,
    TemplateImportInspectionResponse,
    TemplateImportManualSelectionItem,
    TemplateImportParagraphItem,
    TemplateSchemaResponse,
    TemplateVariableSchemaItem,
)
from app.services.docx_template_import_utils import (
    ParagraphTarget,
    iter_document_paragraph_targets,
    load_docx_document,
)

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Za-z][A-Za-z0-9_.-]{0,119})\s*}}")
BRACKET_PATTERN = re.compile(
    r"(?P<raw>\[(?P<label_square>[^\[\]\n]{2,120})\]|<<(?P<label_angle>[^<>\n]{2,120})>>|\u00ab(?P<label_quote>[^\u00ab\u00bb\n]{2,120})\u00bb)"
)
BLANK_PATTERN = re.compile(r"(?P<raw>_{4,}|\.{4,})")
CITATION_LIKE_PATTERN = re.compile(r"^\d+(?:\s*,\s*\d+)*$")
GENERIC_LABELS = {"date", "name", "address", "phone", "email", "signature"}
CYRILLIC_TRANSLIT_MAP = {
    "а": "a",
    "ә": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "ғ": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "қ": "q",
    "л": "l",
    "м": "m",
    "н": "n",
    "ң": "ng",
    "о": "o",
    "ө": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ұ": "u",
    "ү": "u",
    "ф": "f",
    "х": "h",
    "һ": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ы": "y",
    "і": "i",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ь": "",
    "ъ": "",
}


class DocxTemplateImportService:
    """Infer fillable fields from regular DOCX documents."""

    def inspect(self, file_name: str, content: bytes) -> TemplateImportInspectionResponse:
        """Return all addressable text regions for assisted templateization."""
        self._ensure_docx(file_name=file_name, content=content)
        checksum = hashlib.sha256(content).hexdigest()
        document = load_docx_document(content)
        paragraphs = [
            TemplateImportParagraphItem(
                path=target.path,
                source_type=target.source_type,
                text=target.paragraph.text,
                char_count=len(target.paragraph.text),
                table_header_label=target.table_header_label,
            )
            for target in iter_document_paragraph_targets(document)
            if target.paragraph.text.strip()
        ]
        return TemplateImportInspectionResponse(
            inspection_checksum=checksum,
            paragraph_count=len(paragraphs),
            paragraphs=paragraphs,
        )

    def analyze(self, file_name: str, content: bytes) -> TemplateImportAnalysisResponse:
        """Analyze a DOCX file and return likely field candidates."""
        self._ensure_docx(file_name=file_name, content=content)
        checksum = hashlib.sha256(content).hexdigest()
        document = load_docx_document(content)

        candidates: list[TemplateImportFieldCandidate] = []
        seen_locations: set[tuple[str, int, int]] = set()
        for target in iter_document_paragraph_targets(document):
            candidates.extend(self._extract_candidates(target, seen_locations))

        candidates.sort(key=lambda item: (item.paragraph_path, item.fragment_start, item.id))
        schema = self.build_schema_from_candidates(candidates)
        return TemplateImportAnalysisResponse(
            analysis_checksum=checksum,
            candidate_count=len(candidates),
            candidates=candidates,
            schema_payload=schema,
        )

    def confirm_bindings(
        self,
        *,
        analysis: TemplateImportAnalysisResponse,
        confirmations: list[TemplateImportBindingConfirmationItem],
    ) -> tuple[list[TemplateImportBindingResponse], TemplateSchemaResponse]:
        """Apply user-confirmed binding keys to an analysis result."""
        candidate_by_id = {candidate.id: candidate for candidate in analysis.candidates}
        bindings: list[TemplateImportBindingResponse] = []
        for confirmation in confirmations:
            candidate = candidate_by_id.get(confirmation.candidate_id)
            if candidate is None:
                raise ValidationError(
                    f"Binding confirmation references unknown candidate '{confirmation.candidate_id}'."
                )
            bindings.append(
                TemplateImportBindingResponse(
                    id=f"binding-{candidate.id}",
                    candidate_id=candidate.id,
                    binding_key=confirmation.binding_key,
                    label=confirmation.label or candidate.label,
                    raw_fragment=candidate.raw_fragment,
                    paragraph_path=candidate.paragraph_path,
                    source_type=candidate.source_type,
                    detection_kind=candidate.detection_kind,
                    confidence=candidate.confidence,
                    preview_text=candidate.preview_text,
                    value_type=confirmation.value_type or candidate.value_type,
                    component_type=confirmation.component_type or candidate.component_type,
                    required=confirmation.required,
                    sample_value=confirmation.sample_value,
                    fragment_start=candidate.fragment_start,
                    fragment_end=candidate.fragment_end,
                )
            )

        schema = self.build_schema_from_bindings(bindings)
        return bindings, schema

    def templateize_from_selections(
        self,
        *,
        inspection: TemplateImportInspectionResponse,
        selections: list[TemplateImportManualSelectionItem],
    ) -> tuple[list[TemplateImportBindingResponse], TemplateSchemaResponse]:
        """Build confirmed bindings from explicit user-selected text spans."""
        paragraph_by_path = {paragraph.path: paragraph for paragraph in inspection.paragraphs}
        bindings: list[TemplateImportBindingResponse] = []
        for selection in selections:
            paragraph = paragraph_by_path.get(selection.paragraph_path)
            if paragraph is None:
                raise ValidationError(
                    f"Manual selection references unknown paragraph '{selection.paragraph_path}'."
                )
            if selection.fragment_end > paragraph.char_count:
                raise ValidationError(
                    f"Manual selection exceeds paragraph length for '{selection.paragraph_path}'."
                )
            raw_fragment = paragraph.text[selection.fragment_start : selection.fragment_end]
            if not raw_fragment:
                raise ValidationError(
                    f"Manual selection produced an empty fragment for '{selection.paragraph_path}'."
                )
            label = selection.label or self._label_from_key(selection.binding_key)
            binding_id = hashlib.sha1(
                (
                    f"{selection.paragraph_path}:{selection.fragment_start}:"
                    f"{selection.fragment_end}:{selection.binding_key}"
                ).encode("utf-8")
            ).hexdigest()[:12]
            bindings.append(
                TemplateImportBindingResponse(
                    id=f"binding-{binding_id}",
                    candidate_id=f"manual-{binding_id}",
                    binding_key=selection.binding_key,
                    label=label,
                    raw_fragment=raw_fragment,
                    paragraph_path=selection.paragraph_path,
                    source_type=paragraph.source_type,
                    detection_kind="manual_selection",
                    confidence=1.0,
                    preview_text=paragraph.text,
                    value_type=selection.value_type
                    or self._infer_value_type(selection.binding_key, label),
                    component_type=selection.component_type
                    or self._infer_component_type(selection.binding_key, label),
                    required=selection.required,
                    sample_value=selection.sample_value,
                    fragment_start=selection.fragment_start,
                    fragment_end=selection.fragment_end,
                )
            )

        schema = self.build_schema_from_bindings(bindings)
        return bindings, schema

    def build_schema_from_candidates(
        self,
        candidates: list[TemplateImportFieldCandidate],
    ) -> TemplateSchemaResponse:
        """Build a suggested template schema from detected import candidates."""
        grouped = Counter(candidate.suggested_binding for candidate in candidates)
        deduped = self._first_candidate_per_binding(candidates)
        variables = [
            TemplateVariableSchemaItem(
                key=candidate.suggested_binding,
                label=candidate.label,
                placeholder=candidate.raw_fragment,
                value_type=candidate.value_type,
                component_type=candidate.component_type,
                required=candidate.required,
                occurrences=grouped[candidate.suggested_binding],
                sources=[candidate.paragraph_path],
            )
            for candidate in deduped.values()
        ]
        components = [
            TemplateComponentSchemaItem(
                id=f"component-{variable.key}",
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
            variables=sorted(variables, key=lambda item: item.key),
            components=sorted(components, key=lambda item: item.binding),
        )

    def build_schema_from_bindings(
        self,
        bindings: list[TemplateImportBindingResponse],
    ) -> TemplateSchemaResponse:
        """Build the confirmed template schema from stored import bindings."""
        grouped = Counter(binding.binding_key for binding in bindings)
        deduped = self._first_binding_per_key(bindings)
        variables = [
            TemplateVariableSchemaItem(
                key=binding.binding_key,
                label=binding.label,
                placeholder=binding.raw_fragment,
                value_type=binding.value_type,
                component_type=binding.component_type,
                required=binding.required,
                sample_value=binding.sample_value,
                occurrences=grouped[binding.binding_key],
                sources=[binding.paragraph_path],
            )
            for binding in deduped.values()
        ]
        components = [
            TemplateComponentSchemaItem(
                id=binding.id,
                component=binding.component_type,
                binding=binding.binding_key,
                label=binding.label,
                value_type=binding.value_type,
                required=binding.required,
            )
            for binding in deduped.values()
        ]
        return TemplateSchemaResponse(
            variable_count=len(variables),
            variables=sorted(variables, key=lambda item: item.key),
            components=sorted(components, key=lambda item: item.binding),
        )

    def _extract_candidates(
        self,
        target: ParagraphTarget,
        seen_locations: set[tuple[str, int, int]],
    ) -> list[TemplateImportFieldCandidate]:
        text = target.paragraph.text
        if not text or not text.strip():
            return []

        candidates: list[TemplateImportFieldCandidate] = []
        for match in PLACEHOLDER_PATTERN.finditer(text):
            key = match.group(1)
            candidates.append(
                self._build_candidate(
                    target=target,
                    raw_fragment=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    label=self._label_from_key(key),
                    binding_key=key,
                    detection_kind="existing_placeholder",
                    confidence=0.99,
                )
            )
            seen_locations.add((target.path, match.start(), match.end()))

        for match in BRACKET_PATTERN.finditer(text):
            location = (target.path, match.start("raw"), match.end("raw"))
            if location in seen_locations:
                continue
            label = self._clean_label(
                match.group("label_square")
                or match.group("label_angle")
                or match.group("label_quote")
                or ""
            )
            if not label:
                continue
            if CITATION_LIKE_PATTERN.fullmatch(label):
                continue
            if not self._has_bracket_field_context(
                text=text,
                start=match.start("raw"),
                end=match.end("raw"),
                source_type=target.source_type,
            ):
                continue
            candidates.append(
                self._build_candidate(
                    target=target,
                    raw_fragment=match.group("raw"),
                    start=match.start("raw"),
                    end=match.end("raw"),
                    label=label,
                    binding_key=self._binding_key_from_label(label),
                    detection_kind="bracketed_label",
                    confidence=0.87,
                )
            )
            seen_locations.add(location)

        for match in BLANK_PATTERN.finditer(text):
            location = (target.path, match.start("raw"), match.end("raw"))
            if location in seen_locations:
                continue
            label = self._derive_blank_label(target=target, text=text, start=match.start("raw"))
            if not label:
                continue
            candidates.append(
                self._build_candidate(
                    target=target,
                    raw_fragment=match.group("raw"),
                    start=match.start("raw"),
                    end=match.end("raw"),
                    label=label,
                    binding_key=self._binding_key_from_label(label),
                    detection_kind="blank_span",
                    confidence=0.72 if target.table_header_label else 0.64,
                )
            )
            seen_locations.add(location)

        return candidates

    def _build_candidate(
        self,
        *,
        target: ParagraphTarget,
        raw_fragment: str,
        start: int,
        end: int,
        label: str,
        binding_key: str,
        detection_kind: str,
        confidence: float,
    ) -> TemplateImportFieldCandidate:
        candidate_id = hashlib.sha1(
            f"{target.path}:{start}:{end}:{raw_fragment}".encode("utf-8")
        ).hexdigest()[:12]
        return TemplateImportFieldCandidate(
            id=candidate_id,
            label=label,
            suggested_binding=binding_key,
            raw_fragment=raw_fragment,
            paragraph_path=target.path,
            source_type=target.source_type,
            detection_kind=detection_kind,
            confidence=confidence,
            preview_text=target.paragraph.text.strip(),
            value_type=self._infer_value_type(binding_key, label),
            component_type=self._infer_component_type(binding_key, label),
            required=True,
            fragment_start=start,
            fragment_end=end,
        )

    def _derive_blank_label(self, *, target: ParagraphTarget, text: str, start: int) -> str | None:
        if target.table_header_label:
            return self._clean_label(target.table_header_label)

        prefix = text[:start].strip()
        if not prefix:
            return None
        prefix = prefix.rstrip(":.- ")
        parts = [part.strip() for part in re.split(r"[\n;,.]", prefix) if part.strip()]
        if not parts:
            return None
        label = self._clean_label(parts[-1])
        if not label:
            return None
        if label.lower() in GENERIC_LABELS and len(parts) > 1:
            label = self._clean_label(f"{parts[-2]} {label}")
        return label or None

    def _clean_label(self, label: str) -> str:
        normalized = re.sub(r"\s+", " ", label.strip(" []<>\u00ab\u00bb\t\r\n"))
        normalized = re.sub(r"^[\-\d\).:]+\s*", "", normalized)
        return normalized.strip()

    def _binding_key_from_label(self, label: str) -> str:
        transliterated = "".join(
            CYRILLIC_TRANSLIT_MAP.get(character, character) for character in label.lower()
        )
        normalized = re.sub(r"[^A-Za-z0-9]+", "_", transliterated).strip("_")
        if not normalized:
            normalized = f"field_{hashlib.sha1(label.encode('utf-8')).hexdigest()[:8]}"
        if normalized[0].isdigit():
            normalized = f"field_{normalized}"
        return normalized[:120]

    def _has_bracket_field_context(
        self,
        *,
        text: str,
        start: int,
        end: int,
        source_type: str,
    ) -> bool:
        prefix = text[:start].rstrip()
        suffix = text[end:].lstrip()
        if not prefix and not suffix:
            return True
        if prefix.endswith((":", "-", "=", "(", "\n")):
            return True
        if source_type in {"header", "footer"} and len(prefix) <= 2:
            return True
        return False

    def _label_from_key(self, key: str) -> str:
        return key.replace(".", " ").replace("_", " ").replace("-", " ").title()

    def _infer_component_type(self, binding_key: str, label: str) -> str:
        lowered = f"{binding_key} {label}".lower()
        if any(token in lowered for token in ("image", "photo", "logo", "signature")):
            return "image"
        if any(token in lowered for token in ("table", "rows", "items", "list")):
            return "table"
        return "text"

    def _infer_value_type(self, binding_key: str, label: str) -> str:
        lowered = f"{binding_key} {label}".lower()
        component_type = self._infer_component_type(binding_key, label)
        if component_type == "image":
            return "image"
        if component_type == "table":
            return "array"
        if "date" in lowered:
            return "date"
        if any(token in lowered for token in ("amount", "price", "sum", "total")):
            return "number"
        return "string"

    def _ensure_docx(self, *, file_name: str, content: bytes) -> None:
        if not file_name.lower().endswith(".docx"):
            raise ValidationError("Only .docx templates are supported.")
        if not zipfile.is_zipfile(BytesIO(content)):
            raise ValidationError("The uploaded file is not a valid DOCX archive.")

    def _first_candidate_per_binding(
        self,
        candidates: list[TemplateImportFieldCandidate],
    ) -> dict[str, TemplateImportFieldCandidate]:
        deduped: dict[str, TemplateImportFieldCandidate] = {}
        for candidate in candidates:
            deduped.setdefault(candidate.suggested_binding, candidate)
        return deduped

    def _first_binding_per_key(
        self,
        bindings: list[TemplateImportBindingResponse],
    ) -> dict[str, TemplateImportBindingResponse]:
        deduped: dict[str, TemplateImportBindingResponse] = {}
        for binding in bindings:
            deduped.setdefault(binding.binding_key, binding)
        return deduped
