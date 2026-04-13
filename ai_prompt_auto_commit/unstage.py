"""pre-commit hook: remove .prompts/ files from the git index."""

from __future__ import annotations

import subprocess
import sys

from .common import PROMPTS_DIRECTORY


def unstage() -> int:
    """Remove any .prompts/ files from the git index before committing."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--", f"{PROMPTS_DIRECTORY}/"],
        capture_output=True,
        text=True,
    )
    staged = result.stdout.strip()
    if not staged:
        return 0
    for filepath in staged.splitlines():
        subprocess.run(["git", "restore", "--staged", "--", filepath], check=True)
    return 0


def main() -> None:
    sys.exit(unstage())
