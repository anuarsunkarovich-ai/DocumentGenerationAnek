"""automatic billing invoices and scheduled plan changes"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.add_column(
        "plan_definitions",
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "plan_definitions",
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="USD"),
    )
    op.add_column(
        "organization_plans",
        sa.Column("pending_plan_definition_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        op.f("ix_organization_plans_pending_plan_definition_id"),
        "organization_plans",
        ["pending_plan_definition_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_organization_plans_pending_plan_definition_id_plan_definitions"),
        "organization_plans",
        "plan_definitions",
        ["pending_plan_definition_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "billing_invoices",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("organization_plan_id", sa.Uuid(), nullable=False),
        sa.Column("plan_definition_id", sa.Uuid(), nullable=False),
        sa.Column("plan_code", sa.String(length=50), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("generation_count", sa.Integer(), nullable=False),
        sa.Column("template_count", sa.Integer(), nullable=False),
        sa.Column("user_count", sa.Integer(), nullable=False),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "premium_feature_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "line_items",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_billing_invoices_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_plan_id"],
            ["organization_plans.id"],
            name=op.f("fk_billing_invoices_organization_plan_id_organization_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_definition_id"],
            ["plan_definitions.id"],
            name=op.f("fk_billing_invoices_plan_definition_id_plan_definitions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_billing_invoices")),
        sa.UniqueConstraint(
            "organization_id",
            "period_start",
            "period_end",
            name="uq_billing_invoices_org_period",
        ),
    )
    op.create_index(
        op.f("ix_billing_invoices_organization_id"),
        "billing_invoices",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_invoices_organization_plan_id"),
        "billing_invoices",
        ["organization_plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_billing_invoices_plan_definition_id"),
        "billing_invoices",
        ["plan_definition_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE plan_definitions
        SET monthly_price_cents = CASE code
            WHEN 'starter' THEN 0
            WHEN 'growth' THEN 19900
            WHEN 'enterprise' THEN 99900
            ELSE monthly_price_cents
        END,
        currency_code = 'USD'
        """
    )

    op.alter_column("plan_definitions", "monthly_price_cents", server_default=None)
    op.alter_column("plan_definitions", "currency_code", server_default=None)


def downgrade() -> None:
    """Revert the migration."""
    op.drop_index(op.f("ix_billing_invoices_plan_definition_id"), table_name="billing_invoices")
    op.drop_index(op.f("ix_billing_invoices_organization_plan_id"), table_name="billing_invoices")
    op.drop_index(op.f("ix_billing_invoices_organization_id"), table_name="billing_invoices")
    op.drop_table("billing_invoices")

    op.drop_constraint(
        op.f("fk_organization_plans_pending_plan_definition_id_plan_definitions"),
        "organization_plans",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_organization_plans_pending_plan_definition_id"),
        table_name="organization_plans",
    )
    op.drop_column("organization_plans", "pending_plan_definition_id")

    op.drop_column("plan_definitions", "currency_code")
    op.drop_column("plan_definitions", "monthly_price_cents")
