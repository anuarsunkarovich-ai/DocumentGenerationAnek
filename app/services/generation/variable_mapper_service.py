"""Map constructor bindings into normalized renderable blocks."""

from typing import Any

from app.core.exceptions import ValidationError
from app.dtos.constructor import (
    BaseBlock,
    ConstructorBindingReference,
    DocumentConstructor,
    HeaderBlock,
    ImageBlock,
    PageBreakBlock,
    SignatureBlock,
    SpacerBlock,
    TableBlock,
    TextBlock,
)
from app.services.generation.models import ResolvedBlock, ResolvedDocument, ResolvedTemplateContext
from app.services.security_service import SecurityService


class VariableMapperService:
    """Resolve constructor bindings against the provided data payload."""

    def __init__(self, security_service: SecurityService | None = None) -> None:
        """Store security helpers for validating resolved assets."""
        self._security_service = security_service or SecurityService()

    def map_document(
        self,
        *,
        context: ResolvedTemplateContext,
        constructor: DocumentConstructor,
        data: dict[str, Any],
    ) -> tuple[ResolvedDocument, dict[str, Any], str]:
        """Return the normalized renderable document, payload, and cache key."""
        normalized_payload = self._normalize_payload(data)
        resolved_blocks = [
            self._resolve_block(block=block, payload=normalized_payload)
            for block in constructor.blocks
        ]
        cache_key = self._build_cache_key(
            template_version_id=str(context.template_version_id),
            constructor=constructor.model_dump(mode="json"),
            payload=normalized_payload,
        )
        return (
            ResolvedDocument(
                constructor=constructor,
                formatting=constructor.formatting,
                blocks=resolved_blocks,
                data=normalized_payload,
            ),
            normalized_payload,
            cache_key,
        )

    def _resolve_block(self, *, block: BaseBlock, payload: dict[str, Any]) -> ResolvedBlock:
        """Resolve one constructor block into a renderable structure."""
        if isinstance(block, TextBlock):
            return ResolvedBlock(
                id=block.id,
                type=block.type,
                content={
                    "text": block.text or self._resolve_binding(block.binding, payload),
                    "style": block.style.model_dump(mode="json"),
                    "multiline": block.multiline,
                },
            )
        if isinstance(block, HeaderBlock):
            return ResolvedBlock(
                id=block.id,
                type=block.type,
                content={
                    "text": block.text or self._resolve_binding(block.binding, payload),
                    "level": block.level,
                    "numbering": block.numbering,
                    "style": block.style.model_dump(mode="json"),
                },
            )
        if isinstance(block, TableBlock):
            rows = block.rows or self._resolve_binding(block.rows_binding, payload)
            if not isinstance(rows, list):
                raise ValidationError(f"Table block '{block.id}' requires a list of rows.")
            return ResolvedBlock(
                id=block.id,
                type=block.type,
                content={
                    "columns": [column.model_dump(mode="json") for column in block.columns],
                    "rows": rows,
                    "caption": block.caption,
                    "header_bold": block.header_bold,
                    "compact": block.compact,
                },
            )
        if isinstance(block, ImageBlock):
            image_value = self._resolve_binding(block.binding, payload)
            if not isinstance(image_value, str):
                raise ValidationError(f"Image block '{block.id}' requires a string data URL.")
            return ResolvedBlock(
                id=block.id,
                type=block.type,
                content={
                    "image": self._security_service.validate_image_data_url(image_value),
                    "width_mm": block.width_mm,
                    "height_mm": block.height_mm,
                    "keep_aspect_ratio": block.keep_aspect_ratio,
                    "caption": block.caption,
                    "alignment": block.alignment,
                },
            )
        if isinstance(block, SignatureBlock):
            return ResolvedBlock(
                id=block.id,
                type=block.type,
                content={
                    "signer_name": self._resolve_binding(block.signer_name, payload),
                    "signer_role": self._resolve_optional_binding(block.signer_role, payload),
                    "date": self._resolve_optional_binding(block.date_binding, payload),
                    "line_label": block.line_label,
                    "include_date": block.include_date,
                    "include_stamp_area": block.include_stamp_area,
                },
            )
        if isinstance(block, PageBreakBlock):
            return ResolvedBlock(id=block.id, type=block.type, content={"reason": block.reason})
        if isinstance(block, SpacerBlock):
            return ResolvedBlock(
                id=block.id, type=block.type, content={"height_mm": block.height_mm}
            )
        raise ValidationError(f"Unsupported document block '{block.id}'.")

    def _resolve_binding(
        self,
        binding: ConstructorBindingReference | None,
        payload: dict[str, Any],
    ) -> Any:
        """Resolve a required binding against the payload."""
        if binding is None:
            raise ValidationError("A required binding was not provided.")
        value = payload.get(binding.key, binding.fallback)
        if value is None and binding.required:
            raise ValidationError(f"Required binding '{binding.key}' is missing.")
        return value

    def _resolve_optional_binding(
        self,
        binding: ConstructorBindingReference | None,
        payload: dict[str, Any],
    ) -> Any:
        """Resolve an optional binding against the payload."""
        if binding is None:
            return None
        return payload.get(binding.key, binding.fallback)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Normalize incoming data into a deterministic structure."""
        return dict(sorted(payload.items(), key=lambda item: item[0]))

    def _build_cache_key(
        self,
        *,
        template_version_id: str,
        constructor: dict[str, Any],
        payload: dict[str, Any],
    ) -> str:
        """Build a stable hash for caching generated artifacts."""
        import json
        from hashlib import sha256

        body = json.dumps(
            {
                "template_version_id": template_version_id,
                "constructor": constructor,
                "payload": payload,
            },
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
        return sha256(body).hexdigest()
