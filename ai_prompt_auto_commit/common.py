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
    result= []
    for ending in FILE_ENDINGS:
        result.extend(sorted(prompts_dir.glob(f"*{ending}")))
    return result

