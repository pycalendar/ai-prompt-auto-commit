"""pre-commit hook: remove .prompts/ files from the git index."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import common
from .common import PROMPTS_DIRECTORY
from .prepare_repository import hook_installed

MISSING_HOOK_HINT = (
    "ai-prompt-auto-commit: Claude Code prompts are not recorded in this clone; run\n"
    "  pre-commit run --hook-stage manual prepare-ai-repository\n"
    "(or silence this with: git config ai-prompt-auto-commit.hint false)\n"
)


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


def hint_missing_hook(repo_root: Path, tty: Path = Path("/dev/tty")) -> None:
    """Tell the user when the Claude Code hook is not installed in this clone.

    pre-commit hides the output of hooks that pass, so the hint goes straight
    to the terminal.  Without one (IDE, CI, an agent) it is skipped.
    `git config ai-prompt-auto-commit.hint false` switches it off.
    """
    if hook_installed(repo_root):
        return
    setting = subprocess.run(
        ["git", "-C", str(repo_root), "config", "--type=bool", "--get", "ai-prompt-auto-commit.hint"],
        capture_output=True,
        text=True,
    )
    if setting.stdout.strip() == "false":
        return
    try:
        with tty.open("w", encoding="utf-8") as fh:
            fh.write(MISSING_HOOK_HINT)
    except OSError:
        pass


def main() -> None:
    hint_missing_hook(common._repo_root())
    sys.exit(unstage())
