"""Tests for _read_live_tokens in app.py.

Verifies that the TUI correctly reads tokens and model from transcript,
handles non-dict JSON entries, and that _poll_state continues even when
_read_live_tokens raises.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the prism-cli package to sys.path
_CLI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_CLI_DIR))

from models import WorkflowState

# Transcript fixture: user message (no usage), two assistant messages with usage,
# and a non-dict JSON line (42) that must be skipped gracefully.
TRANSCRIPT_LINES = [
    '{"type":"user","message":{"role":"user","content":"hello"}}\n',
    '{"type":"assistant","message":{"model":"claude-opus-4-6","usage":{"input_tokens":100,"cache_creation_input_tokens":500,"cache_read_input_tokens":0,"output_tokens":50}}}\n',
    "42\n",
    '{"type":"assistant","message":{"model":"claude-opus-4-6","usage":{"input_tokens":200,"cache_creation_input_tokens":0,"cache_read_input_tokens":300,"output_tokens":75}}}\n',
]
# Expected total: 100+500+0+50 + 200+0+300+75 = 1225


def _make_app(tmp_path: Path) -> object:
    """Create a PrismDashboard instance without starting Textual."""
    from app import PrismDashboard

    return PrismDashboard(path=tmp_path)


def _make_state(session_id: str = "test-session-id") -> WorkflowState:
    return WorkflowState(active=True, session_id=session_id)


def _write_transcript(tmp_path: Path, session_id: str, lines: list[str]) -> Path:
    projects = tmp_path / ".claude" / "projects" / "proj"
    projects.mkdir(parents=True)
    tp = projects / f"{session_id}.jsonl"
    tp.write_text("".join(lines), encoding="utf-8")
    return tp


class TestReadLiveTokensPopulatesState:
    """Happy-path: tokens and model are extracted from a valid transcript."""

    def test_populates_total_tokens(self, tmp_path: Path):
        session_id = "happy-session"
        tp = _write_transcript(tmp_path, session_id, TRANSCRIPT_LINES)
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        assert state.total_tokens == 1225

    def test_sets_model(self, tmp_path: Path):
        session_id = "model-session"
        tp = _write_transcript(tmp_path, session_id, TRANSCRIPT_LINES)
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        assert state.model == "claude-opus-4-6"


class TestReadLiveTokensEdgeCases:
    """Edge-case resilience."""

    def test_skips_non_dict_entries(self, tmp_path: Path):
        """Line '42' (integer JSON) must not crash the reader."""
        session_id = "nondict-session"
        tp = _write_transcript(tmp_path, session_id, TRANSCRIPT_LINES)
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        # Must have read ALL lines including past the non-dict entry
        assert state.total_tokens == 1225

    def test_handles_empty_transcript(self, tmp_path: Path):
        session_id = "empty-session"
        tp = _write_transcript(tmp_path, session_id, [])
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        assert state.total_tokens == 0
        assert state.model == ""

    def test_handles_none_token_values(self, tmp_path: Path):
        """Token values explicitly set to null in JSON must not raise TypeError."""
        lines = [
            '{"type":"assistant","message":{"model":"claude-opus-4-6","usage":{"input_tokens":null,"output_tokens":50}}}\n',
        ]
        session_id = "null-tokens-session"
        tp = _write_transcript(tmp_path, session_id, lines)
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        assert state.total_tokens == 50

    def test_handles_missing_transcript(self, tmp_path: Path):
        """When glob returns no matches, state is unchanged."""
        app = _make_app(tmp_path)
        state = _make_state("no-file-session")

        with patch("app._glob.glob", return_value=[]):
            app._read_live_tokens(state)

        assert state.total_tokens == 0


class TestReadLiveTokensIncremental:
    """Incremental reading: second call reads only new lines."""

    def test_incremental_reading(self, tmp_path: Path):
        session_id = "incr-session"
        # Write first two assistant lines
        first_batch = TRANSCRIPT_LINES[:2]
        tp = _write_transcript(tmp_path, session_id, first_batch)
        app = _make_app(tmp_path)
        state = _make_state(session_id)

        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        tokens_after_first = state.total_tokens
        assert tokens_after_first == 650  # 100+500+0+50

        # Append remaining lines
        with open(tp, "a", encoding="utf-8") as f:
            f.writelines(TRANSCRIPT_LINES[2:])

        # Second call — should read only new content
        with patch("app._glob.glob", return_value=[str(tp)]):
            app._read_live_tokens(state)

        assert state.total_tokens == 1225


class TestPollStateContinuesAfterTokenError:
    """_poll_state must not skip mutate_reactive if _read_live_tokens raises."""

    def test_widget_updates_not_blocked_by_token_error(self, tmp_path: Path):
        from app import PrismDashboard

        app = _make_app(tmp_path)

        # Patch _read_live_tokens to raise an unexpected exception
        def _raise(*args, **kwargs):
            raise RuntimeError("simulated token read failure")

        app._read_live_tokens = _raise

        # Patch out Textual internals so _poll_state can run in isolation
        from textual.css.query import NoMatches

        app.mutate_reactive = MagicMock()
        app.query_one = MagicMock(side_effect=NoMatches())

        # Create a minimal state file so _poll_state doesn't crash on parse
        state_dir = tmp_path / ".claude"
        state_dir.mkdir()
        (state_dir / "prism-loop.local.md").write_text(
            "---\nactive: true\nsession_id: err-session\n---\n",
            encoding="utf-8",
        )
        app._state_file = state_dir / "prism-loop.local.md"
        app._work_dir = tmp_path

        app._poll_state()

        # mutate_reactive must have been called despite the token error
        app.mutate_reactive.assert_called_once()
