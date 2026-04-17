"""prepare-commit-msg hook: append pending prompts to the commit message."""

from __future__ import annotations

import sys
from pathlib import Path

from . import common
from .common import PROMPTS_DIRECTORY


FILE_ENDINGS = [".md", ".txt"]

def get_prompt_files() -> list[Path]:
    """Return a list of pending prompt files."""
    repo_root = common._repo_root()
    prompts_dir = repo_root / PROMPTS_DIRECTORY
    result= []
    for ending in FILE_ENDINGS:
        result.extend(sorted(prompts_dir.glob(f"*{ending}")))
    return result

def append_to_commit_msg(commit_msg_file: Path) -> int:
    """Append all pending .prompts/*.md files to the commit message."""
    repo_root = common._repo_root()

    pending = get_prompt_files()
    if not pending:
        return 0

    lines: list[str] = ["\nAI Prompts:\n"]
    for filepath in pending:
        stem = filepath.stem
        model = stem.split("_", 1)[1] if "_" in stem else stem
        raw = filepath.read_text(encoding="utf-8")
        content = " ".join(raw.splitlines()).rstrip()
        content = content.replace(str(repo_root) + "/", "./")
        lines.append(f"{model}: {content}\n")

    with commit_msg_file.open("a", encoding="utf-8") as fh:
        fh.writelines(lines)
    return 0


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: append-ai-prompts <commit-msg-file>", file=sys.stderr)
        sys.exit(1)
    sys.exit(append_to_commit_msg(Path(sys.argv[1])))
