"""Tests for prepare_repository()."""

from __future__ import annotations

import importlib.metadata
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytest

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


GENERATED_FILES = (
    "/.claude/settings.local.json",
    "/.claude/hooks/record-prompt.py",
    "/.github/assistant-guidelines.md",
)


def test_root_gitignore_contains_generated_files(repo: Path) -> None:
    """Regression: the generated files were left for the user to commit,
    and stale committed copies kept running an outdated hook."""
    lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in GENERATED_FILES:
        assert pattern in lines


def test_root_gitignore_generated_files_not_duplicated(repo: Path) -> None:
    prepare_repository()  # second run
    lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    for pattern in GENERATED_FILES:
        assert lines.count(pattern) == 1


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


def test_assistant_guidelines_date_command_matches_filename_pattern() -> None:
    """The guidelines tell other AI models which `date` command produces the
    timestamp; it has to be the format the hooks write, `T` included."""
    content = get_default_assistant_guidelines()
    match = re.search(r"`date \+([^`]+)`", content)
    assert match, "the guidelines name no date command"
    timestamp = datetime(2026, 10, 7, 9, 5, 3).strftime(match.group(1))
    assert timestamp == "2026-10-07T09-05-03"


# ---------------------------------------------------------------------------
# .claude/settings.local.json
# ---------------------------------------------------------------------------

def _hook_ids(settings: dict) -> list[str]:
    return [
        h.get("id", "")
        for matcher in settings.get("hooks", {}).get("UserPromptSubmit", [])
        for h in matcher.get("hooks", [])
    ]


def test_claude_settings_created_from_scratch(repo: Path) -> None:
    dest = repo / ".claude" / "settings.local.json"
    assert dest.exists()
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert "ai-prompt-auto-commit" in _hook_ids(settings)


def test_claude_settings_hook_inserted_into_existing_file(repo: Path) -> None:
    # Replace with a file that has other content but no hook, then re-run
    dest = repo / ".claude" / "settings.local.json"
    dest.write_text(json.dumps({"other": "value"}), encoding="utf-8")
    prepare_repository()
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert settings["other"] == "value"
    assert "ai-prompt-auto-commit" in _hook_ids(settings)


def test_claude_settings_hook_appended_to_existing_matcher(repo: Path) -> None:
    # Replace with a file that has a different hook, then re-run
    dest = repo / ".claude" / "settings.local.json"
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
    dest = repo / ".claude" / "settings.local.json"
    settings = json.loads(dest.read_text(encoding="utf-8"))
    assert _hook_ids(settings).count("ai-prompt-auto-commit") == 1


def test_claude_settings_hook_has_version(repo: Path) -> None:
    dest = repo / ".claude" / "settings.local.json"
    settings = json.loads(dest.read_text(encoding="utf-8"))
    hook = next(
        h for matcher in settings["hooks"]["UserPromptSubmit"]
        for h in matcher.get("hooks", [])
        if h.get("id") == "ai-prompt-auto-commit"
    )
    expected = importlib.metadata.version("ai-prompt-auto-commit")
    assert hook["version"] == expected


def test_claude_settings_hook_updated_on_rerun(repo: Path) -> None:
    dest = repo / ".claude" / "settings.local.json"
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


def test_shared_claude_settings_not_created(repo: Path) -> None:
    """The hook goes into the per-user settings file; the shared, committed
    .claude/settings.json is not ours to create."""
    assert not (repo / ".claude" / "settings.json").exists()


def test_hook_moved_out_of_shared_settings(repo: Path) -> None:
    """Upgrading from a version that installed into settings.json must not
    leave the hook in both files, or every prompt is recorded twice."""
    shared = repo / ".claude" / "settings.json"
    old_hook = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    shared.write_text(json.dumps({
        "permissions": {"allow": ["Bash(ls)"]},
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [old_hook, {"id": "other-hook", "type": "command", "command": "echo hi"}]}
            ]
        },
    }), encoding="utf-8")
    prepare_repository()
    settings = json.loads(shared.read_text(encoding="utf-8"))
    assert settings["permissions"] == {"allow": ["Bash(ls)"]}
    assert _hook_ids(settings) == ["other-hook"]
    local = json.loads((repo / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert "ai-prompt-auto-commit" in _hook_ids(local)


def test_shared_settings_removed_when_only_our_hook(repo: Path) -> None:
    shared = repo / ".claude" / "settings.json"
    shared.write_text(json.dumps(get_default_claude_settings()), encoding="utf-8")
    prepare_repository()
    assert not shared.exists()


def test_shared_settings_without_our_hook_untouched(repo: Path) -> None:
    shared = repo / ".claude" / "settings.json"
    content = '{"permissions": {}}'
    shared.write_text(content, encoding="utf-8")
    prepare_repository()
    assert shared.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("content", [
    "{not json",
    "[]",
    '{"hooks": null}',
    '{"hooks": {"UserPromptSubmit": "oops"}}',
    '{"hooks": {"UserPromptSubmit": ["oops", {"hooks": [null]}]}}',
])
def test_odd_shared_settings_left_alone(repo: Path, content: str) -> None:
    """The shared file is the user's; content we do not understand is
    skipped with a warning, not a crash of the whole setup."""
    shared = repo / ".claude" / "settings.json"
    shared.write_text(content, encoding="utf-8")
    assert prepare_repository() == 0
    assert shared.read_text(encoding="utf-8") == content


def test_shared_settings_other_matchers_untouched(repo: Path) -> None:
    shared = repo / ".claude" / "settings.json"
    ours = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]
    shared.write_text(json.dumps({
        "hooks": {"UserPromptSubmit": [{"matcher": "keep-me"}, ours]}
    }), encoding="utf-8")
    prepare_repository()
    settings = json.loads(shared.read_text(encoding="utf-8"))
    assert settings == {"hooks": {"UserPromptSubmit": [{"matcher": "keep-me"}]}}


def test_shared_settings_keep_non_ascii(repo: Path) -> None:
    shared = repo / ".claude" / "settings.json"
    settings = get_default_claude_settings()
    settings["description"] = "Blåbærsyltetøy"
    shared.write_text(json.dumps(settings, ensure_ascii=False), encoding="utf-8")
    prepare_repository()
    assert "Blåbærsyltetøy" in shared.read_text(encoding="utf-8")


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
    """The bundled file carries a version header of its own, so generating
    from an already-generated file must be a no-op."""
    import ai_prompt_auto_commit.prepare_repository as pr

    generated = pr.get_default_assistant_guidelines()
    monkeypatch.setattr(pr, "get_data", lambda name: generated)
    assert pr.get_default_assistant_guidelines() == generated
