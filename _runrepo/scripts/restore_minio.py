"""Restore a MinIO bucket mirror into the configured object storage bucket."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from app.core.config import get_settings
from scripts.backup_minio import build_mc_alias_command


def build_mc_restore_command(*, input_dir: Path, alias_name: str = "backup-target") -> list[str]:
    """Build the mc mirror command for restoring one bucket mirror."""
    settings = get_settings()
    return [
        "mc",
        "mirror",
        "--overwrite",
        str(input_dir),
        f"{alias_name}/{settings.storage.bucket}",
    ]


def main() -> None:
    """Run an object-storage restore from a local directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Directory containing the bucket mirror to restore.")
    args = parser.parse_args()
    subprocess.run(build_mc_alias_command(alias_name="backup-target"), check=True)
    subprocess.run(build_mc_restore_command(input_dir=args.input), check=True)


if __name__ == "__main__":
    main()
