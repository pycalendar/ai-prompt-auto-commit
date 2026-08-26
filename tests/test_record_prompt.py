"""Tests for the bundled UserPromptSubmit hook script (data/record_prompt.py).

The script is installed into a target repository as
`.claude/hooks/record-prompt.py`, so it is loaded here straight from the
package data directory rather than imported as a module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

from ai_prompt_auto_commit.prepare_repository import HOOK_SCRIPT_DATA, get_data_path


@pytest.fixture(scope="module")
def hook() -> types.ModuleType:
    """The bundled hook script, loaded as a module."""
    path = get_data_path(HOOK_SCRIPT_DATA)
    spec = importlib.util.spec_from_file_location("_record_prompt_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _payload(**overrides: object) -> dict:
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "why does the redirect fail?",
        "source": "user",
        "cwd": ".",
        "transcript_path": "",
    }
    payload.update(overrides)
    return payload


def _transcript(path: Path, entries: list[dict]) -> Path:
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")
    return path


def _assistant(model: str, **extra: object) -> dict:
    return {"type": "assistant", "message": {"model": model}, **extra}


# ---------------------------------------------------------------------------
# should_record — only genuine user-authored turns
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source", ["user", "sdk"])
def test_human_sources_are_recorded(hook, source: str) -> None:
    assert hook.should_record(_payload(source=source))


@pytest.mark.parametrize("source", ["system", "loop_wakeup", "schedule_wakeup", "poll_event"])
def test_machine_injected_sources_are_dropped(hook, source: str) -> None:
    assert not hook.should_record(_payload(source=source))


def test_missing_source_defaults_to_recording(hook) -> None:
    payload = _payload()
    del payload["source"]
    assert hook.should_record(payload)


@pytest.mark.parametrize("prompt", [
    "<task-notification>\n<task-id>b7cljujii</task-id>\n</task-notification>",
    "<bash-input>pytest -k compat</bash-input>",
    "<bash-stdout>Command did not complete within its 120s timeout</bash-stdout>",
    "<local-command-caveat>Caveat: The messages below were generated</local-command-caveat>",
    "<system-reminder>background context</system-reminder>",
])
def test_synthetic_turns_dropped_even_without_source(hook, prompt: str) -> None:
    payload = _payload(prompt=prompt)
    del payload["source"]
    assert not hook.should_record(payload)


@pytest.mark.parametrize("prompt", ["", "   \n  "])
def test_empty_prompt_is_dropped(hook, prompt: str) -> None:
    assert not hook.should_record(_payload(prompt=prompt))


def test_slash_command_is_a_real_prompt(hook) -> None:
    assert hook.should_record(_payload(prompt="/review-and-push"))


# ---------------------------------------------------------------------------
# model_from_transcript — read the model, never guess it
# ---------------------------------------------------------------------------

def test_model_is_last_assistant_model(hook, tmp_path: Path) -> None:
    t = _transcript(tmp_path / "t.jsonl", [
        {"type": "user", "message": {"content": "hi"}},
        _assistant("claude-sonnet-4-6"),
        _assistant("claude-opus-5"),
    ])
    assert hook.model_from_transcript(str(t)) == "claude-opus-5"


def test_sidechain_model_is_ignored(hook, tmp_path: Path) -> None:
    """A subagent's model must not be attributed to the user's prompt."""
    t = _transcript(tmp_path / "t.jsonl", [
        _assistant("claude-opus-5"),
        _assistant("claude-haiku-4-5-20251001", isSidechain=True),
    ])
    assert hook.model_from_transcript(str(t)) == "claude-opus-5"


def test_synthetic_model_is_ignored(hook, tmp_path: Path) -> None:
    t = _transcript(tmp_path / "t.jsonl", [
        _assistant("claude-opus-5"),
        _assistant("<synthetic>"),
    ])
    assert hook.model_from_transcript(str(t)) == "claude-opus-5"


def test_malformed_lines_are_tolerated(hook, tmp_path: Path) -> None:
    t = tmp_path / "t.jsonl"
    t.write_text('not json\n{"type": "assistant", "message": {"model": "m-1"}}\n{\n', encoding="utf-8")
    assert hook.model_from_transcript(str(t)) == "m-1"


@pytest.mark.parametrize("path", ["", "/nonexistent/transcript.jsonl"])
def test_unreadable_transcript_yields_unknown(hook, path: str) -> None:
    assert hook.model_from_transcript(path) == hook.UNKNOWN_MODEL


def test_transcript_without_assistant_turns_yields_unknown(hook, tmp_path: Path) -> None:
    """The first prompt of a session: no assistant has spoken yet."""
    t = _transcript(tmp_path / "t.jsonl", [
        {"type": "mode", "mode": "normal"},
        {"type": "user", "message": {"content": "hi"}},
    ])
    assert hook.model_from_transcript(str(t)) == hook.UNKNOWN_MODEL


def test_model_found_beyond_the_tail_window(hook, tmp_path: Path) -> None:
    """Only the tail is read normally; a far-away model must still be found."""
    padding = [{"type": "user", "message": {"content": "x" * 4096}}] * 512
    t = _transcript(tmp_path / "t.jsonl", [_assistant("claude-opus-5")] + padding)
    assert t.stat().st_size > hook.TAIL_BYTES
    assert hook.model_from_transcript(str(t)) == "claude-opus-5"


# ---------------------------------------------------------------------------
# record() — file naming and content
# ---------------------------------------------------------------------------

def test_prompt_written_with_model_from_transcript(hook, tmp_path: Path) -> None:
    t = _transcript(tmp_path / "t.jsonl", [_assistant("claude-opus-5")])
    dest = hook.record(_payload(cwd=str(tmp_path), transcript_path=str(t)))
    assert dest is not None
    assert dest.parent == tmp_path / ".prompts"
    assert dest.name.endswith("_claude-opus-5.txt")
    assert dest.read_text(encoding="utf-8") == "why does the redirect fail?\n"


def test_machine_injected_turn_writes_nothing(hook, tmp_path: Path) -> None:
    assert hook.record(_payload(cwd=str(tmp_path), source="system")) is None
    assert not (tmp_path / ".prompts").exists()


def test_second_prompt_in_the_same_second_is_not_overwritten(hook, tmp_path: Path) -> None:
    payload = _payload(cwd=str(tmp_path))
    first = hook.record(payload)
    second = hook.record(dict(payload, prompt="and now?"))
    assert first != second
    assert first.read_text(encoding="utf-8") == "why does the redirect fail?\n"
    assert second.read_text(encoding="utf-8") == "and now?\n"


# ---------------------------------------------------------------------------
# main() — the actual hook contract: JSON on stdin, nothing on stdout
# ---------------------------------------------------------------------------

def _run_hook(payload: dict, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(get_data_path(HOOK_SCRIPT_DATA))],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_hook_writes_nothing_to_stdout(tmp_path: Path) -> None:
    """UserPromptSubmit stdout is injected into the prompt as context."""
    result = _run_hook(_payload(cwd=str(tmp_path)), tmp_path)
    assert result.stdout == ""
    assert result.returncode == 0
    assert len(list((tmp_path / ".prompts").glob("*.txt"))) == 1


def test_hook_survives_garbage_on_stdin(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(get_data_path(HOOK_SCRIPT_DATA))],
        input="not json at all",
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# never lose a prompt: the hook must fail soft, whatever goes wrong
# ---------------------------------------------------------------------------

def test_hook_command_exits_zero_when_the_script_is_missing(tmp_path: Path) -> None:
    """Claude Code erases the prompt on exit 2, which python3 returns for a
    missing file. A repository whose script was never installed must degrade
    to not recording, not to swallowing what the user typed."""
    from ai_prompt_auto_commit.prepare_repository import get_default_claude_settings

    command = get_default_claude_settings()["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    result = subprocess.run(
        ["sh", "-c", command],
        input=json.dumps(_payload()),
        capture_output=True,
        text=True,
        cwd=tmp_path,  # no .claude/hooks/record-prompt.py here
        env={"PATH": os.environ["PATH"]},
    )
    assert result.returncode == 0, result.stderr


def test_unreadable_transcript_yields_unknown_not_a_crash(hook, tmp_path: Path) -> None:
    t = _transcript(tmp_path / "t.jsonl", [_assistant("claude-opus-5")])
    t.chmod(0o000)
    try:
        assert hook.model_from_transcript(str(t)) == hook.UNKNOWN_MODEL
    finally:
        t.chmod(0o600)


def test_prompt_still_recorded_when_the_transcript_is_unreadable(hook, tmp_path: Path) -> None:
    t = _transcript(tmp_path / "t.jsonl", [_assistant("claude-opus-5")])
    t.chmod(0o000)
    try:
        dest = hook.record(_payload(cwd=str(tmp_path), transcript_path=str(t)))
    finally:
        t.chmod(0o600)
    assert dest is not None and dest.name.endswith(f"_{hook.UNKNOWN_MODEL}.txt")


def test_non_utf8_locale_still_records_the_prompt(tmp_path: Path) -> None:
    """The payload is always UTF-8 JSON; the locale must not get a say."""
    env = dict(os.environ, LC_ALL="C", LANG="C", PYTHONIOENCODING="", PYTHONUTF8="0")
    env.pop("PYTHONIOENCODING")
    result = subprocess.run(
        [sys.executable, str(get_data_path(HOOK_SCRIPT_DATA))],
        input=json.dumps(_payload(prompt="hvorfor feiler kalenderoppslaget?"), ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        cwd=tmp_path,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    written = list((tmp_path / ".prompts").glob("*.txt"))
    assert len(written) == 1
    assert written[0].read_text(encoding="utf-8") == "hvorfor feiler kalenderoppslaget?\n"


@pytest.mark.parametrize("model, expected", [
    ("anthropic/claude-opus-5", "anthropic-claude-opus-5"),
    ("some_model", "some-model"),          # `_` separates timestamp from model
    ("../../escape", "escape"),
])
def test_model_name_is_made_safe_for_a_filename(hook, tmp_path: Path, model: str, expected: str) -> None:
    t = _transcript(tmp_path / "t.jsonl", [_assistant(model)])
    dest = hook.record(_payload(cwd=str(tmp_path), transcript_path=str(t)))
    assert dest is not None
    assert dest.parent == tmp_path / ".prompts"
    assert dest.name.endswith(f"_{expected}.txt")


def test_missing_cwd_records_nowhere_at_all(hook, tmp_path: Path) -> None:
    """Not merely "does not create the missing tree": falling back to the
    process cwd files the prompt under whatever repository the hook happened
    to be run from."""
    gone = tmp_path / "deleted" / "deeply"
    before = sorted(Path.cwd().rglob(".prompts/*.txt"))
    assert hook.record(_payload(cwd=str(gone))) is None
    assert not gone.exists()
    assert sorted(Path.cwd().rglob(".prompts/*.txt")) == before
