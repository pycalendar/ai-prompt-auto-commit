from __future__ import annotations

from pathlib import Path

import pytest

import ai_prompt_auto_commit.common as common
from ai_prompt_auto_commit.common import PROMPTS_DIRECTORY
from ai_prompt_auto_commit.prepare_repository import prepare_repository


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Temporary directory acting as the git repo root."""
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    monkeypatch.setattr(common, "_repo_root", lambda: repo)
    prepare_repository()
    return repo


@pytest.fixture()
def prompts_dir(repo: Path) -> Path:
    return repo / PROMPTS_DIRECTORY


@pytest.fixture()
def committed_dir(prompts_dir: Path) -> Path:
    d = prompts_dir / "committed"
    d.mkdir(exist_ok=True)
    return d
