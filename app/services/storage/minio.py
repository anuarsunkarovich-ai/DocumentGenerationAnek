"""MinIO-backed object storage implementation."""

import asyncio
from datetime import datetime, timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import StorageSettings
from app.core.exceptions import ApplicationError
from app.services.storage.base import StorageService
from app.services.storage.key_builder import StorageKeyBuilder
from app.services.storage.models import StorageObject


class StorageError(ApplicationError):
    """Raised when object storage operations fail."""


class MinioStorageService(StorageService):
    """Store templates and artifacts in a MinIO bucket."""

    def __init__(self, settings: StorageSettings) -> None:
        """Initialize the MinIO client and key builder."""
        self._settings = settings
        self._bucket = settings.bucket
        self._client = Minio(
            endpoint=settings.endpoint,
            access_key=settings.access_key,
            secret_key=settings.secret_key,
            secure=settings.secure,
            region=settings.region,
        )
        self._key_builder = StorageKeyBuilder(settings)

    async def ensure_bucket(self) -> None:
        """Ensure the configured bucket exists."""
        try:
            exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
            if not exists:
                if not self._settings.auto_create_bucket:
                    raise StorageError(f"Bucket '{self._bucket}' does not exist.")
                await asyncio.to_thread(self._client.make_bucket, self._bucket)
        except S3Error as error:
            raise StorageError("Failed to verify storage bucket.") from error

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
        key = self._key_builder.template_key(
            organization_code=organization_code,
            template_code=template_code,
            version=version,
            file_name=file_name,
        )
        return await self._put_object(
            key=key,
            content=content,
            content_type=content_type,
        )

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
        key = self._key_builder.artifact_key(
            organization_code=organization_code,
            job_id=job_id,
            artifact_name=artifact_name,
        )
        return await self._put_object(
            key=key,
            content=content,
            content_type=content_type,
        )

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
        key = self._key_builder.preview_key(
            organization_code=organization_code,
            job_id=job_id,
            preview_name=preview_name,
        )
        return await self._put_object(
            key=key,
            content=content,
            content_type=content_type,
        )

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
        key = self._key_builder.cache_key(
            organization_code=organization_code,
            cache_key=cache_key,
            artifact_name=artifact_name,
        )
        return await self._put_object(
            key=key,
            content=content,
            content_type=content_type,
        )

    async def download_bytes(self, key: str) -> bytes:
        """Download an object into memory."""
        try:
            response = await asyncio.to_thread(self._client.get_object, self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as error:
            raise StorageError(f"Failed to download object '{key}'.") from error

    async def stat_object(self, key: str) -> StorageObject:
        """Return metadata for a stored object."""
        try:
            result = await asyncio.to_thread(self._client.stat_object, self._bucket, key)
        except S3Error as error:
            raise StorageError(f"Failed to stat object '{key}'.") from error

        return StorageObject(
            bucket=self._bucket,
            key=key,
            content_type=result.content_type or "application/octet-stream",
            size_bytes=result.size or 0,
            etag=result.etag,
            version_id=result.version_id,
            last_modified=result.last_modified,
        )

    async def get_download_url(self, key: str) -> str:
        """Return a temporary download URL for an object."""
        try:
            return await asyncio.to_thread(
                self._client.presigned_get_object,
                self._bucket,
                key,
                timedelta(seconds=self._settings.presigned_url_expiry_seconds),
            )
        except S3Error as error:
            raise StorageError(f"Failed to build download URL for '{key}'.") from error

    async def delete_object(self, key: str) -> None:
        """Remove an object from storage."""
        try:
            await asyncio.to_thread(self._client.remove_object, self._bucket, key)
        except S3Error as error:
            raise StorageError(f"Failed to delete object '{key}'.") from error

    async def _put_object(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
    ) -> StorageObject:
        """Upload an object and return its metadata."""
        await self.ensure_bucket()
        data = BytesIO(content)

        try:
            result = await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                key,
                data,
                len(content),
                content_type=content_type,
            )
        except S3Error as error:
            raise StorageError(f"Failed to upload object '{key}'.") from error

        return StorageObject(
            bucket=self._bucket,
            key=key,
            content_type=content_type,
            size_bytes=len(content),
            etag=result.etag,
            version_id=result.version_id,
            url=self._build_object_url(key),
            last_modified=datetime.utcnow(),
        )

    def _build_object_url(self, key: str) -> str:
        """Return a direct bucket URL for internal diagnostics."""
        return f"{self._settings.public_base_url}/{self._bucket}/{key}"
