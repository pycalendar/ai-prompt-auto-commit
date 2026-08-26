"""Tests for prepare_repository()."""

from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path

from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.prepare_repository import (
    HOOK_SCRIPT_FILENAME,
    get_default_assistant_guidelines,
    get_default_claude_settings,
    get_default_hook_script,
    prepare_repository,
)


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


def test_root_gitignore_newline_added_when_missing(repo: Path) -> None:
    (repo / ".gitignore").write_text("*.pyc", encoding="utf-8")  # no trailing newline
    prepare_repository()
    lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert f"/{PROMPTS_DIRECTORY}/" in lines
    assert lines[0] == "*.pyc"


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
# get_default_assistant_guidelines
# ---------------------------------------------------------------------------

def test_get_default_assistant_guidelines_includes_header() -> None:
    content = get_default_assistant_guidelines()
    expected_header = f"""---
version: "{importlib.metadata.version("ai-prompt-auto-commit")}"
---

"""
    assert content.startswith(expected_header)


def test_get_default_assistant_guidelines_only_one_header() -> None:
    content = get_default_assistant_guidelines()
    header_start = content.find("---")
    assert header_start != -1
    header_end = content.find("---", header_start + 3)
    assert header_end != -1
    # There should be no more --- before the content
    next_header = content.find("---", header_end + 3)
    assert next_header == -1, "Multiple headers found in assistant guidelines"

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


# ---------------------------------------------------------------------------
# .claude/hooks/record-prompt.py
# ---------------------------------------------------------------------------

def test_hook_script_installed(repo: Path) -> None:
    script = repo / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME
    assert script.is_file()
    assert os.access(script, os.X_OK)


def test_hook_script_version_matches_package(repo: Path) -> None:
    script = repo / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME
    expected = importlib.metadata.version("ai-prompt-auto-commit")
    assert f'HOOK_VERSION = "{expected}"' in script.read_text(encoding="utf-8")


def test_hook_script_refreshed_on_rerun(repo: Path) -> None:
    script = repo / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME
    script.write_text("# stale\n", encoding="utf-8")
    prepare_repository()
    assert script.read_text(encoding="utf-8") == get_default_hook_script()


def test_hook_command_invokes_the_script(repo: Path) -> None:
    hook = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert HOOK_SCRIPT_FILENAME in hook["command"]


def test_hook_command_has_no_hardcoded_model(repo: Path) -> None:
    """Regression: the model was defaulted to a constant, so every prompt lied."""
    hook = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert "claude-" not in hook["command"]


def test_hook_command_does_not_require_jq(repo: Path) -> None:
    """jq was an undocumented hard dependency; failure was silent."""
    hook = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert "jq" not in hook["command"]


def test_get_default_assistant_guidelines_is_idempotent(repo: Path) -> None:
    """Re-running prepare_repository() must leave the file byte-identical.

    This does not pin the blank-line fix on its own — the generator reads the
    bundled data file, so it was always stable across two calls. The round
    trip below is what pins it.
    """
    guidelines = repo / ".github" / "assistant-guidelines.md"
    before = guidelines.read_text(encoding="utf-8")
    prepare_repository()
    assert guidelines.read_text(encoding="utf-8") == before


def test_assistant_guidelines_survives_the_release_round_trip(monkeypatch) -> None:
    """`./release` copies the generated .github/ file back over the bundled
    one, so generating from an already-generated file must be a no-op."""
    import ai_prompt_auto_commit.prepare_repository as pr

    generated = pr.get_default_assistant_guidelines()
    monkeypatch.setattr(pr, "get_data", lambda name: generated)
    assert pr.get_default_assistant_guidelines() == generated
