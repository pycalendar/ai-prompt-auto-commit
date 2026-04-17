"""Save AI prompts to `.prompts/` using repository conventions.

Usage examples:

    record-ai-prompt --prompt "why does this fail?"
    printf "%s" "write a faster query" | record-ai-prompt
    record-ai-prompt --prompt "summarize this code" --model "copilot"

The module docstring is used as the argparse help description.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from . import common

PROMPTS_DIR = ".prompts"
FILE_EXTENSION = ".txt"


def _model_from_filename(name: str) -> str:
    """Extract the model name from a prompt filename.

    Supported patterns:
      {timestamp}_{model}.txt
      {timestamp}-{seq}_{model}.txt
      {timestamp}_{model}_{hash}.md
    """
    without_ext = name.rsplit(".", 1)[0]
    parts = without_ext.split("_")
    # parts[0] is the timestamp (possibly with a sequence suffix), parts[1] is the model
    if len(parts) < 2:
        return ""
    return parts[1]


def get_last_used_model(prompts_dir: Path) -> str:
    """Return the model name from the most recently modified prompt file.

    Searches both *prompts_dir* and *prompts_dir/committed*.
    Raises SystemExit if no prompt files are found.
    """
    candidates: list[Path] = []
    for pattern in ("*.txt", "*.md"):
        candidates.extend(prompts_dir.glob(pattern))
    committed = prompts_dir / "committed"
    if committed.is_dir():
        for pattern in ("*.txt", "*.md"):
            candidates.extend(committed.glob(pattern))
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        raise SystemExit(
            f"Error: no prompt files found in {prompts_dir} or {prompts_dir / 'committed'}. "
            "Use --model to specify a model explicitly."
        )
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    model = _model_from_filename(latest.name)
    if not model:
        raise SystemExit(
            f"Error: could not extract model name from '{latest.name}'. "
            "Use --model to specify a model explicitly."
        )
    return model


def next_prompt_filename(prompts_dir: Path, timestamp: str, model: str) -> Path:
    pattern = f"{timestamp}-*_{model}{FILE_EXTENSION}"
    existing = [p.name for p in prompts_dir.glob(pattern) if p.is_file()]
    numbers: list[int] = []
    for name in existing:
        try:
            seq = int(name.split("-")[3])
        except (IndexError, ValueError):
            continue
        numbers.append(seq)
    next_seq = max(numbers, default=0) + 1
    return prompts_dir / f"{timestamp}-{next_seq:03d}_{model}{FILE_EXTENSION}"


def read_prompt_text(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    if not sys.stdin.isatty():
        text = sys.stdin.read()
        if text.strip():
            return text
    raise SystemExit("Error: a prompt must be provided via --prompt or stdin")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--prompt", help="The prompt text to store.")
    parser.add_argument(
        "--model",
        default=None,
        help="Model name to include in the filename (default: last used model).",
    )
    args = parser.parse_args()

    repo = common._repo_root()
    prompts_dir = repo / PROMPTS_DIR
    prompts_dir.mkdir(parents=True, exist_ok=True)

    model = args.model if args.model is not None else get_last_used_model(prompts_dir)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    prompt_text = read_prompt_text(args).rstrip("\n")
    filename = next_prompt_filename(prompts_dir, timestamp, model)
    filename.write_text(prompt_text + "\n", encoding="utf-8")
    print(filename)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
