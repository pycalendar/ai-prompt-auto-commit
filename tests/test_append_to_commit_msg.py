"""Tests for append_to_commit_msg()."""

from __future__ import annotations

from pathlib import Path

from ai_prompt_auto_commit.append import append_to_commit_msg
from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY


def _write_prompt(repo: Path, filename: str, content: str) -> None:
    (repo / PROMPTS_DIRECTORY / filename).write_text(content, encoding="utf-8")


def _commit_msg(repo: Path, initial: str = "Initial commit\n") -> Path:
    path = repo / ".git_commit_editmsg"
    path.write_text(initial, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# basic behaviour
# ---------------------------------------------------------------------------

def test_returns_zero_with_no_prompts(repo: Path) -> None:
    msg = _commit_msg(repo)
    assert append_to_commit_msg(msg) == 0


def test_commit_message_unchanged_when_no_prompts(repo: Path) -> None:
    msg = _commit_msg(repo, "Fix bug\n")
    append_to_commit_msg(msg)
    assert msg.read_text(encoding="utf-8") == "Fix bug\n"


def test_single_prompt_appended(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-sonnet-4-6.md", "refactor the auth module")
    msg = _commit_msg(repo)
    append_to_commit_msg(msg)
    content = msg.read_text(encoding="utf-8")
    assert "AI Prompts:" in content
    assert "claude-sonnet-4-6: refactor the auth module" in content


def test_returns_zero_with_prompts(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-sonnet-4-6.md", "fix the bug")
    msg = _commit_msg(repo)
    assert append_to_commit_msg(msg) == 0


# ---------------------------------------------------------------------------
# ordering and multiple prompts
# ---------------------------------------------------------------------------

def test_multiple_prompts_appended_in_chronological_order(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-sonnet-4-6.md", "first prompt")
    _write_prompt(repo, "2026-01-01T10-01-00_claude-sonnet-4-6.md", "second prompt")
    _write_prompt(repo, "2026-01-01T10-02-00_claude-sonnet-4-6.md", "third prompt")
    msg = _commit_msg(repo)
    append_to_commit_msg(msg)
    content = msg.read_text(encoding="utf-8")
    assert content.index("first prompt") < content.index("second prompt") < content.index("third prompt")


def test_existing_commit_message_preserved(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-sonnet-4-6.md", "some prompt")
    msg = _commit_msg(repo, "My commit message\n")
    append_to_commit_msg(msg)
    content = msg.read_text(encoding="utf-8")
    assert content.startswith("My commit message\n")
    assert "AI Prompts:" in content


# ---------------------------------------------------------------------------
# content formatting
# ---------------------------------------------------------------------------

def test_multiline_prompt_joined_into_one_line(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-opus-4-6.md", "line one\nline two\nline three")
    msg = _commit_msg(repo)
    append_to_commit_msg(msg)
    content = msg.read_text(encoding="utf-8")
    assert "claude-opus-4-6: line one line two line three" in content


def test_repo_root_stripped_from_prompt_content(repo: Path) -> None:
    _write_prompt(
        repo,
        "2026-01-01T10-00-00_claude-sonnet-4-6.md",
        f"look at {repo}/README.md for details",
    )
    msg = _commit_msg(repo)
    append_to_commit_msg(msg)
    content = msg.read_text(encoding="utf-8")
    assert str(repo) not in content
    assert "./README.md" in content


def test_model_extracted_from_filename(repo: Path) -> None:
    _write_prompt(repo, "2026-01-01T10-00-00_claude-haiku-4-5-20251001.md", "write a test")
    msg = _commit_msg(repo)
    append_to_commit_msg(msg)
    assert "claude-haiku-4-5-20251001: write a test" in msg.read_text(encoding="utf-8")
