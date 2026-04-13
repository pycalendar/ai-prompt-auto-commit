from __future__ import annotations

from pathlib import Path

import pytest

import ai_prompt_auto_commit.common as common
from ai_prompt_auto_commit.prepare_repository import prepare_repository


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary directory acting as the git repo root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    monkeypatch.setattr(common, "_repo_root", lambda: repo)
    prepare_repository()
    return repo
