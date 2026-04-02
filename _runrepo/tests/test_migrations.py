"""Tests for Alembic migration integrity."""

import re
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT_DIR = Path(__file__).resolve().parents[1]
VERSIONS_DIR = ROOT_DIR / "migrations" / "versions"
pytestmark = pytest.mark.migration

DESTRUCTIVE_PATTERNS = (
    re.compile(r"\bop\.drop_table\s*\("),
    re.compile(r"\bop\.drop_column\s*\("),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TYPE\b", re.IGNORECASE),
)
DESTRUCTIVE_REVIEW_MARKER = "destructive_change_reviewed: true"


def build_alembic_config(*, output_buffer: StringIO | None = None) -> Config:
    """Return an Alembic config pointing at the workspace migration files."""
    config = Config(str(ROOT_DIR / "alembic.ini"), output_buffer=output_buffer)
    config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
    config.set_main_option("prepend_sys_path", str(ROOT_DIR))
    return config


def test_alembic_has_single_head_revision() -> None:
    """Ensure the migration history stays linear until branching is intentional."""
    script_directory = ScriptDirectory.from_config(build_alembic_config())

    assert script_directory.get_heads() == ["c3d4e5f6a7b8"]


def test_alembic_offline_upgrade_renders_sql() -> None:
    """Ensure the current migration set can render an offline upgrade script."""
    buffer = StringIO()
    command.upgrade(build_alembic_config(output_buffer=buffer), "head", sql=True)

    rendered = buffer.getvalue()

    assert "CREATE TABLE organizations" in rendered
    assert "CREATE TABLE document_jobs" in rendered
    assert "CREATE TABLE auth_sessions" in rendered
    assert "CREATE TABLE organization_memberships" in rendered
    assert "CREATE TABLE api_keys" in rendered
    assert "CREATE TABLE api_key_usage_logs" in rendered
    assert "CREATE TABLE plan_definitions" in rendered
    assert "CREATE TABLE organization_plans" in rendered
    assert "CREATE TABLE organization_usage_meters" in rendered
    assert "CREATE TABLE billing_invoices" in rendered
    assert rendered.count("CREATE TYPE user_role") == 1
    assert rendered.count("CREATE TYPE template_status") == 1
    assert rendered.count("CREATE TYPE document_job_status") == 1
    assert rendered.count("CREATE TYPE artifact_kind") == 1
    assert rendered.count("CREATE TYPE audit_action") == 1


def test_alembic_revision_chain_is_contiguous() -> None:
    """Ensure every revision points at a real parent and keeps one linear history."""
    script_directory = ScriptDirectory.from_config(build_alembic_config())
    revisions = list(script_directory.walk_revisions(base="base", head="heads"))
    revision_map = {revision.revision: revision for revision in revisions}

    assert revisions, "Expected at least one Alembic revision."

    for revision in revisions:
        if revision.down_revision is None:
            continue

        parents = (
            revision.down_revision
            if isinstance(revision.down_revision, tuple)
            else (revision.down_revision,)
        )
        for parent in parents:
            assert parent in revision_map, f"Revision {revision.revision} points to missing {parent}."


def test_migrations_require_review_marker_for_destructive_changes() -> None:
    """Force explicit review notes before destructive migration operations land."""
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        if DESTRUCTIVE_REVIEW_MARKER in source:
            continue

        upgrade_source = source.partition("def upgrade")[2].partition("def downgrade")[0]

        assert not any(pattern.search(upgrade_source) for pattern in DESTRUCTIVE_PATTERNS), (
            f"{path.name} contains a destructive schema operation without the "
            f"'{DESTRUCTIVE_REVIEW_MARKER}' marker."
        )
