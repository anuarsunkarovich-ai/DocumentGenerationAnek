"""Service-level models for storage operations."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class StorageObject:
    """Metadata returned after a file is stored or inspected."""

    bucket: str
    key: str
    content_type: str
    size_bytes: int
    etag: str | None = None
    version_id: str | None = None
    url: str | None = None
    last_modified: datetime | None = None
