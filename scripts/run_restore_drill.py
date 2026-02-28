"""Run a simple restore drill for PostgreSQL and MinIO backups."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def build_restore_drill_commands(*, backup_dir: Path) -> list[list[str]]:
    """Build the commands required for one restore drill."""
    postgres_backup = backup_dir / "postgres.dump"
    minio_backup = backup_dir / "minio"
    return [
        ["python", "scripts/restore_postgres.py", str(postgres_backup)],
        ["python", "scripts/restore_minio.py", str(minio_backup)],
    ]


def main() -> None:
    """Execute the restore drill commands sequentially."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup_dir", type=Path, help="Directory containing postgres.dump and minio/ backups.")
    args = parser.parse_args()
    for command in build_restore_drill_commands(backup_dir=args.backup_dir):
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
