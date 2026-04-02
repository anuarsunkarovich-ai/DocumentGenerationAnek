"""Create a PostgreSQL backup using the configured application database settings."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from app.core.config import get_settings


def build_pg_dump_command(*, output_path: Path) -> list[str]:
    """Build the pg_dump command for one backup file."""
    settings = get_settings()
    return [
        "pg_dump",
        "--format=custom",
        f"--host={settings.database.host}",
        f"--port={settings.database.port}",
        f"--username={settings.database.user}",
        f"--dbname={settings.database.name}",
        f"--file={output_path}",
    ]


def build_pg_env() -> dict[str, str]:
    """Build environment variables for pg_dump."""
    settings = get_settings()
    env = os.environ.copy()
    env["PGPASSWORD"] = settings.database.password
    return env


def main() -> None:
    """Run pg_dump for the configured database."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path to the backup file to create.")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        build_pg_dump_command(output_path=args.output),
        check=True,
        env=build_pg_env(),
    )


if __name__ == "__main__":
    main()
