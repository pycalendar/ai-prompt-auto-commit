"""Tests for unstage()."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.unstage import unstage


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
