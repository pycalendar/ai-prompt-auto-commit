# ai-prompt-auto-commit

[![Tests](https://github.com/pycalendar/ai-prompt-auto-commit/actions/workflows/test.yml/badge.svg)](https://github.com/pycalendar/ai-prompt-auto-commit/actions/workflows/test.yml)
![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)
![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)
![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-blueviolet)

Automatically records every AI prompt you send and appends them to your git commit messages — so your commit history always reflects the AI assistance that shaped the code.

## How it works

1. **Claude Code** saves every prompt to `.prompts/` as a timestamped Markdown file (via a `UserPromptSubmit` hook in `.claude/settings.json`). Other models can also be instructed to do so.
2. On `git commit`, the **`prepare-commit-msg`** hook reads all pending prompts and appends them to the commit message under an `AI Prompts:` section.
3. After the commit, the **`post-commit`** hook moves the used prompts to `.prompts/committed/`, tagged with the commit hash, so they are archived but not reused.

### Commit message example

```text
Fix login redirect bug

AI Prompts:
claude-sonnet-4-6: why does the redirect fail after OAuth callback?
claude-sonnet-4-6: rewrite the session middleware to preserve the return URL
```

[Example Commit](https://github.com/pycalendar/ai-prompt-auto-commit-test/commit/a806094cdd05d612be62cab4302d87c58243b977)

## Requirements

- [git](https://git-scm.com/)
- [pre-commit](https://pre-commit.com/) (`pip install pre-commit`)
- Python 3.10+

## Installation

### 1. Add to `.pre-commit-config.yaml`

Add the following to your repository's `.pre-commit-config.yaml` (create it if it doesn't exist):

```yaml
default_install_hook_types: [pre-commit, prepare-commit-msg, post-commit]

repos:
  - repo: https://github.com/niccokunzmann/ai-prompt-auto-commit
    rev: v0.0.8
    hooks:
      - id: prepare-ai-repository
      - id: unstage-ai-prompts
      - id: append-ai-prompts
      - id: archive-ai-prompts
```

### 2. Install the hooks

This needs to be run for every clone:

```bash
pre-commit install
```

This installs all three git hooks (`pre-commit`, `prepare-commit-msg`, `post-commit`) in one step.

### 3. Set up the repository

This needs to be run once for each repository:

```bash
pre-commit run --hook-stage manual prepare-ai-repository
```

This runs the one-time setup (using the `manual` stage) and will:

- Create a `.prompts/` directory with a `.gitignore` that prevents prompt files from being committed
- Install the Claude Code `UserPromptSubmit` hook into `.claude/settings.json` so prompts are recorded automatically (merges safely with existing settings)

## Updating

To update the hooks:

```shell
pre-commit autoupdate
pre-commit run --hook-stage manual prepare-ai-repository
```

## Contributing prompt recording for another AI

`.github/assistant-guidelines.md` tells AI models how to record each of your prompts.
We welcome your contribution!

## Supported AI models

This pre-commit supports the following AI models:

| Model | ID in commit message |
| --- | --- |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| Claude Opus 4.6 | `claude-opus-4-6` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |
| Any future Claude model | recorded automatically |
| GitHub Copilot | manual prompt recording |

### Claude

The recording is done automatically through the hooks.

#### Trouble Shooting

If no files are created in `.promts`:

- Restart the editor or session.
- Or open /hooks in Claude Code (the UI menu) to reload config.

After that, the hook will fire on every prompt.

### GitHub Copilot

Prompt the AI:

> Save all prompts according to the [assistant guidelines](.github/assistant-guidelines.md)

### Scripts

You can record prompts manually or instruct the AI to use the script.

```sh
record-ai-prompt --prompt "<your prompt>" --model "<model used>"
```

Or pipe text into it:

```sh
printf "%s" "<your prompt>" | record-ai-prompt
```

## File layout

```text
.prompts/
  2026-04-12T20-35-51_claude-sonnet-4-6.txt   ← pending (not yet committed)
  committed/
    2026-04-12T20-10-00_claude-sonnet-4-6_a2e1ca7....txt  ← archived after commit
```

## Changelog

You can view the versions in the [change log](CHANGES.md).

## Release new versions

To release a new version:

```sh
./release 0.0.5
```
