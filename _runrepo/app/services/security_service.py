"""Security-focused validation helpers for uploads and client input."""

import re
from base64 import b64decode
from binascii import Error as BinasciiError
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import is_zipfile

from app.core.config import get_settings
from app.core.exceptions import ValidationError

SAFE_FILE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
DATA_URL_PATTERN = re.compile(
    r"^data:image/(png|jpeg|jpg|webp);base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE,
)
ALLOWED_TEMPLATE_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
    "application/zip",
}


class SecurityService:
    """Centralize defensive validation for uploads and client-supplied references."""

    def __init__(self) -> None:
        """Load size limits and storage prefixes from settings."""
        self._settings = get_settings()

    def sanitize_file_name(self, file_name: str, *, default_stem: str) -> str:
        """Return a safe base file name with path segments removed."""
        base_name = Path(file_name or "").name.strip()
        if not base_name:
            raise ValidationError("File name is required.")

        suffix = Path(base_name).suffix.lower()
        stem = Path(base_name).stem
        safe_stem = SAFE_FILE_NAME_PATTERN.sub("-", stem).strip("-.")
        if not safe_stem:
            safe_stem = default_stem
        return f"{safe_stem}{suffix}"

    def validate_template_upload(
        self,
        *,
        file_name: str,
        content_type: str | None,
        content: bytes,
    ) -> str:
        """Validate a DOCX upload and return its sanitized file name."""
        safe_file_name = self.sanitize_file_name(file_name, default_stem="template")
        if not safe_file_name.lower().endswith(".docx"):
            raise ValidationError("Only .docx templates are supported.")
        if not content:
            raise ValidationError("Template file is empty.")
        if len(content) > self._settings.generation.max_upload_size_bytes:
            raise ValidationError("Template file exceeds the configured upload size limit.")
        if content_type and content_type not in ALLOWED_TEMPLATE_CONTENT_TYPES:
            raise ValidationError("Unsupported template content type.")
        if not is_zipfile(BytesIO(content)):
            raise ValidationError("Template file must be a valid DOCX package.")
        return safe_file_name

    def validate_template_storage_key(
        self,
        *,
        storage_key: str,
        organization_code: str,
    ) -> str:
        """Validate that a registered storage key points to the caller's template area."""
        normalized = storage_key.strip().replace("\\", "/").strip("/")
        if not normalized:
            raise ValidationError("Storage key is required.")

        parts = PurePosixPath(normalized).parts
        if any(part in {"", ".", ".."} for part in parts):
            raise ValidationError("Storage key contains unsafe path segments.")

        expected_prefix = (
            self._settings.storage.templates_prefix,
            organization_code,
        )
        if parts[:2] != expected_prefix:
            raise ValidationError("Storage key does not belong to the organization template area.")
        return normalized

    def validate_image_data_url(self, image_source: str) -> str:
        """Validate an inline image data URL and return the normalized source."""
        if not isinstance(image_source, str):
            raise ValidationError("Image source must be a string data URL.")

        normalized = image_source.strip()
        match = DATA_URL_PATTERN.fullmatch(normalized)
        if match is None:
            raise ValidationError("Only base64 PNG, JPEG, and WEBP data URLs are supported.")

        encoded = re.sub(r"\s+", "", match.group("data"))
        try:
            decoded = b64decode(encoded, validate=True)
        except BinasciiError as error:
            raise ValidationError("Image data URL is not valid base64.") from error

        if len(decoded) > self._settings.generation.max_image_size_bytes:
            raise ValidationError("Image exceeds the configured size limit.")
        return normalized
