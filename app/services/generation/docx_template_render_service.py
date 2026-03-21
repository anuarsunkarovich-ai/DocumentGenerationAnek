"""Render imported DOCX templates while preserving the original layout."""

from __future__ import annotations

import json
from hashlib import sha256
from io import BytesIO
from typing import Any

from app.core.exceptions import ValidationError
from app.services.docx_template_import_utils import (
    load_docx_document,
    resolve_paragraph_target,
)
from app.services.generation.models import ResolvedTemplateContext


class DocxTemplateRenderService:
    """Apply confirmed import bindings directly onto the stored DOCX source."""

    def prepare_payload(
        self,
        *,
        context: ResolvedTemplateContext,
        data: dict[str, Any],
    ) -> tuple[dict[str, Any], str]:
        """Normalize imported-template values and build a stable cache key."""
        normalized: dict[str, Any] = {}
        bindings = context.import_bindings
        if not bindings:
            raise ValidationError("Imported template bindings have not been confirmed yet.")

        for binding in bindings:
            key = str(binding["binding_key"])
            value = data.get(key)
            if value is None:
                if bool(binding.get("required", True)):
                    raise ValidationError(f"Required binding '{key}' is missing.")
                normalized[key] = None
                continue
            if isinstance(value, (dict, list)):
                raise ValidationError(
                    f"Imported template binding '{key}' must resolve to a scalar text value."
                )
            normalized[key] = str(value)

        cache_payload = json.dumps(
            {
                "render_strategy": context.render_strategy,
                "template_version_id": str(context.template_version_id),
                "data": normalized,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        return normalized, sha256(cache_payload.encode("utf-8")).hexdigest()

    def render(
        self,
        *,
        content: bytes,
        context: ResolvedTemplateContext,
        data: dict[str, Any],
    ) -> bytes:
        """Return a filled DOCX while retaining the uploaded document structure."""
        document = load_docx_document(content)
        bindings_by_path: dict[str, list[dict[str, Any]]] = {}
        for binding in context.import_bindings:
            value = data.get(str(binding["binding_key"]))
            if value is None:
                continue
            bindings_by_path.setdefault(str(binding["paragraph_path"]), []).append(
                {
                    "start": int(binding["fragment_start"]),
                    "end": int(binding["fragment_end"]),
                    "raw_fragment": str(binding["raw_fragment"]),
                    "value": str(value),
                    "binding_key": str(binding["binding_key"]),
                }
            )

        for path, replacements in bindings_by_path.items():
            paragraph = resolve_paragraph_target(document, path)
            for replacement in sorted(replacements, key=lambda item: item["start"], reverse=True):
                self._replace_span_in_runs(
                    paragraph.runs,
                    start=replacement["start"],
                    end=replacement["end"],
                    expected_text=replacement["raw_fragment"],
                    replacement_text=replacement["value"],
                    binding_key=replacement["binding_key"],
                )

        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _replace_span_in_runs(
        self,
        runs,
        *,
        start: int,
        end: int,
        expected_text: str,
        replacement_text: str,
        binding_key: str,
    ) -> None:
        full_text = "".join(run.text for run in runs)
        if start < 0 or end > len(full_text) or start >= end:
            raise ValidationError(f"Imported binding '{binding_key}' points at an invalid span.")
        if full_text[start:end] != expected_text:
            raise ValidationError(
                f"Imported binding '{binding_key}' no longer matches the stored DOCX source."
            )

        inserted = False
        cursor = 0
        for run in runs:
            text = run.text
            run_start = cursor
            run_end = cursor + len(text)
            cursor = run_end

            overlaps = not (run_end <= start or run_start >= end)
            if not overlaps:
                continue

            pieces: list[str] = []
            if run_start < start:
                pieces.append(text[: start - run_start])
            if not inserted:
                pieces.append(replacement_text)
                inserted = True
            if run_end > end:
                pieces.append(text[end - run_start :])
            run.text = "".join(pieces)

        if not inserted:
            raise ValidationError(f"Imported binding '{binding_key}' could not be applied.")
