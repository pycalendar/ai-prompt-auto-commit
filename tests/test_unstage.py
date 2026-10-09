"""Tests for unstage()."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.prepare_repository import HOOK_SCRIPT_FILENAME
from ai_prompt_auto_commit.unstage import hint_missing_hook, unstage


def _diff_result(stdout: str) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    return result


@pytest.fixture()
def mock_run():
    with patch("ai_prompt_auto_commit.unstage.subprocess.run") as m:
        yield m


# ---------------------------------------------------------------------------
# no staged prompts
# ---------------------------------------------------------------------------

def test_returns_zero_when_nothing_staged(mock_run: MagicMock) -> None:
    mock_run.return_value = _diff_result("")
    assert unstage() == 0
    # only the diff command was called — no restore
    assert mock_run.call_count == 1


def test_no_restore_called_when_nothing_staged(mock_run: MagicMock) -> None:
    mock_run.return_value = _diff_result("")
    unstage()
    restore_calls = [c for c in mock_run.call_args_list if "restore" in c.args[0]]
    assert restore_calls == []


# ---------------------------------------------------------------------------
# staged prompts are unstaged
# ---------------------------------------------------------------------------

def test_single_staged_prompt_is_unstaged(mock_run: MagicMock) -> None:
    staged = f"{PROMPTS_DIRECTORY}/2026-01-01T10-00-00_claude-sonnet-4-6.md"
    mock_run.side_effect = [_diff_result(staged), MagicMock(returncode=0)]
    unstage()
    mock_run.assert_any_call(
        ["git", "restore", "--staged", "--", staged],
        check=True,
    )


def test_multiple_staged_prompts_all_unstaged(mock_run: MagicMock) -> None:
    files = [
        f"{PROMPTS_DIRECTORY}/2026-01-01T10-00-00_claude-sonnet-4-6.md",
        f"{PROMPTS_DIRECTORY}/2026-01-01T10-01-00_claude-opus-4-6.md",
    ]
    mock_run.side_effect = [_diff_result("\n".join(files))] + [MagicMock(returncode=0)] * len(files)
    unstage()
    restore_calls = [c for c in mock_run.call_args_list if "restore" in c.args[0]]
    assert len(restore_calls) == 2
    restored_paths = [c.args[0][-1] for c in restore_calls]
    assert files[0] in restored_paths
    assert files[1] in restored_paths


def test_returns_zero_after_unstaging(mock_run: MagicMock) -> None:
    staged = f"{PROMPTS_DIRECTORY}/2026-01-01T10-00-00_claude-sonnet-4-6.md"
    mock_run.side_effect = [_diff_result(staged), MagicMock(returncode=0)]
    assert unstage() == 0


# ---------------------------------------------------------------------------
# diff command shape
# ---------------------------------------------------------------------------

def test_diff_command_filters_prompts_directory(mock_run: MagicMock) -> None:
    mock_run.return_value = _diff_result("")
    unstage()
    cmd = mock_run.call_args_list[0].args[0]
    assert cmd[:4] == ["git", "diff", "--cached", "--name-only"]
    assert f"{PROMPTS_DIRECTORY}/" in cmd


# ---------------------------------------------------------------------------
# hint when the Claude Code hook script is missing
# ---------------------------------------------------------------------------


def _hint(repo: Path) -> str:
    tty = repo / "tty"
    tty.write_text("", encoding="utf-8")
    hint_missing_hook(repo, tty)
    return tty.read_text(encoding="utf-8")


def test_no_hint_when_prepared(repo: Path) -> None:
    assert _hint(repo) == ""


def test_hint_when_hook_script_missing(repo: Path) -> None:
    """The generated files are gitignored, so a fresh clone records nothing
    until prepare-ai-repository has run; say so on every commit."""
    (repo / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME).unlink()
    assert "prepare-ai-repository" in _hint(repo)


@pytest.mark.parametrize("settings", [None, "{not json", "[]", '{"hooks": {}}'])
def test_hint_when_hook_missing_from_settings(repo: Path, settings: str | None) -> None:
    """Pulling the commit that stops tracking .claude/settings.json removes
    the hook while the ignored script survives."""
    local = repo / ".claude" / "settings.local.json"
    if settings is None:
        local.unlink()
    else:
        local.write_text(settings, encoding="utf-8")
    assert "prepare-ai-repository" in _hint(repo)


def test_no_hint_while_hook_still_in_shared_settings(repo: Path) -> None:
    """A clone not yet re-prepared still records through settings.json."""
    local = repo / ".claude" / "settings.local.json"
    local.rename(repo / ".claude" / "settings.json")
    assert _hint(repo) == ""


def test_hint_can_be_switched_off(repo: Path) -> None:
    """A clone that does not use Claude Code needs a way to silence it."""
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "ai-prompt-auto-commit.hint", "false"],
        check=True,
    )
    (repo / ".claude" / "hooks" / HOOK_SCRIPT_FILENAME).unlink()
    assert _hint(repo) == ""


def test_hint_without_terminal_is_silent(tmp_path: Path) -> None:
    """IDEs, CI and agents commit without a tty; that must not fail."""
    hint_missing_hook(tmp_path, tmp_path / "no-such-dir" / "tty")
