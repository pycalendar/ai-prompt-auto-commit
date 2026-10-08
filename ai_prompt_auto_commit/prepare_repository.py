"""prepare-ai-repository hook: one-time repository setup."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.abc import Traversable

from . import common
from .common import PROMPTS_DIRECTORY
import re

PACKAGE_VERSION = importlib.metadata.version("ai-prompt-auto-commit")
ASSISTANT_GUIDELINES_HEADER = f"""---
version: "{PACKAGE_VERSION}"
---

"""

# The UserPromptSubmit hook script, bundled as package data and installed into
# the target repository.  It cannot import this package — the console scripts
# live in pre-commit's isolated cache venv, which is not on the assistant's
# PATH — so a self-contained copy is placed where the hook can reach it.
HOOK_SCRIPT_DATA = "record_prompt.py"
HOOK_SCRIPT_FILENAME = "record-prompt.py"
HOOK_VERSION_PATTERN = r'(?m)^HOOK_VERSION = ".*"'

# Claude Code's per-user settings file.  The hook goes here rather than into
# the shared .claude/settings.json, which is meant to be committed.
CLAUDE_SETTINGS_FILE = ".claude/settings.local.json"
SHARED_CLAUDE_SETTINGS_FILE = ".claude/settings.json"

# Files written by prepare_repository(), added to the target's .gitignore.
GENERATED_FILES = (
    f"/{CLAUDE_SETTINGS_FILE}",
    f"/.claude/hooks/{HOOK_SCRIPT_FILENAME}",
    "/.github/assistant-guidelines.md",
)

def get_data_path(file_name: str) -> "Traversable":
    """Return the path of a bundled data file."""
    return importlib.resources.files("ai_prompt_auto_commit.data").joinpath(file_name)

def get_data(file_name: str) -> str:
    """Return the contents of a bundled data file."""
    return get_data_path(file_name).read_text(encoding="utf-8")

def get_default_claude_settings() -> dict:
    """Return the bundled claude_settings.json with the package version injected into the hook."""
    ref = get_data("claude_settings.json")
    settings = json.loads(ref)
    settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["version"] = PACKAGE_VERSION
    return settings

def get_default_hook_script() -> str:
    """Return the bundled hook script with the package version injected."""
    content = get_data(HOOK_SCRIPT_DATA)
    return re.sub(
        HOOK_VERSION_PATTERN,
        f'HOOK_VERSION = "{PACKAGE_VERSION}"',
        content,
        count=1,
    )

def get_default_assistant_guidelines() -> str:
    """Return the bundled assistant-guidelines.md content with the package version header."""
    content = get_data("assistant-guidelines.md")
    content = re.sub(r"(?m)^---\n(?:[^-]|[^\n]-)*\n---\n", "", content)
    # The header supplies its own blank line; without this the file grows one
    # more of them on every run.
    return ASSISTANT_GUIDELINES_HEADER + content.lstrip("\n")

def hook_installed(repo_root: Path) -> bool:
    """Whether the Claude Code hook is in place: the script, and its entry in
    a settings file (the shared one, until prepare-ai-repository moves it).
    Either can go missing on its own."""
    if not (repo_root / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME).exists():
        return False
    hook_id = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]["id"]
    for name in (CLAUDE_SETTINGS_FILE, SHARED_CLAUDE_SETTINGS_FILE):
        try:
            settings = json.loads((repo_root / name).read_text(encoding="utf-8"))
            if any(
                h.get("id") == hook_id
                for m in settings["hooks"]["UserPromptSubmit"]
                for h in m.get("hooks") or []
            ):
                return True
        except (OSError, ValueError, KeyError, AttributeError, TypeError):
            pass
    return False

def _remove_hook_from(settings_file: Path, hook_id: str) -> None:
    """Remove the hook that versions up to 0.0.10 installed into the shared
    settings file, so it does not run twice.  Containers left empty are
    pruned, and so is the file if nothing else remains in it.

    The file belongs to the user, so content of an unexpected shape is left
    alone with a warning rather than aborting the setup.
    """
    if not settings_file.exists():
        return
    try:
        settings = json.loads(settings_file.read_text(encoding="utf-8"))
        hooks = settings.get("hooks") or {}
        matchers = hooks.get("UserPromptSubmit") or []
        found = any(
            h.get("id") == hook_id for m in matchers for h in m.get("hooks") or []
        )
    except (ValueError, AttributeError, TypeError):
        print(f"Warning: cannot read {settings_file}; leaving it alone.", file=sys.stderr)
        return
    if not found:
        return
    emptied = []
    for matcher in matchers:
        before = matcher.get("hooks") or []
        if any(h.get("id") == hook_id for h in before):
            matcher["hooks"] = [h for h in before if h.get("id") != hook_id]
            if not matcher["hooks"]:
                emptied.append(matcher)
    matchers[:] = [m for m in matchers if not any(m is e for e in emptied)]
    if not matchers:
        del hooks["UserPromptSubmit"]
    if not hooks:
        del settings["hooks"]
    if settings:
        settings_file.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Removed hook '{hook_id}' from {settings_file}")
    else:
        settings_file.unlink()
        print(f"Removed {settings_file}, which held nothing but hook '{hook_id}'")


def prepare_repository(
    prompts_directory:str = PROMPTS_DIRECTORY,) -> int:
    """Set up .prompts/, and .claude/settings.local.json in the target repo."""
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

    # Keep the prompts and every generated file out of git.  The generated
    # files are rewritten on each run, so a committed copy only goes stale.
    root_gitignore = repo_root / ".gitignore"
    for pattern in (f"/{prompts_directory}/", *GENERATED_FILES):
        existing_text = root_gitignore.read_text(encoding="utf-8") if root_gitignore.exists() else ""
        if pattern not in existing_text.splitlines():
            with root_gitignore.open("a", encoding="utf-8") as fh:
                if existing_text and not existing_text.endswith("\n"):
                    fh.write("\n")
                fh.write(f"{pattern}\n")
            print(f"Added '{pattern}' to {root_gitignore}")
        else:
            print(f"{root_gitignore} already contains '{pattern}'")

    # Install the UserPromptSubmit hook into the per-user settings file
    bundled = get_default_claude_settings()
    hook_def = bundled["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    hook_id = hook_def["id"]
    package_version = hook_def["version"]

    claude_dest = repo_root / ".claude"
    dest_file = repo_root / CLAUDE_SETTINGS_FILE
    _remove_hook_from(repo_root / SHARED_CLAUDE_SETTINGS_FILE, hook_id)

    # Install the hook script the settings above point at.  Always rewritten,
    # so an outdated copy cannot survive an upgrade.
    hooks_dest = claude_dest / "hooks"
    hooks_dest.mkdir(parents=True, exist_ok=True)
    script_file = hooks_dest / HOOK_SCRIPT_FILENAME
    script_file.write_text(get_default_hook_script(), encoding="utf-8")
    script_file.chmod(0o755)
    print(f"Created or updated {script_file}")

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
