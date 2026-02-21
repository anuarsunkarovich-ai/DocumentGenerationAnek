"""billing and plan enforcement"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3c1b2d4e5a6"
down_revision: str | None = "e1a2c4d6f890"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.add_column("template_versions", sa.Column("size_bytes", sa.BigInteger(), nullable=True))

    op.create_table(
        "plan_definitions",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("billable_unit", sa.String(length=50), nullable=False),
        sa.Column("monthly_generation_cap", sa.Integer(), nullable=False),
        sa.Column("max_templates", sa.Integer(), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("storage_quota_bytes", sa.BigInteger(), nullable=False),
        sa.Column("audit_retention_days", sa.Integer(), nullable=False),
        sa.Column("signature_support", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan_definitions")),
    )
    op.create_index(op.f("ix_plan_definitions_code"), "plan_definitions", ["code"], unique=True)

    op.create_table(
        "organization_plans",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("plan_definition_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.Date(), nullable=False),
        sa.Column("current_period_end", sa.Date(), nullable=False),
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
            name=op.f("fk_organization_plans_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_definition_id"],
            ["plan_definitions.id"],
            name=op.f("fk_organization_plans_plan_definition_id_plan_definitions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_plans")),
        sa.UniqueConstraint("organization_id", name=op.f("uq_organization_plans_organization_id")),
    )
    op.create_index(
        op.f("ix_organization_plans_organization_id"),
        "organization_plans",
        ["organization_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_organization_plans_plan_definition_id"),
        "organization_plans",
        ["plan_definition_id"],
        unique=False,
    )

    op.create_table(
        "organization_usage_meters",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("generation_count", sa.Integer(), nullable=False),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False),
        sa.Column("template_count", sa.Integer(), nullable=False),
        sa.Column("user_count", sa.Integer(), nullable=False),
        sa.Column(
            "premium_feature_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            name=op.f("fk_organization_usage_meters_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_usage_meters")),
        sa.UniqueConstraint(
            "organization_id",
            "period_start",
            name="uq_organization_usage_meters_org_period",
        ),
    )
    op.create_index(
        op.f("ix_organization_usage_meters_organization_id"),
        "organization_usage_meters",
        ["organization_id"],
        unique=False,
    )

    plan_definitions = sa.table(
        "plan_definitions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String(length=50)),
        sa.column("name", sa.String(length=255)),
        sa.column("billable_unit", sa.String(length=50)),
        sa.column("monthly_generation_cap", sa.Integer()),
        sa.column("max_templates", sa.Integer()),
        sa.column("max_users", sa.Integer()),
        sa.column("storage_quota_bytes", sa.BigInteger()),
        sa.column("audit_retention_days", sa.Integer()),
        sa.column("signature_support", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        plan_definitions,
        [
            {
                "id": uuid.UUID("8a2e6509-c2a0-428d-9ed1-1f536ed41001"),
                "code": "starter",
                "name": "Starter",
                "billable_unit": "per_organization",
                "monthly_generation_cap": 100,
                "max_templates": 5,
                "max_users": 3,
                "storage_quota_bytes": 104857600,
                "audit_retention_days": 30,
                "signature_support": False,
                "is_active": True,
            },
            {
                "id": uuid.UUID("8a2e6509-c2a0-428d-9ed1-1f536ed41002"),
                "code": "growth",
                "name": "Growth",
                "billable_unit": "per_organization",
                "monthly_generation_cap": 1000,
                "max_templates": 50,
                "max_users": 15,
                "storage_quota_bytes": 5368709120,
                "audit_retention_days": 180,
                "signature_support": True,
                "is_active": True,
            },
            {
                "id": uuid.UUID("8a2e6509-c2a0-428d-9ed1-1f536ed41003"),
                "code": "enterprise",
                "name": "Enterprise",
                "billable_unit": "per_organization",
                "monthly_generation_cap": 10000,
                "max_templates": 500,
                "max_users": 100,
                "storage_quota_bytes": 53687091200,
                "audit_retention_days": 365,
                "signature_support": True,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_index(
        op.f("ix_organization_usage_meters_organization_id"),
        table_name="organization_usage_meters",
    )
    op.drop_table("organization_usage_meters")

    op.drop_index(
        op.f("ix_organization_plans_plan_definition_id"),
        table_name="organization_plans",
    )
    op.drop_index(
        op.f("ix_organization_plans_organization_id"),
        table_name="organization_plans",
    )
    op.drop_table("organization_plans")

    op.drop_index(op.f("ix_plan_definitions_code"), table_name="plan_definitions")
    op.drop_table("plan_definitions")

    op.drop_column("template_versions", "size_bytes")
