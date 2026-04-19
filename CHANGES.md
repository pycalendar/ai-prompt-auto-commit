# Changelog

<!-- Note: Adding a version here, also edit README.md pre-commit template. -->

## v0.0.8

- Fix: Include all files in the `data` directory of the package.

## v0.0.7

- Create support for GitHub Copilot
- `prepare-ai-repository` now creates or updates `.github/assistant-guidelines.md`
  - copies bundled assistant-guidelines content into the repo
  - adds a header with the current package version
- Add `record-ai-prompt` script — saves a prompt to `.prompts/` from the command line or stdin
  - `--model` defaults to the last used model inferred from existing prompt filenames
  - raises an error if no prior prompt files exist and no `--model` is given
- `archive-ai-prompts` now archives both `*.txt` and `*.md` prompt files (previously only `*.md`)
- Development: add `Makefile` (`make dev`, `make test`, `make clean`) and `CONTRIBUTING.md`
- Development: fix pre-commit hooks to use `.venv/bin/` scripts via `language: script`

## v0.0.6

- Create .prompts if absent in `.clauded/settings.json`
- `prepare-ai-repository` hook
  - adds .prompts to the `/.gitignore`
  - updates the hook `.claude/settings.json`
  - adds a version to the hook

## v0.0.5

- Create release script
- Update versions in files

## v0.0.4

- Do not add `.prompts` to `/.gitignore`. The `.gitignore` in `.prompts` is sufficient.

## v0.0.3

- Use Python 3.10+

## v0.0.2

- document how to properly install this package

## v0.0.1

- First release.
- **`unstage-ai-prompts`** (`pre-commit` stage)
    Removes any `.prompts/` files from the git index before a commit is created,
    ensuring prompt files never end up in version history regardless of how they
    were staged.
- **`append-ai-prompts`** (`prepare-commit-msg` stage)
    Reads every pending `.prompts/*.md` file (sorted chronologically by filename),
    joins multi-line prompts into a single line, strips the repository root from
    embedded paths, and appends the results to the commit message under an
    `AI Prompts:` section in the format `<model>: <prompt>`.
- **`archive-ai-prompts`** (`post-commit` stage)
    After a successful commit, moves all pending prompt files from `.prompts/` to
    `.prompts/committed/`, renaming each to include the commit hash. If a commit
    is aborted the prompts remain in `.prompts/` and are picked up by the next
    commit.
