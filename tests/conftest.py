from __future__ import annotations

from pathlib import Path

import pytest

import ai_prompt_auto_commit.hooks as hooks

from ai_prompt_auto_commit.hooks import prepare_repository


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary directory acting as the git repo root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    monkeypatch.setattr(hooks, "_repo_root", lambda: repo)
    prepare_repository()
    return repo
