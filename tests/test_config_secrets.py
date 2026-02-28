"""Tests for file-backed secret loading and production validation."""

from pathlib import Path

import pytest

from app.core.config import (
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    ObservabilitySettings,
    RedisSettings,
    Settings,
    StorageSettings,
)


def test_settings_load_secret_values_from_files(tmp_path: Path) -> None:
    """Secret-bearing settings should resolve mounted file contents."""
    database_password = tmp_path / "db-password"
    storage_access_key = tmp_path / "storage-access"
    storage_secret_key = tmp_path / "storage-secret"
    redis_password = tmp_path / "redis-password"
    jwt_secret = tmp_path / "jwt-secret"
    sentry_dsn = tmp_path / "sentry-dsn"

    database_password.write_text("db-secret\n", encoding="utf-8")
    storage_access_key.write_text("storage-access\n", encoding="utf-8")
    storage_secret_key.write_text("storage-secret\n", encoding="utf-8")
    redis_password.write_text("redis-secret\n", encoding="utf-8")
    jwt_secret.write_text("jwt-secret\n", encoding="utf-8")
    sentry_dsn.write_text("https://sentry.example/1\n", encoding="utf-8")

    settings = Settings(
        app=AppSettings(environment="development"),
        database=DatabaseSettings(password_file=str(database_password)),
        storage=StorageSettings(
            access_key_file=str(storage_access_key),
            secret_key_file=str(storage_secret_key),
        ),
        redis=RedisSettings(password_file=str(redis_password)),
        auth=AuthSettings(jwt_secret_key_file=str(jwt_secret)),
        observability=ObservabilitySettings(sentry_dsn_file=str(sentry_dsn)),
    )

    assert settings.database.password == "db-secret"
    assert settings.storage.access_key == "storage-access"
    assert settings.storage.secret_key == "storage-secret"
    assert settings.redis.password == "redis-secret"
    assert settings.auth.jwt_secret_key == "jwt-secret"
    assert settings.observability.sentry_dsn == "https://sentry.example/1"


def test_production_settings_require_file_backed_secrets() -> None:
    """Production mode should reject deployments that rely on plaintext secrets."""
    with pytest.raises(ValueError, match="DATABASE__PASSWORD_FILE"):
        Settings(app=AppSettings(environment="production"))
