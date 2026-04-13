"""Tests for prepare_repository()."""

from __future__ import annotations

import json
from pathlib import Path

from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.prepare_repository import prepare_repository


# ---------------------------------------------------------------------------
# .prompts/ directory
# ---------------------------------------------------------------------------

def test_prompts_dir_created(repo: Path) -> None:
    assert (repo / PROMPTS_DIRECTORY).is_dir()


def test_prompts_gitignore_contains_wildcard(repo: Path) -> None:
    gitignore = repo / PROMPTS_DIRECTORY / ".gitignore"
    assert gitignore.exists()
    assert "*" in gitignore.read_text(encoding="utf-8").splitlines()


def test_prompts_gitignore_not_duplicated(repo: Path) -> None:
    prepare_repository()  # second run — fixture already ran once
    gitignore = repo / PROMPTS_DIRECTORY / ".gitignore"
    assert gitignore.read_text(encoding="utf-8").splitlines().count("*") == 1


# ---------------------------------------------------------------------------
# top-level .gitignore
# ---------------------------------------------------------------------------

def test_gitignore_is_not_touched(repo: Path) -> None:
    assert not (repo / ".gitignore").exists()

def test_gitignore_existing_content_preserved(repo: Path) -> None:
    # Overwrite with pre-existing content and re-run
    old_content = "*.pyc\n__pycache__\n"
    (repo / ".gitignore").write_text(old_content, encoding="utf-8")
    prepare_repository()
    content = (repo / ".gitignore").read_text(encoding="utf-8")
    assert content == old_content

# ---------------------------------------------------------------------------
# .claude/settings.json
# ---------------------------------------------------------------------------

def _hook_ids(settings: dict) -> list[str]:
    return [
        h.get("id", "")
        for matcher in settings.get("hooks", {}).get("UserPromptSubmit", [])
        for h in matcher.get("hooks", [])
    ]


def test_claude_settings_created_from_scratch(repo: Path) -> None:
    dest = repo / ".claude" / "settings.json"
    assert dest.exists()
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert "ai-prompt-auto-commit" in _hook_ids(settings)


def test_claude_settings_hook_inserted_into_existing_file(repo: Path) -> None:
    # Replace with a file that has other content but no hook, then re-run
    dest = repo / ".claude" / "settings.json"
    dest.write_text(json.dumps({"other": "value"}), encoding="utf-8")
    prepare_repository()
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert settings["other"] == "value"
    assert "ai-prompt-auto-commit" in _hook_ids(settings)


def test_claude_settings_hook_appended_to_existing_matcher(repo: Path) -> None:
    # Replace with a file that has a different hook, then re-run
    dest = repo / ".claude" / "settings.json"
    dest.write_text(json.dumps({
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"id": "other-hook", "type": "command", "command": "echo hi"}]}
            ]
        }
    }), encoding="utf-8")
    prepare_repository()
    ids = _hook_ids(json.loads(dest.read_text(encoding="utf-8")))
    assert "other-hook" in ids
    assert "ai-prompt-auto-commit" in ids


def test_claude_settings_hook_not_duplicated(repo: Path) -> None:
    prepare_repository()  # second run
    dest = repo / ".claude" / "settings.json"
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert _hook_ids(settings).count("ai-prompt-auto-commit") == 1


def test_prepare_repository_returns_zero(repo: Path) -> None:
    assert prepare_repository() == 0
