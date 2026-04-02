"""Tests for backup and restore helper scripts."""

from pathlib import Path

from app.core.config import get_settings
from scripts.backup_minio import build_mc_alias_command, build_mc_backup_command
from scripts.backup_postgres import build_pg_dump_command
from scripts.restore_minio import build_mc_restore_command
from scripts.restore_postgres import build_pg_restore_command
from scripts.run_restore_drill import build_restore_drill_commands


def test_postgres_backup_and_restore_commands_include_configured_targets(tmp_path: Path) -> None:
    """Postgres backup helpers should point at the configured database and file paths."""
    backup_path = tmp_path / "postgres.dump"
    dump_command = build_pg_dump_command(output_path=backup_path)
    restore_command = build_pg_restore_command(input_path=backup_path)
    settings = get_settings()

    assert dump_command[0] == "pg_dump"
    assert f"--host={settings.database.host}" in dump_command
    assert f"--dbname={settings.database.name}" in dump_command
    assert f"--file={backup_path}" in dump_command
    assert restore_command[0] == "pg_restore"
    assert f"--host={settings.database.host}" in restore_command
    assert str(backup_path) == restore_command[-1]


def test_minio_backup_and_restore_commands_include_bucket_and_path(tmp_path: Path) -> None:
    """Object-storage backup helpers should target the configured bucket."""
    backup_dir = tmp_path / "minio"
    alias_command = build_mc_alias_command()
    backup_command = build_mc_backup_command(output_dir=backup_dir)
    restore_command = build_mc_restore_command(input_dir=backup_dir)
    settings = get_settings()

    assert alias_command[:3] == ["mc", "alias", "set"]
    assert settings.storage.access_key in alias_command
    assert settings.storage.secret_key in alias_command
    assert backup_command[-2] == f"backup-source/{settings.storage.bucket}"
    assert backup_command[-1] == str(backup_dir)
    assert restore_command[-1] == f"backup-target/{settings.storage.bucket}"


def test_restore_drill_commands_chain_database_and_storage_restores(tmp_path: Path) -> None:
    """Restore drills should replay both PostgreSQL and MinIO restore steps."""
    commands = build_restore_drill_commands(backup_dir=tmp_path)

    assert commands == [
        ["python", "scripts/restore_postgres.py", str(tmp_path / "postgres.dump")],
        ["python", "scripts/restore_minio.py", str(tmp_path / "minio")],
    ]
