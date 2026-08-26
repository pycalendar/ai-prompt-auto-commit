"""Shared constants and helpers used across all hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROMPTS_DIRECTORY = ".prompts"
COMMITTED_DIRECTORY = f"{PROMPTS_DIRECTORY}/committed"


def _repo_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )

FILE_ENDINGS = [".md", ".txt"]

def get_prompt_files() -> list[Path]:
    """Return a list of pending prompt files."""
    repo_root = _repo_root()
    prompts_dir = repo_root / PROMPTS_DIRECTORY
    result = []
    for ending in FILE_ENDINGS:
        result.extend(prompts_dir.glob(f"*{ending}"))
    # By write time, not by name: a sequence-numbered "<ts>-001_<model>" sorts
    # before the plain "<ts>_<model>" it followed, because '-' < '_'.
    return sorted(result, key=lambda p: (p.stat().st_mtime_ns, p.name))
