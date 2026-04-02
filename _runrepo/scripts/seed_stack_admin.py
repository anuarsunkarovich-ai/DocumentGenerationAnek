"""Seed an admin user and default organization for live-stack smoke tests."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


async def seed_stack_admin() -> dict[str, str]:
    """Create or update one stable admin identity for smoke tests."""
    from app.core.auth import hash_password
    from app.core.database import get_transaction_session
    from app.models.enums import UserRole
    from app.models.organization import Organization
    from app.models.organization_membership import OrganizationMembership
    from app.models.user import User

    organization_code = os.getenv("STACK_ADMIN_ORG_CODE", "smoke-org")
    organization_name = os.getenv("STACK_ADMIN_ORG_NAME", "Smoke Test Org")
    email = os.getenv("STACK_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("STACK_ADMIN_PASSWORD", "Passw0rd!")
    full_name = os.getenv("STACK_ADMIN_FULL_NAME", "Smoke Test Admin")

    async with get_transaction_session() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.code == organization_code)
        )
        if organization is None:
            organization = Organization(
                name=organization_name,
                code=organization_code,
                is_active=True,
            )
            session.add(organization)
            await session.flush()
        else:
            organization.name = organization_name
            organization.is_active = True

        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                organization_id=organization.id,
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(user)
            await session.flush()
        else:
            user.organization_id = organization.id
            user.full_name = full_name
            user.password_hash = hash_password(password)
            user.role = UserRole.ADMIN
            user.is_active = True

        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization.id,
            )
        )
        if membership is None:
            membership = OrganizationMembership(
                user_id=user.id,
                organization_id=organization.id,
                role=UserRole.ADMIN,
                is_active=True,
                is_default=True,
            )
            session.add(membership)
        else:
            membership.role = UserRole.ADMIN
            membership.is_active = True
            membership.is_default = True

        await session.flush()
        return {
            "organization_id": str(organization.id),
            "organization_code": organization.code,
            "email": user.email,
            "password": password,
            "user_id": str(user.id),
        }


def main() -> None:
    """Seed the admin user and write the result as JSON."""
    print(json.dumps(asyncio.run(seed_stack_admin())))


if __name__ == "__main__":
    main()
