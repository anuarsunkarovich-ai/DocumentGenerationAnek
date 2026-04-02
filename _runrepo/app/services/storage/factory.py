"""Factories for storage services."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.storage.base import StorageService
from app.services.storage.minio import MinioStorageService


@lru_cache
def get_storage_service() -> StorageService:
    """Return the configured storage service implementation."""
    settings = get_settings()
    return MinioStorageService(settings.storage)
