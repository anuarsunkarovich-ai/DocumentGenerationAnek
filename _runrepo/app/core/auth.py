"""Password hashing and JWT helpers for internal authentication."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

_PASSWORD_HASHER = PasswordHash.recommended()


@dataclass(frozen=True)
class AccessTokenClaims:
    """Validated claims extracted from an access token."""

    user_id: UUID


def hash_password(password: str) -> str:
    """Hash a plaintext password with the configured password hasher."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored password hash."""
    try:
        return _PASSWORD_HASHER.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(
    *,
    user_id: UUID,
) -> str:
    """Create a signed JWT access token for one user session."""
    settings = get_settings()
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.auth.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "token_type": "access",
        "iss": settings.auth.issuer,
        "aud": settings.auth.audience,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    """Decode and validate a signed JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth.jwt_secret_key,
            algorithms=[settings.auth.jwt_algorithm],
            audience=settings.auth.audience,
            issuer=settings.auth.issuer,
        )
    except jwt.ExpiredSignatureError as error:
        raise AuthenticationError("Access token has expired.") from error
    except jwt.InvalidTokenError as error:
        raise AuthenticationError("Access token is invalid.") from error

    if payload.get("token_type") != "access":
        raise AuthenticationError("Access token is invalid.")

    try:
        return AccessTokenClaims(
            user_id=UUID(str(payload["sub"])),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise AuthenticationError("Access token is invalid.") from error


def generate_refresh_token() -> str:
    """Generate an opaque refresh token."""
    return token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token before persisting it."""
    return sha256(token.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Generate an opaque API key for machine-to-machine auth."""
    return f"lgk_{token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key before persisting it."""
    return sha256(api_key.encode("utf-8")).hexdigest()


def api_key_prefix(api_key: str) -> str:
    """Return a short visible prefix for operator-facing key listings."""
    return api_key[:12]
