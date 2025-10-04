"""Integration tests for authentication routes and token validation."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

import app.api.dependencies.auth as auth_dependency_module
import app.services.auth_service as auth_service_module
from app.core.auth import hash_password
from app.core.config import get_settings
from app.models.enums import UserRole

pytestmark = pytest.mark.integration


def install_auth_test_doubles(monkeypatch, state: dict[str, Any]) -> None:
    """Patch auth repositories and transactions with in-memory doubles."""

    @asynccontextmanager
    async def fake_transaction_session():
        yield object()

    class FakeUserRepository:
        def __init__(self, session: object) -> None:
            _ = session
            self._state = state

        async def get_by_email(self, email: str):
            return self._state["users_by_email"].get(email)

        async def get_by_id(self, user_id):
            return self._state["users_by_id"].get(user_id)

        async def mark_logged_in(self, user):
            user.last_login_at = datetime.now(timezone.utc)
            return user

    class FakeAuthSessionRepository:
        def __init__(self, session: object) -> None:
            _ = session
            self._state = state

        async def create(self, auth_session):
            auth_session_state = SimpleNamespace(
                id=getattr(auth_session, "id", uuid4()),
                user_id=auth_session.user_id,
                refresh_token_hash=auth_session.refresh_token_hash,
                expires_at=auth_session.expires_at,
                revoked_at=getattr(auth_session, "revoked_at", None),
                last_used_at=getattr(auth_session, "last_used_at", None),
            )
            self._state["sessions"][auth_session.refresh_token_hash] = auth_session_state
            return auth_session_state

        async def get_by_refresh_token_hash(self, refresh_token_hash: str):
            auth_session = self._state["sessions"].get(refresh_token_hash)
            if auth_session is not None:
                auth_session.user = self._state["users_by_id"][auth_session.user_id]
            return auth_session

        async def revoke(self, auth_session):
            auth_session.revoked_at = datetime.now(timezone.utc)
            return auth_session

        async def touch(self, auth_session):
            auth_session.last_used_at = datetime.now(timezone.utc)
            return auth_session

    monkeypatch.setattr(auth_service_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(auth_service_module, "UserRepository", FakeUserRepository)
    monkeypatch.setattr(auth_service_module, "AuthSessionRepository", FakeAuthSessionRepository)
    monkeypatch.setattr(auth_dependency_module, "get_transaction_session", fake_transaction_session)
    monkeypatch.setattr(auth_dependency_module, "UserRepository", FakeUserRepository)


def build_auth_state() -> dict[str, Any]:
    """Build an in-memory user and session state for auth tests."""
    organization_id = uuid4()
    organization = SimpleNamespace(
        id=organization_id,
        name="Math Department",
        code="math-dept",
        is_active=True,
    )
    user = SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        email="anek@example.com",
        full_name="Anek",
        role=UserRole.ADMIN,
        is_active=True,
        password_hash=hash_password("correct-password"),
        last_login_at=None,
        organization=organization,
    )
    return {
        "organization": organization,
        "user": user,
        "users_by_email": {user.email: user},
        "users_by_id": {user.id: user},
        "sessions": {},
    }


def build_expired_access_token(*, user_id, organization_id, role: str) -> str:
    """Build an expired JWT for negative token-validation tests."""
    settings = get_settings()
    issued_at = datetime.now(timezone.utc) - timedelta(minutes=30)
    expires_at = issued_at + timedelta(minutes=1)
    return jwt.encode(
        {
            "sub": str(user_id),
            "organization_id": str(organization_id),
            "role": role,
            "token_type": "access",
            "iss": settings.auth.issuer,
            "aud": settings.auth.audience,
            "iat": issued_at,
            "exp": expires_at,
        },
        settings.auth.jwt_secret_key,
        algorithm=settings.auth.jwt_algorithm,
    )


def test_login_rejects_bad_password(client: TestClient, monkeypatch) -> None:
    """Ensure invalid credentials return 401."""
    state = build_auth_state()
    install_auth_test_doubles(monkeypatch, state)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "anek@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_me_rejects_missing_token(client: TestClient) -> None:
    """Ensure protected auth routes reject missing bearer tokens."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were not provided."


def test_me_rejects_expired_token(client: TestClient, monkeypatch) -> None:
    """Ensure expired access tokens are rejected."""
    state = build_auth_state()
    install_auth_test_doubles(monkeypatch, state)
    expired_token = build_expired_access_token(
        user_id=state["user"].id,
        organization_id=state["organization"].id,
        role=state["user"].role.value,
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Access token has expired."


def test_login_and_me_return_authenticated_user(client: TestClient, monkeypatch) -> None:
    """Ensure valid login returns tokens and /me resolves the authenticated user."""
    state = build_auth_state()
    install_auth_test_doubles(monkeypatch, state)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "ANEK@example.com", "password": "correct-password"},
    )

    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "anek@example.com"
    assert len(state["sessions"]) == 1

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["id"] == str(state["user"].id)
    assert me_response.json()["organization"]["code"] == "math-dept"


def test_refresh_and_logout_revoke_sessions(client: TestClient, monkeypatch) -> None:
    """Ensure refresh rotates tokens and logout revokes the current refresh session."""
    state = build_auth_state()
    install_auth_test_doubles(monkeypatch, state)

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "anek@example.com", "password": "correct-password"},
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    original_refresh_token = login_payload["refresh_token"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )

    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert refresh_payload["refresh_token"] != original_refresh_token

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_payload["refresh_token"]},
        headers={"Authorization": f"Bearer {refresh_payload['access_token']}"},
    )

    assert logout_response.status_code == 204

    revoked_refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_payload["refresh_token"]},
    )

    assert revoked_refresh_response.status_code == 401
    assert revoked_refresh_response.json()["detail"] == "Refresh token is invalid or expired."
