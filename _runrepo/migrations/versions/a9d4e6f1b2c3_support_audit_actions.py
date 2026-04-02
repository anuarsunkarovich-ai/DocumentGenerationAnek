"""support audit actions"""

from collections.abc import Sequence

from alembic import op

revision: str = "a9d4e6f1b2c3"
down_revision: str | None = "f3c1b2d4e5a6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Apply the migration."""
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'DOCUMENT_JOB_REPLAYED'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'CACHE_INVALIDATED'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'API_KEY_DISABLED'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'USER_DISABLED'")


def downgrade() -> None:
    """Revert the migration."""
    # PostgreSQL enum value removal is intentionally not automated here.
    return None
