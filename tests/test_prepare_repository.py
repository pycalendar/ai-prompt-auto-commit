"""Tests for prepare_repository()."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path

from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.prepare_repository import get_default_claude_settings, prepare_repository


# ---------------------------------------------------------------------------
# .prompts/ directory
# ---------------------------------------------------------------------------

def test_prompts_dir_created(repo: Path) -> None:
    assert (repo / PROMPTS_DIRECTORY).is_dir()


# ---------------------------------------------------------------------------
# top-level .gitignore
# ---------------------------------------------------------------------------

def test_root_gitignore_contains_prompts_pattern(repo: Path) -> None:
    gitignore = repo / ".gitignore"
    assert gitignore.exists()
    assert f"/{PROMPTS_DIRECTORY}/" in gitignore.read_text(encoding="utf-8").splitlines()


def test_root_gitignore_pattern_not_duplicated(repo: Path) -> None:
    prepare_repository()  # second run
    gitignore = repo / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines()
    assert lines.count(f"/{PROMPTS_DIRECTORY}/") == 1


def test_root_gitignore_existing_content_preserved(repo: Path) -> None:
    old_content = "*.pyc\n__pycache__\n"
    (repo / ".gitignore").write_text(old_content, encoding="utf-8")
    prepare_repository()
    content = (repo / ".gitignore").read_text(encoding="utf-8")
    assert content.startswith(old_content)
    assert f"/{PROMPTS_DIRECTORY}/" in content


# ---------------------------------------------------------------------------
# get_default_claude_settings
# ---------------------------------------------------------------------------

def test_get_default_claude_settings_returns_hook() -> None:
    settings = get_default_claude_settings()
    hooks = settings["hooks"]["UserPromptSubmit"][0]["hooks"]
    assert any(h.get("id") == "ai-prompt-auto-commit" for h in hooks)


def test_get_default_claude_settings_version_matches_package() -> None:
    settings = get_default_claude_settings()
    hook = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    expected = importlib.metadata.version("ai-prompt-auto-commit")
    assert hook["version"] == expected

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


def test_claude_settings_hook_has_version(repo: Path) -> None:
    dest = repo / ".claude" / "settings.json"
    settings = json.loads(dest.read_text(encoding="utf-8"))
    hook = next(
        h for matcher in settings["hooks"]["UserPromptSubmit"]
        for h in matcher.get("hooks", [])
        if h.get("id") == "ai-prompt-auto-commit"
    )
    expected = importlib.metadata.version("ai-prompt-auto-commit")
    assert hook["version"] == expected


def test_claude_settings_hook_updated_on_rerun(repo: Path) -> None:
    dest = repo / ".claude" / "settings.json"
    # Corrupt the existing hook with stale content
    settings = json.loads(dest.read_text(encoding="utf-8"))
    for matcher in settings["hooks"]["UserPromptSubmit"]:
        for h in matcher.get("hooks", []):
            if h.get("id") == "ai-prompt-auto-commit":
                h["version"] = "0.0.0"
                h["command"] = "stale command"
                h["extra_stale_key"] = "should be removed"
    dest.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    prepare_repository()
    settings = json.loads(dest.read_text(encoding="utf-8"))
    hook = next(
        h for matcher in settings["hooks"]["UserPromptSubmit"]
        for h in matcher.get("hooks", [])
        if h.get("id") == "ai-prompt-auto-commit"
    )
    expected = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert hook == expected
    assert "extra_stale_key" not in hook


def test_prepare_repository_returns_zero(repo: Path) -> None:
    assert prepare_repository() == 0
    assert repo.is_dir()
