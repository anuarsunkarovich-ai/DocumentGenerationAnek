"""Create a MinIO bucket mirror using the configured object storage settings."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from app.core.config import get_settings


def _storage_endpoint() -> str:
    settings = get_settings()
    scheme = "https" if settings.storage.secure else "http"
    return f"{scheme}://{settings.storage.endpoint}"


def build_mc_alias_command(*, alias_name: str = "backup-source") -> list[str]:
    """Build the mc alias command for the configured storage instance."""
    settings = get_settings()
    return [
        "mc",
        "alias",
        "set",
        alias_name,
        _storage_endpoint(),
        settings.storage.access_key,
        settings.storage.secret_key,
    ]


def build_mc_backup_command(*, output_dir: Path, alias_name: str = "backup-source") -> list[str]:
    """Build the mc mirror command for one storage backup."""
    settings = get_settings()
    return [
        "mc",
        "mirror",
        "--overwrite",
        f"{alias_name}/{settings.storage.bucket}",
        str(output_dir),
    ]


def main() -> None:
    """Run an object-storage backup to a local directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Directory where the bucket mirror should be written.")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_mc_alias_command(), check=True)
    subprocess.run(build_mc_backup_command(output_dir=args.output), check=True)


if __name__ == "__main__":
    main()
