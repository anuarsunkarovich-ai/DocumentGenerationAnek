"""Storage service interface."""

from abc import ABC, abstractmethod

from app.services.storage.models import StorageObject


class StorageService(ABC):
    """Abstract boundary for object storage providers."""

    @abstractmethod
    async def ensure_bucket(self) -> None:
        """Ensure the configured bucket exists."""

    @abstractmethod
    async def upload_template(
        self,
        *,
        organization_code: str,
        template_code: str,
        version: str,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        """Store a template source file."""

    @abstractmethod
    async def upload_generated_artifact(
        self,
        *,
        organization_code: str,
        job_id: str,
        artifact_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        """Store a generated artifact file."""

    @abstractmethod
    async def upload_preview(
        self,
        *,
        organization_code: str,
        job_id: str,
        preview_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        """Store a preview artifact file."""

    @abstractmethod
    async def upload_cached_artifact(
        self,
        *,
        organization_code: str,
        cache_key: str,
        artifact_name: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        """Store a cached artifact file."""

    @abstractmethod
    async def download_bytes(self, key: str) -> bytes:
        """Download an object into memory."""

    @abstractmethod
    async def stat_object(self, key: str) -> StorageObject:
        """Return metadata for a stored object."""

    @abstractmethod
    async def get_download_url(self, key: str) -> str:
        """Return a temporary download URL for an object."""

    @abstractmethod
    async def delete_object(self, key: str) -> None:
        """Remove an object from storage."""
