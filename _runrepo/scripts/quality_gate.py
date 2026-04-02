"""Run the local backend quality gate suite."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
COMMANDS = [
    [sys.executable, "-m", "compileall", "app", "tests", "main.py", "migrations"],
    ["uv", "run", "ruff", "check", "."],
    ["uv", "run", "mypy", "app", "tests"],
    ["uv", "run", "pytest"],
]


def main() -> int:
    """Run each quality gate command and stop on the first failure."""
    for command in COMMANDS:
        print(f"$ {' '.join(command)}")
        result = subprocess.run(command, cwd=ROOT_DIR, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
