"""docx import bindings metadata"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a9d4e6f1b2c3"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.add_column(
        "template_versions",
        sa.Column(
            "render_strategy",
            sa.String(length=32),
            nullable=False,
            server_default="constructor",
        ),
    )
    op.add_column(
        "template_versions",
        sa.Column(
            "import_analysis",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "template_versions",
        sa.Column(
            "import_bindings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    op.alter_column("template_versions", "render_strategy", server_default=None)
    op.alter_column("template_versions", "import_analysis", server_default=None)
    op.alter_column("template_versions", "import_bindings", server_default=None)


def downgrade() -> None:
    """Revert the migration."""
    op.drop_column("template_versions", "import_bindings")
    op.drop_column("template_versions", "import_analysis")
    op.drop_column("template_versions", "render_strategy")
