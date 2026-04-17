# Contributing

## Setup

```sh
make dev
```

This creates `.venv/`, installs the package in editable mode, installs `pre-commit` and `pytest`, registers the git hooks, and runs the one-time repository setup.

Activate the virtual environment before working:

```sh
source .venv/bin/activate
```

## Running tests

```sh
make test
# or with the venv active:
pytest
```

## Cleanup

```sh
make clean
```

Removes `.venv/` and the pre-commit cache.

## Project layout

```
ai_prompt_auto_commit/
  common.py            shared helpers (_repo_root, get_prompt_files)
  interceptor.py       record-ai-prompt CLI (saves prompts to .prompts/)
  append.py            prepare-commit-msg hook
  archive.py           post-commit hook (moves prompts to .prompts/committed/)
  unstage.py           pre-commit hook (removes .prompts/ from git index)
  prepare_repository.py  one-time repo setup
tests/
  conftest.py          shared fixtures (repo, tmp git root)
  test_interceptor.py
  test_prepare_repository.py
```

## Adding a new hook entry point

1. Add the function in `ai_prompt_auto_commit/<module>.py`
2. Register a `[project.scripts]` entry in `pyproject.toml`
3. Add a hook entry in `.pre-commit-config.yaml` (use `language: system`)
4. Re-run `make dev` to pick up the new script
