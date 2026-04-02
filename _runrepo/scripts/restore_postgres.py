"""Restore a PostgreSQL backup into the configured application database."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from app.core.config import get_settings


def build_pg_restore_command(*, input_path: Path) -> list[str]:
    """Build the pg_restore command for one backup file."""
    settings = get_settings()
    return [
        "pg_restore",
        "--clean",
        "--if-exists",
        "--no-owner",
        "--format=custom",
        f"--host={settings.database.host}",
        f"--port={settings.database.port}",
        f"--username={settings.database.user}",
        f"--dbname={settings.database.name}",
        str(input_path),
    ]


def build_pg_env() -> dict[str, str]:
    """Build environment variables for pg_restore."""
    settings = get_settings()
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.database.password
    return env


def main() -> None:
    """Run pg_restore for the configured database."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to the backup file to restore.")
    args = parser.parse_args()
    subprocess.run(
        build_pg_restore_command(input_path=args.input),
        check=True,
        env=build_pg_env(),
    )


if __name__ == "__main__":
    main()
