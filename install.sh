#!/usr/bin/env bash
# Installs the ai-promt-auto-commit hooks into the current git repo

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "Error: .git/hooks directory not found. Are you inside a git repository?" >&2
  exit 1
fi

install_hook() {
  local name="$1"
  local src="$SCRIPT_DIR/$name"
  local dest="$HOOKS_DIR/$name"

  if [ -f "$dest" ]; then
    echo "A $name hook already exists at $dest"
    read -r -p "Overwrite? [y/N] " answer
    case "$answer" in
      [yY]) ;;
      *) echo "Skipping $name."; return ;;
    esac
  fi

  cp "$src" "$dest"
  chmod +x "$dest"
  echo "Installed $name hook to $dest"
}

install_hook pre-commit
install_hook prepare-commit-msg
install_hook post-commit

# Initialize .prompts directory with a .gitignore that ignores .md files
PROMPTS_DIR="$REPO_ROOT/.prompts"
PROMPTS_GITIGNORE="$PROMPTS_DIR/.gitignore"
mkdir -p "$PROMPTS_DIR"
if grep -qxF '*.md' "$PROMPTS_GITIGNORE" 2>/dev/null; then
  echo ".prompts/.gitignore already ignores *.md"
else
  printf '*.md\n' >> "$PROMPTS_GITIGNORE"
  echo "Initialized $PROMPTS_GITIGNORE"
fi

# Add .prompts to .gitignore
GITIGNORE="$REPO_ROOT/.gitignore"
if grep -qxF '.prompts' "$GITIGNORE" 2>/dev/null; then
  echo ".prompts already in $GITIGNORE"
else
  printf '\n.prompts\n' >> "$GITIGNORE"
  echo "Added .prompts to $GITIGNORE"
fi

# Copy .claude/settings.json into the target repo
CLAUDE_DEST="$REPO_ROOT/.claude"
CLAUDE_SRC="$SCRIPT_DIR/.claude/settings.json"

if [ ! -f "$CLAUDE_SRC" ]; then
  echo "Warning: $CLAUDE_SRC not found, skipping Claude settings." >&2
else
  mkdir -p "$CLAUDE_DEST"
  DEST_FILE="$CLAUDE_DEST/settings.json"
  if [ -f "$DEST_FILE" ]; then
    echo ".claude/settings.json already exists at $DEST_FILE"
    echo "Please tell Claude to merge the following settings into the existing $DEST_FILE:"
    echo "---"
    cat "$CLAUDE_SRC"
    echo "---"
  else
    cp "$CLAUDE_SRC" "$DEST_FILE"
    echo "Installed .claude/settings.json to $DEST_FILE"
  fi
fi
