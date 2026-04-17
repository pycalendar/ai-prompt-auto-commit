"""Tests for archive.py — post-commit hook that moves prompt files to committed/."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_prompt_auto_commit.archive import archive

COMMIT_HASH = "abc1234def5678901234567890abcdef01234567"


@pytest.fixture()
def fake_git_hash(monkeypatch: pytest.MonkeyPatch):
    """Patch subprocess so git rev-parse HEAD returns COMMIT_HASH."""
    with patch("ai_prompt_auto_commit.archive.subprocess.check_output", return_value=COMMIT_HASH + "\n"):
        yield


# ---------------------------------------------------------------------------
# no pending files
# ---------------------------------------------------------------------------

def test_returns_zero_when_no_files(repo: Path, fake_git_hash) -> None:
    assert archive() == 0


def test_does_not_create_committed_dir_when_no_files(repo: Path, prompts_dir: Path, fake_git_hash) -> None:
    archive()
    assert not (prompts_dir / "committed").exists()


# ---------------------------------------------------------------------------
# .md files
# ---------------------------------------------------------------------------

def test_moves_md_file_to_committed(repo: Path, prompts_dir: Path, committed_dir: Path, fake_git_hash) -> None:
    f = prompts_dir / "2026-04-17T10-00-00_claude-sonnet-4-6.md"
    f.write_text("prompt\n")
    archive()
    assert not f.exists()
    assert (committed_dir / f"2026-04-17T10-00-00_claude-sonnet-4-6_{COMMIT_HASH}.md").exists()


# ---------------------------------------------------------------------------
# .txt files
# ---------------------------------------------------------------------------

def test_moves_txt_file_to_committed(repo: Path, prompts_dir: Path, committed_dir: Path, fake_git_hash) -> None:
    f = prompts_dir / "2026-04-17T10-00-00_gpt-4o.txt"
    f.write_text("prompt\n")
    archive()
    assert not f.exists()
    assert (committed_dir / f"2026-04-17T10-00-00_gpt-4o_{COMMIT_HASH}.txt").exists()


# ---------------------------------------------------------------------------
# mixed .md and .txt
# ---------------------------------------------------------------------------

def test_moves_both_md_and_txt(repo: Path, prompts_dir: Path, committed_dir: Path, fake_git_hash) -> None:
    md = prompts_dir / "2026-04-17T09-00-00_model-a.md"
    txt = prompts_dir / "2026-04-17T10-00-00_model-b.txt"
    md.write_text("a\n")
    txt.write_text("b\n")
    archive()
    assert not md.exists()
    assert not txt.exists()
    assert (committed_dir / f"2026-04-17T09-00-00_model-a_{COMMIT_HASH}.md").exists()
    assert (committed_dir / f"2026-04-17T10-00-00_model-b_{COMMIT_HASH}.txt").exists()


def test_preserves_file_content(repo: Path, prompts_dir: Path, committed_dir: Path, fake_git_hash) -> None:
    f = prompts_dir / "2026-04-17T10-00-00_my-model.txt"
    f.write_text("my prompt text\n")
    archive()
    dest = committed_dir / f"2026-04-17T10-00-00_my-model_{COMMIT_HASH}.txt"
    assert dest.read_text() == "my prompt text\n"


def test_returns_zero_on_success(repo: Path, prompts_dir: Path, fake_git_hash) -> None:
    (prompts_dir / "2026-04-17T10-00-00_model.txt").write_text("x\n")
    assert archive() == 0
