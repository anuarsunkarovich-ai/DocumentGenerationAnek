"""Helpers for stable storage key construction."""

from pathlib import PurePosixPath

from app.core.config import StorageSettings
from app.core.exceptions import ApplicationError


class InvalidStorageKeySegmentError(ApplicationError):
    """Raised when a storage key segment is empty or unsafe."""


class StorageKeyBuilder:
    """Build stable object keys for templates and artifacts."""

    def __init__(self, settings: StorageSettings) -> None:
        """Capture storage prefixes from settings."""
        self._settings = settings

    def template_key(
        self,
        *,
        organization_code: str,
        template_code: str,
        version: str,
        file_name: str,
    ) -> str:
        """Build a template source key."""
        return str(
            PurePosixPath(
                self._settings.templates_prefix,
                self._clean_segment(organization_code),
                self._clean_segment(template_code),
                self._clean_segment(version),
                self._clean_file_name(file_name),
            )
        )

    def artifact_key(
        self,
        *,
        organization_code: str,
        job_id: str,
        artifact_name: str,
    ) -> str:
        """Build a generated artifact key."""
        return str(
            PurePosixPath(
                self._settings.artifacts_prefix,
                self._clean_segment(organization_code),
                self._clean_segment(job_id),
                self._clean_file_name(artifact_name),
            )
        )

    def preview_key(
        self,
        *,
        organization_code: str,
        job_id: str,
        preview_name: str,
    ) -> str:
        """Build a preview artifact key."""
        return str(
            PurePosixPath(
                self._settings.previews_prefix,
                self._clean_segment(organization_code),
                self._clean_segment(job_id),
                self._clean_file_name(preview_name),
            )
        )

    def cache_key(
        self,
        *,
        organization_code: str,
        cache_key: str,
        artifact_name: str,
    ) -> str:
        """Build a cached artifact key."""
        return str(
            PurePosixPath(
                self._settings.cache_prefix,
                self._clean_segment(organization_code),
                self._clean_segment(cache_key),
                self._clean_file_name(artifact_name),
            )
        )

    def _clean_segment(self, value: str) -> str:
        """Normalize a path segment into a safe object-key component."""
        cleaned = value.strip().replace("\\", "/").strip("/")
        if not cleaned or cleaned in {".", ".."} or "/" in cleaned:
            raise InvalidStorageKeySegmentError(f"Unsafe storage key segment: '{value}'.")
        return cleaned

    def _clean_file_name(self, value: str) -> str:
        """Normalize a file name while preserving the base name only."""
        cleaned = value.strip().replace("\\", "/").split("/")[-1]
        if not cleaned or cleaned in {".", ".."}:
            raise InvalidStorageKeySegmentError(f"Unsafe file name: '{value}'.")
        return cleaned
