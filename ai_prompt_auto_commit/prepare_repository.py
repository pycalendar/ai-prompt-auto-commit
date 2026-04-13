"""prepare-ai-repository hook: one-time repository setup."""

from __future__ import annotations

import importlib.resources
import json
import sys
from pathlib import Path

from . import common
from .common import PROMPTS_DIRECTORY


def prepare_repository() -> int:
    """Set up .prompts/, and .claude/settings.json in the target repo."""
    repo_root = common._repo_root()

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

    # Install the UserPromptSubmit hook into .claude/settings.json
    ref = importlib.resources.files("ai_prompt_auto_commit.data").joinpath("claude_settings.json")
    bundled = json.loads(ref.read_text(encoding="utf-8"))
    hook_def = bundled["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    hook_id = hook_def["id"]

    claude_dest = repo_root / ".claude"
    dest_file = claude_dest / "settings.json"

    settings = json.loads(dest_file.read_text(encoding="utf-8")) if dest_file.exists() else {}

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

    # Ensure prepare-commit-msg and post-commit hooks are installed.
    # Derive them from the existing pre-commit hook file by swapping --hook-type.
    hooks_dir = repo_root / ".git" / "hooks"
    pre_commit_hook = hooks_dir / "pre-commit"
    if not pre_commit_hook.exists():
        print("Warning: no pre-commit hook found; skipping hook-type installation.", file=sys.stderr)
    else:
        template = pre_commit_hook.read_text(encoding="utf-8")
        for hook_type in ("prepare-commit-msg", "post-commit"):
            dest = hooks_dir / hook_type
            if dest.exists():
                print(f"{hook_type} hook already installed")
            else:
                content = template.replace(
                    "ARGS=(hook-impl --config=.pre-commit-config.yaml --hook-type=pre-commit)",
                    f"ARGS=(hook-impl --config=.pre-commit-config.yaml --hook-type={hook_type})",
                )
                dest.write_text(content, encoding="utf-8")
                dest.chmod(0o755)
                print(f"Installed {hook_type} hook to {dest}")

    return 0


def main() -> None:
    sys.exit(prepare_repository())
