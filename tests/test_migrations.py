"""Tests for Alembic migration integrity."""

from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT_DIR = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.migration


def build_alembic_config(*, output_buffer: StringIO | None = None) -> Config:
    """Return an Alembic config pointing at the workspace migration files."""
    config = Config(str(ROOT_DIR / "alembic.ini"), output_buffer=output_buffer)
    config.set_main_option("script_location", str(ROOT_DIR / "migrations"))
    config.set_main_option("prepend_sys_path", str(ROOT_DIR))
    return config


def test_alembic_has_single_head_revision() -> None:
    """Ensure the migration history stays linear until branching is intentional."""
    script_directory = ScriptDirectory.from_config(build_alembic_config())

    assert script_directory.get_heads() == ["d7f1c3a8b5e2"]


def test_alembic_offline_upgrade_renders_sql() -> None:
    """Ensure the current migration set can render an offline upgrade script."""
    buffer = StringIO()
    command.upgrade(build_alembic_config(output_buffer=buffer), "head", sql=True)

    rendered = buffer.getvalue()

    assert "CREATE TABLE organizations" in rendered
    assert "CREATE TABLE document_jobs" in rendered
    assert "CREATE TABLE auth_sessions" in rendered
    assert "CREATE TABLE organization_memberships" in rendered
    assert rendered.count("CREATE TYPE user_role") == 1
    assert rendered.count("CREATE TYPE template_status") == 1
    assert rendered.count("CREATE TYPE document_job_status") == 1
    assert rendered.count("CREATE TYPE artifact_kind") == 1
    assert rendered.count("CREATE TYPE audit_action") == 1
