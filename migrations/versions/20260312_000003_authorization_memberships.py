"""organization memberships and authorization support"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "20260312_000003"
down_revision: str | None = "20260330_000002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

user_role_enum = postgresql.ENUM(
    "ADMIN",
    "MANAGER",
    "OPERATOR",
    "VIEWER",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "organization_memberships",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_memberships_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_organization_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_memberships")),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_organization_memberships_user_org",
        ),
    )
    op.create_index(
        op.f("ix_organization_memberships_organization_id"),
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_memberships_user_id"),
        "organization_memberships",
        ["user_id"],
        unique=False,
    )

    if context.is_offline_mode():
        return

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, organization_id, role, is_active
            FROM users
            """
        )
    ).mappings()
    membership_table = sa.table(
        "organization_memberships",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("role", user_role_enum),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_default", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    op.bulk_insert(
        membership_table,
        [
            {
                "id": uuid4(),
                "user_id": row["id"],
                "organization_id": row["organization_id"],
                "role": row["role"],
                "is_active": row["is_active"],
                "is_default": True,
                "created_at": now,
                "updated_at": now,
            }
            for row in rows
        ],
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_index(
        op.f("ix_organization_memberships_user_id"),
        table_name="organization_memberships",
    )
    op.drop_index(
        op.f("ix_organization_memberships_organization_id"),
        table_name="organization_memberships",
    )
    op.drop_table("organization_memberships")
