"""post-commit hook: archive pending prompts into .prompts/committed/."""

from __future__ import annotations

import subprocess
import sys

from . import common
from .common import COMMITTED_DIRECTORY, get_prompt_files


def archive() -> int:
    """Move pending prompts to .prompts/committed/<name>_<hash>.md."""
    repo_root = common._repo_root()
    committed_dir = repo_root / COMMITTED_DIRECTORY

    pending = get_prompt_files()
    if not pending:
        return 0

    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    committed_dir.mkdir(parents=True, exist_ok=True)

    for filepath in pending:
        dest = committed_dir / f"{filepath.stem}_{commit_hash}{filepath.suffix}"
        filepath.rename(dest)
    return 0


def main() -> None:
    sys.exit(archive())
