"""Artifact authenticity verification helpers."""

import re
from hashlib import sha256
from uuid import UUID

from app.core.config import get_settings
from app.core.database import get_transaction_session
from app.core.exceptions import ValidationError
from app.dtos.document import (
    DocumentVerificationArtifactResponse,
    DocumentVerificationResponse,
)
from app.repositories.document_artifact_repository import DocumentArtifactRepository

SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class DocumentVerificationService:
    """Verify whether a file or hash matches a generated artifact."""

    async def verify(
        self,
        *,
        organization_id: UUID,
        authenticity_hash: str | None = None,
        file_bytes: bytes | None = None,
    ) -> DocumentVerificationResponse:
        """Return whether the supplied file or hash matches a stored artifact."""
        resolved_hash = self._resolve_hash(authenticity_hash=authenticity_hash, file_bytes=file_bytes)

        async with get_transaction_session() as session:
            repository = DocumentArtifactRepository(session)
            matches = await repository.list_by_checksum(
                organization_id=organization_id,
                checksum=resolved_hash,
            )

        representative = matches[0] if matches else None
        return DocumentVerificationResponse(
            organization_id=organization_id,
            matched=representative is not None,
            provided_hash=resolved_hash,
            matched_artifact_count=len(matches),
            artifact=(
                DocumentVerificationArtifactResponse(
                    artifact_id=representative.id,
                    task_id=representative.document_job_id,
                    kind=representative.kind.value,
                    file_name=representative.file_name,
                    content_type=representative.content_type,
                    size_bytes=representative.size_bytes,
                    issued_at=representative.created_at,
                    authenticity_hash=representative.checksum or resolved_hash,
                    verification_code=self.build_verification_code(
                        artifact_id=representative.id,
                        authenticity_hash=representative.checksum or resolved_hash,
                    ),
                )
                if representative is not None
                else None
            ),
        )

    def _resolve_hash(
        self,
        *,
        authenticity_hash: str | None,
        file_bytes: bytes | None,
    ) -> str:
        """Validate one verification input and return the canonical SHA-256 hash."""
        if file_bytes is not None and authenticity_hash is not None:
            raise ValidationError("Provide either a file or an authenticity hash, not both.")
        if file_bytes is None and authenticity_hash is None:
            raise ValidationError("Provide a file or an authenticity hash to verify.")

        if file_bytes is not None:
            settings = get_settings()
            if len(file_bytes) > settings.generation.max_upload_size_bytes:
                raise ValidationError("Verification file exceeds the configured upload size limit.")
            return sha256(file_bytes).hexdigest()

        normalized_hash = (authenticity_hash or "").strip().lower()
        if not SHA256_HEX_PATTERN.fullmatch(normalized_hash):
            raise ValidationError("Authenticity hash must be a 64-character SHA-256 hex string.")
        return normalized_hash

    @staticmethod
    def build_verification_code(*, artifact_id: UUID, authenticity_hash: str) -> str:
        """Build a short deterministic verification code for UI display."""
        return f"VER-{artifact_id.hex[:8].upper()}-{authenticity_hash[:12].upper()}"
