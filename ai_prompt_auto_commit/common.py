"""Shared constants and helpers used across all hooks."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROMPTS_DIRECTORY = ".prompts"


def _repo_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )
