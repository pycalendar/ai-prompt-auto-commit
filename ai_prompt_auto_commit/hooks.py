"""Git hooks for recording AI prompts in commit messages."""

from __future__ import annotations

import importlib.resources
import json
import subprocess
import sys
from pathlib import Path


PROMPTS_DIRECTORY = ".prompts"


def _repo_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def prepare_repository() -> int:
    """Set up .prompts/, .gitignore, and .claude/settings.json in the target repo."""
    repo_root = _repo_root()

    # Initialize PROMPTS_DIRECTORY with a .gitignore that ignores everything
    prompts_dir = repo_root / PROMPTS_DIRECTORY
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompts_gitignore = prompts_dir / ".gitignore"
    existing_patterns = prompts_gitignore.read_text(encoding="utf-8").splitlines() if prompts_gitignore.exists() else []
    if "*" not in existing_patterns:
        with prompts_gitignore.open("a", encoding="utf-8") as fh:
            fh.write("*\n")
        print(f"Initialized {prompts_gitignore}")
    else:
        print(f"{prompts_gitignore} already ignores *")

    # Add PROMPTS_DIRECTORY to the repo's .gitignore
    gitignore = repo_root / ".gitignore"
    existing_lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    if PROMPTS_DIRECTORY not in existing_lines:
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(f"\n{PROMPTS_DIRECTORY}\n")
        print(f"Added {PROMPTS_DIRECTORY} to {gitignore}")
    else:
        print(f"{PROMPTS_DIRECTORY} already in {gitignore}")

    # Install the UserPromptSubmit hook into .claude/settings.json
    ref = importlib.resources.files("ai_prompt_auto_commit.data").joinpath("claude_settings.json")
    bundled = json.loads(ref.read_text(encoding="utf-8"))
    hook_def = bundled["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    hook_id = hook_def["id"]

    claude_dest = repo_root / ".claude"
    dest_file = claude_dest / "settings.json"

    if dest_file.exists():
        settings = json.loads(dest_file.read_text(encoding="utf-8"))
    else:
        settings = {}

    # Walk existing UserPromptSubmit matchers to check if hook is already present
    matchers = settings.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    already_installed = any(
        h.get("id") == hook_id
        for matcher in matchers
        for h in matcher.get("hooks", [])
    )

    if already_installed:
        print(f"Hook '{hook_id}' already present in {dest_file}")
    else:
        if matchers:
            matchers[0].setdefault("hooks", []).append(hook_def)
        else:
            matchers.append({"hooks": [hook_def]})
        claude_dest.mkdir(parents=True, exist_ok=True)
        dest_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        print(f"Inserted hook '{hook_id}' into {dest_file}")

    return 0


def unstage() -> int:
    """pre-commit: remove any .prompts/ files from the git index."""
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


def append_to_commit_msg(commit_msg_file: Path) -> int:
    """prepare-commit-msg: append pending prompts to the commit message."""
    repo_root = _repo_root()
    prompts_dir = repo_root / PROMPTS_DIRECTORY

    pending = sorted(prompts_dir.glob("*.md"))
    if not pending:
        return 0

    lines: list[str] = ["\nAI Prompts:\n"]
    for filepath in pending:
        stem = filepath.stem
        model = stem.split("_", 1)[1] if "_" in stem else stem
        raw = filepath.read_text(encoding="utf-8")
        # Join lines and strip trailing whitespace
        content = " ".join(raw.splitlines()).rstrip()
        # Remove absolute repo root from any paths embedded in the prompt
        content = content.replace(str(repo_root) + "/", "./")
        lines.append(f"{model}: {content}\n")

    with commit_msg_file.open("a", encoding="utf-8") as fh:
        fh.writelines(lines)
    return 0


def archive() -> int:
    """post-commit: move pending prompts to .prompts/committed/<name>_<hash>.md."""
    repo_root = _repo_root()
    prompts_dir = repo_root / PROMPTS_DIRECTORY
    committed_dir = prompts_dir / "committed"

    pending = sorted(prompts_dir.glob("*.md"))
    if not pending:
        return 0

    commit_hash = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    committed_dir.mkdir(parents=True, exist_ok=True)

    for filepath in pending:
        dest = committed_dir / f"{filepath.stem}_{commit_hash}.md"
        filepath.rename(dest)
    return 0


def prepare_repository_main() -> None:
    sys.exit(prepare_repository())


def unstage_main() -> None:
    sys.exit(unstage())


def append_main() -> None:
    if len(sys.argv) < 2:
        print("Usage: append-ai-prompts <commit-msg-file>", file=sys.stderr)
        exit(1)
    sys.exit(append_to_commit_msg(Path(sys.argv[1])))


def archive_main() -> None:
    sys.exit(archive())
