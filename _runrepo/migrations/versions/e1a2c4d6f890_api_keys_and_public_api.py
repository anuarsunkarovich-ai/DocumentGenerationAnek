"""api keys and public api support"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1a2c4d6f890"
down_revision: str | None = "d7f1c3a8b5e2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'API_KEY_CREATED'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'API_KEY_ROTATED'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'API_KEY_REVOKED'")

    op.create_table(
        "api_keys",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("hashed_key", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_api_keys_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_keys")),
        sa.UniqueConstraint("hashed_key", name="uq_api_keys_hashed_key"),
    )
    op.create_index(op.f("ix_api_keys_key_prefix"), "api_keys", ["key_prefix"], unique=False)
    op.create_index(
        op.f("ix_api_keys_organization_id"), "api_keys", ["organization_id"], unique=False
    )

    op.create_table(
        "api_key_usage_logs",
        sa.Column("api_key_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("rate_limited", sa.Boolean(), nullable=False),
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
            ["api_key_id"],
            ["api_keys.id"],
            name=op.f("fk_api_key_usage_logs_api_key_id_api_keys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_api_key_usage_logs_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_key_usage_logs")),
    )
    op.create_index(
        op.f("ix_api_key_usage_logs_api_key_id"),
        "api_key_usage_logs",
        ["api_key_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_api_key_usage_logs_organization_id"),
        "api_key_usage_logs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_api_key_usage_logs_request_id"),
        "api_key_usage_logs",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_api_key_usage_logs_correlation_id"),
        "api_key_usage_logs",
        ["correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_index(
        op.f("ix_api_key_usage_logs_correlation_id"),
        table_name="api_key_usage_logs",
    )
    op.drop_index(op.f("ix_api_key_usage_logs_request_id"), table_name="api_key_usage_logs")
    op.drop_index(
        op.f("ix_api_key_usage_logs_organization_id"),
        table_name="api_key_usage_logs",
    )
    op.drop_index(op.f("ix_api_key_usage_logs_api_key_id"), table_name="api_key_usage_logs")
    op.drop_table("api_key_usage_logs")

    op.drop_index(op.f("ix_api_keys_organization_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_prefix"), table_name="api_keys")
    op.drop_table("api_keys")
