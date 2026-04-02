"""Service-backed integration tests that use real Postgres and MinIO."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from io import BytesIO
from uuid import uuid4
from zipfile import ZipFile

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.auth import hash_password
from app.core.config import ROOT_DIR, get_settings
from app.core.database import get_transaction_session, reset_database_manager
from app.main import create_application
from app.models.enums import UserRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.services.storage.factory import get_storage_service

pytestmark = [pytest.mark.integration, pytest.mark.service_integration]


def build_docx_fixture(*document_text: str) -> bytes:
    """Build a minimal DOCX fixture for real upload and extraction flows."""
    body = "".join(f"<w:t>{text}</w:t>" for text in document_text)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def build_alembic_config() -> Config:
    """Build an Alembic config that points at the workspace migrations."""
    config = Config(str(ROOT_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
    config.set_main_option("prepend_sys_path", str(ROOT_DIR))
    return config


async def reset_database_schema() -> None:
    """Drop and recreate the public schema so migrations start from an empty database."""
    engine = create_async_engine(
        get_settings().database.url,
        isolation_level="AUTOCOMMIT",
    )
    async with engine.connect() as connection:
        await connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        await connection.execute(text("GRANT ALL ON SCHEMA public TO public"))
    await engine.dispose()


async def seed_identity(*, email: str, password: str) -> dict[str, str]:
    """Insert one admin user and default membership for live auth flows."""
    async with get_transaction_session() as session:
        organization = Organization(
            name="Service Integration Org",
            code=f"service-org-{uuid4().hex[:8]}",
            is_active=True,
        )
        session.add(organization)
        await session.flush()

        user = User(
            organization_id=organization.id,
            email=email,
            full_name="Service Integration Admin",
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        session.add(
            OrganizationMembership(
                user_id=user.id,
                organization_id=organization.id,
                role=UserRole.ADMIN,
                is_active=True,
                is_default=True,
            )
        )
        await session.flush()
        return {
            "organization_id": str(organization.id),
            "email": user.email,
            "password": password,
        }


@pytest.fixture(scope="module")
def service_environment() -> Generator[dict[str, str], None, None]:
    """Configure the app to use local service containers for integration tests."""
    if os.getenv("RUN_SERVICE_INTEGRATION") != "1":
        pytest.skip("Set RUN_SERVICE_INTEGRATION=1 to run service-backed integration tests.")

    bucket = f"service-integration-{uuid4().hex[:8]}"
    overrides = {
        "APP__ENVIRONMENT": "test",
        "APP__DEBUG": "false",
        "DATABASE__HOST": os.getenv("SERVICE_DATABASE_HOST", "127.0.0.1"),
        "DATABASE__PORT": os.getenv("SERVICE_DATABASE_PORT", "5432"),
        "DATABASE__NAME": os.getenv("SERVICE_DATABASE_NAME", "lean_generator"),
        "DATABASE__USER": os.getenv("SERVICE_DATABASE_USER", "postgres"),
        "DATABASE__PASSWORD": os.getenv("SERVICE_DATABASE_PASSWORD", "postgres"),
        "STORAGE__ENDPOINT": os.getenv("SERVICE_STORAGE_ENDPOINT", "127.0.0.1:9000"),
        "STORAGE__PUBLIC_ENDPOINT": os.getenv("SERVICE_STORAGE_PUBLIC_ENDPOINT", "127.0.0.1:9000"),
        "STORAGE__ACCESS_KEY": os.getenv("SERVICE_STORAGE_ACCESS_KEY", "minioadmin"),
        "STORAGE__SECRET_KEY": os.getenv("SERVICE_STORAGE_SECRET_KEY", "minioadmin"),
        "STORAGE__BUCKET": bucket,
        "STORAGE__SECURE": "false",
        "STORAGE__PUBLIC_SECURE": "false",
        "REDIS__HOST": os.getenv("SERVICE_REDIS_HOST", "127.0.0.1"),
        "REDIS__PORT": os.getenv("SERVICE_REDIS_PORT", "6379"),
        "AUTH__JWT_SECRET_KEY": "service-integration-secret-key-123456",
    }

    previous = {key: os.environ.get(key) for key in overrides}
    for key, value in overrides.items():
        os.environ[key] = value

    get_settings.cache_clear()
    get_storage_service.cache_clear()
    reset_database_manager()

    try:
        yield overrides
    finally:
        get_storage_service.cache_clear()
        get_settings.cache_clear()
        reset_database_manager()
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def test_migrations_round_trip_on_empty_database(service_environment: dict[str, str]) -> None:
    """Ensure a fresh database can upgrade, downgrade, and upgrade again."""
    _ = service_environment
    asyncio.run(reset_database_schema())

    config = build_alembic_config()
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


def test_real_startup_upload_and_schema_flow(service_environment: dict[str, str]) -> None:
    """Exercise startup bucket creation and real template persistence against live services."""
    _ = service_environment
    asyncio.run(reset_database_schema())
    command.upgrade(build_alembic_config(), "head")

    email = f"service-admin-{uuid4().hex[:8]}@example.com"
    password = "Passw0rd!"
    reset_database_manager()
    identity = asyncio.run(seed_identity(email=email, password=password))
    reset_database_manager()

    settings = get_settings()
    minio_client = Minio(
        endpoint=settings.storage.endpoint,
        access_key=settings.storage.access_key,
        secret_key=settings.storage.secret_key,
        secure=settings.storage.secure,
    )
    assert minio_client.bucket_exists(settings.storage.bucket) is False

    with TestClient(create_application()) as client:
        assert minio_client.bucket_exists(settings.storage.bucket) is True

        health_response = client.get("/health/ready")
        assert health_response.status_code == 200
        assert health_response.json()["checks"]["database"]["status"] == "ok"
        assert health_response.json()["checks"]["storage"]["status"] == "ok"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": identity["email"], "password": identity["password"]},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        schema_response = client.post(
            "/api/v1/templates/extract-schema",
            headers=headers,
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}", "{{signer_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert schema_response.status_code == 200
        assert schema_response.json()["variable_count"] == 2

        upload_response = client.post(
            "/api/v1/templates/upload",
            headers=headers,
            data={
                "organization_id": identity["organization_id"],
                "name": "Service Certificate",
                "code": "service-certificate",
                "version": "1.0.0",
                "description": "Service-backed upload",
                "publish": "true",
            },
            files={
                "file": (
                    "certificate.docx",
                    build_docx_fixture("{{student_name}}", "{{signer_name}}"),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert upload_response.status_code == 201
        upload_payload = upload_response.json()
        template_id = upload_payload["template"]["id"]
        template_version_id = upload_payload["version"]["id"]
        storage_key = upload_payload["version"]["storage_key"]
        assert storage_key.startswith("templates/")
        assert minio_client.bucket_exists(settings.storage.bucket) is True
        stored_object = minio_client.stat_object(settings.storage.bucket, storage_key)
        assert (stored_object.size or 0) > 0

        template_response = client.get(
            f"/api/v1/templates/{template_id}",
            headers=headers,
            params={"organization_id": identity["organization_id"]},
        )
        assert template_response.status_code == 200
        assert template_response.json()["current_version"]["id"] == template_version_id

        extracted_response = client.post(
            f"/api/v1/templates/{template_id}/extract-schema",
            headers=headers,
            params={"organization_id": identity["organization_id"]},
        )
        assert extracted_response.status_code == 200
        extracted_payload = extracted_response.json()
        assert extracted_payload["template_version_id"] == template_version_id
        assert extracted_payload["schema"]["variable_count"] == 2
