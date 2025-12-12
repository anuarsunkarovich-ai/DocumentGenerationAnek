"""initial schema"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b91d8c0a4f2e"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


template_status_enum = postgresql.ENUM(
    "DRAFT",
    "ACTIVE",
    "ARCHIVED",
    name="template_status",
    create_type=False,
)
user_role_enum = postgresql.ENUM(
    "ADMIN",
    "MANAGER",
    "OPERATOR",
    "VIEWER",
    name="user_role",
    create_type=False,
)
document_job_status_enum = postgresql.ENUM(
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="document_job_status",
    create_type=False,
)
artifact_kind_enum = postgresql.ENUM(
    "DOCX",
    "PDF",
    "PREVIEW",
    "SOURCE",
    name="artifact_kind",
    create_type=False,
)
audit_action_enum = postgresql.ENUM(
    "TEMPLATE_CREATED",
    "TEMPLATE_VERSION_CREATED",
    "DOCUMENT_JOB_CREATED",
    "DOCUMENT_JOB_COMPLETED",
    "DOCUMENT_JOB_FAILED",
    "ARTIFACT_CREATED",
    name="audit_action",
    create_type=False,
)


def upgrade() -> None:
    """Apply the migration."""
    bind = op.get_bind()
    template_status_enum.create(bind, checkfirst=True)
    user_role_enum.create(bind, checkfirst=True)
    document_job_status_enum.create(bind, checkfirst=True)
    artifact_kind_enum.create(bind, checkfirst=True)
    audit_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_index(op.f("ix_organizations_code"), "organizations", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_users_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
    )
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)

    op.create_table(
        "templates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", template_status_enum, nullable=False),
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
            name=op.f("fk_templates_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_templates")),
        sa.UniqueConstraint("organization_id", "code", name="uq_templates_org_code"),
    )
    op.create_index(
        op.f("ix_templates_organization_id"), "templates", ["organization_id"], unique=False
    )

    op.create_table(
        "template_versions",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("variable_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("component_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
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
            ["created_by_user_id"],
            ["users.id"],
            name=op.f("fk_template_versions_created_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_template_versions_template_id_templates"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_versions")),
        sa.UniqueConstraint("template_id", "version", name="uq_template_versions_template_version"),
    )
    op.create_index(
        op.f("ix_template_versions_created_by_user_id"),
        "template_versions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_template_versions_template_id"), "template_versions", ["template_id"], unique=False
    )

    op.create_table(
        "document_jobs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("template_version_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", document_job_status_enum, nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cache_key", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            name=op.f("fk_document_jobs_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name=op.f("fk_document_jobs_requested_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("fk_document_jobs_template_id_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_version_id"],
            ["template_versions.id"],
            name=op.f("fk_document_jobs_template_version_id_template_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_jobs")),
    )
    op.create_index(
        op.f("ix_document_jobs_cache_key"), "document_jobs", ["cache_key"], unique=False
    )
    op.create_index(
        op.f("ix_document_jobs_organization_id"),
        "document_jobs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_jobs_requested_by_user_id"),
        "document_jobs",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_jobs_template_id"), "document_jobs", ["template_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_jobs_template_version_id"),
        "document_jobs",
        ["template_version_id"],
        unique=False,
    )

    op.create_table(
        "audit_logs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
            name=op.f("fk_audit_logs_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    op.create_table(
        "document_artifacts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("document_job_id", sa.Uuid(), nullable=True),
        sa.Column("template_version_id", sa.Uuid(), nullable=False),
        sa.Column("kind", artifact_kind_enum, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("is_cached", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            ["document_job_id"],
            ["document_jobs.id"],
            name=op.f("fk_document_artifacts_document_job_id_document_jobs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_document_artifacts_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_version_id"],
            ["template_versions.id"],
            name=op.f("fk_document_artifacts_template_version_id_template_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_artifacts")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_document_artifacts_storage_key")),
    )
    op.create_index(
        op.f("ix_document_artifacts_document_job_id"),
        "document_artifacts",
        ["document_job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_artifacts_organization_id"),
        "document_artifacts",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_artifacts_template_version_id"),
        "document_artifacts",
        ["template_version_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_index(
        op.f("ix_document_artifacts_template_version_id"), table_name="document_artifacts"
    )
    op.drop_index(op.f("ix_document_artifacts_organization_id"), table_name="document_artifacts")
    op.drop_index(op.f("ix_document_artifacts_document_job_id"), table_name="document_artifacts")
    op.drop_table("document_artifacts")

    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_organization_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_document_jobs_template_version_id"), table_name="document_jobs")
    op.drop_index(op.f("ix_document_jobs_template_id"), table_name="document_jobs")
    op.drop_index(op.f("ix_document_jobs_requested_by_user_id"), table_name="document_jobs")
    op.drop_index(op.f("ix_document_jobs_organization_id"), table_name="document_jobs")
    op.drop_index(op.f("ix_document_jobs_cache_key"), table_name="document_jobs")
    op.drop_table("document_jobs")

    op.drop_index(op.f("ix_template_versions_template_id"), table_name="template_versions")
    op.drop_index(op.f("ix_template_versions_created_by_user_id"), table_name="template_versions")
    op.drop_table("template_versions")

    op.drop_index(op.f("ix_templates_organization_id"), table_name="templates")
    op.drop_table("templates")

    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_organizations_code"), table_name="organizations")
    op.drop_table("organizations")

    bind = op.get_bind()
    audit_action_enum.drop(bind, checkfirst=True)
    artifact_kind_enum.drop(bind, checkfirst=True)
    document_job_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
    template_status_enum.drop(bind, checkfirst=True)
