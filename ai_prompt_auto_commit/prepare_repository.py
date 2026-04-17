"""prepare-ai-repository hook: one-time repository setup."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import json
import sys
from pathlib import Path

from . import common
from .common import PROMPTS_DIRECTORY
import re

PACKAGE_VERSION = importlib.metadata.version("ai-prompt-auto-commit")
ASSISTANT_GUIDELINES_HEADER = f"""---
version: "{PACKAGE_VERSION}"
---

"""

def get_data(file_name: str) -> str:
    """Return the contents of a bundled data file."""
    ref = importlib.resources.files("ai_prompt_auto_commit.data").joinpath(file_name)
    return ref.read_text(encoding="utf-8")

def get_default_claude_settings() -> dict:
    """Return the bundled claude_settings.json with the package version injected into the hook."""
    ref = get_data("claude_settings.json")
    settings = json.loads(ref)
    settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["version"] = PACKAGE_VERSION
    return settings

def get_default_assistant_guidelines() -> str:
    """Return the bundled assistant-guidelines.md content with the package version header."""
    content = get_data("assistant-guidelines.md")
    content = re.sub(r"(?m)^---\n(:?[^-]|[^\n]-)*\n---\n", "", content)
    return ASSISTANT_GUIDELINES_HEADER + content

def prepare_repository(
    prompts_directory:str = PROMPTS_DIRECTORY,) -> int:
    """Set up .prompts/, and .claude/settings.json in the target repo."""
    repo_root = common._repo_root()

    # Create PROMPTS_DIRECTORY
    prompts_dir = repo_root / prompts_directory
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Create or update .github/assistant-guidelines.md with the current package version header
    github_dir = repo_root / ".github"
    github_dir.mkdir(parents=True, exist_ok=True)
    guidelines_file = github_dir / "assistant-guidelines.md"
    guidelines_file.write_text(get_default_assistant_guidelines(), encoding="utf-8")
    print(f"Created or updated {guidelines_file}")

    # Add .prompts/ to the root .gitignore
    root_gitignore = repo_root / ".gitignore"
    pattern = f"/{prompts_directory}/"
    existing = root_gitignore.read_text(encoding="utf-8").splitlines() if root_gitignore.exists() else []
    if pattern not in existing:
        with root_gitignore.open("a", encoding="utf-8") as fh:
            fh.write(f"{pattern}\n")
        print(f"Added '{pattern}' to {root_gitignore}")
    else:
        print(f"{root_gitignore} already contains '{pattern}'")

    # Install the UserPromptSubmit hook into .claude/settings.json
    bundled = get_default_claude_settings()
    hook_def = bundled["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    hook_id = hook_def["id"]
    package_version = hook_def["version"]

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
        for matcher in matchers:
            hooks_list = matcher.get("hooks", [])
            for i, h in enumerate(hooks_list):
                if h.get("id") == hook_id:
                    hooks_list[i] = hook_def
        print(f"Updated hook '{hook_id}' to version {package_version} in {dest_file}")
    else:
        if matchers:
            matchers[0].setdefault("hooks", []).append(hook_def)
        else:
            matchers.append({"hooks": [hook_def]})
        print(f"Inserted hook '{hook_id}' into {dest_file}")

    claude_dest.mkdir(parents=True, exist_ok=True)
    dest_file.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

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
