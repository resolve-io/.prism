#!/usr/bin/env python3
"""
Unit tests for plugins/prism-devtools/skills/remember/scripts/remember.py.

Tests:
- classify_domain(): keyword-based domain inference
- classify_type(): keyword-based type inference
- main(): argument handling, subprocess invocation, error cases
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the remember script directory to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "skills" / "remember" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from remember import classify_domain, classify_type, main


# ---------------------------------------------------------------------------
# classify_domain() tests
# ---------------------------------------------------------------------------

def test_domain_classification_hooks():
    assert classify_domain("stop hook wraps DB in try/except") == "hooks"


def test_domain_classification_hooks_posttooluse():
    assert classify_domain("posttooluse fires on every edit") == "hooks"


def test_domain_classification_brain():
    assert classify_domain("brain scores.db needs new table") == "brain"


def test_domain_classification_brain_vector():
    assert classify_domain("vector search returns ranked results") == "brain"


def test_domain_classification_cli():
    assert classify_domain("snapshot header shows version") == "cli"


def test_domain_classification_cli_tui():
    assert classify_domain("tui renders the workflow table") == "cli"


def test_domain_classification_conductor():
    assert classify_domain("conductor uses epsilon-greedy selection") == "conductor"


def test_domain_classification_byos():
    assert classify_domain("SKILL.md must have imperative instruction") == "byos"


def test_domain_classification_platform():
    assert classify_domain("wsl requires python3 not python") == "platform"


def test_domain_classification_platform_windows():
    assert classify_domain("windows path separators differ from linux") == "platform"


def test_domain_classification_default():
    assert classify_domain("some random observation") == "general"


# ---------------------------------------------------------------------------
# classify_type() tests
# ---------------------------------------------------------------------------

def test_type_classification_convention():
    assert classify_type("always use python3 not python") == "convention"


def test_type_classification_convention_never():
    assert classify_type("never import from the parent package directly") == "convention"


def test_type_classification_convention_must():
    assert classify_type("scripts must handle missing files gracefully") == "convention"


def test_type_classification_pattern():
    assert classify_type("pattern for atomic file writes using temp files") == "pattern"


def test_type_classification_pattern_approach():
    assert classify_type("approach to epsilon-greedy prompt selection") == "pattern"


def test_type_classification_failure():
    assert classify_type("hook crashed with ImportError on missing dependency") == "failure"


def test_type_classification_failure_broke():
    assert classify_type("sqlite connection broke after concurrent writes") == "failure"


def test_type_classification_failure_bug():
    assert classify_type("bug in state file regex parser") == "failure"


def test_type_classification_decision():
    assert classify_type("decided to use sqlite not json for persistence") == "decision"


def test_type_classification_decision_chose():
    assert classify_type("chose WAL mode because it allows concurrent reads") == "decision"


def test_type_classification_default():
    assert classify_type("interesting thing about the code") == "pattern"


# ---------------------------------------------------------------------------
# main() tests
# ---------------------------------------------------------------------------

def test_no_args_exits_with_error():
    result = main([])
    assert result == 1


def test_script_calls_mulch_record():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "recorded mx-abc123\n"
    mock_result.stderr = ""

    with patch("remember.subprocess.run", return_value=mock_result) as mock_run:
        exit_code = main(["stop hook wraps DB in try/except"])

    assert exit_code == 0
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]  # first positional arg is the cmd list
    assert call_args[0] == "ml"
    assert call_args[1] == "record"
    assert call_args[2] == "hooks"  # domain inferred from "hook"
    assert "--type" in call_args
    assert "pattern" in call_args  # no convention keywords in input -> default type is "pattern"


def test_script_calls_mulch_record_correct_type():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("remember.subprocess.run", return_value=mock_result) as mock_run:
        exit_code = main(["always use python3 not python on wsl"])

    assert exit_code == 0
    call_args = mock_run.call_args[0][0]
    assert "platform" in call_args   # domain from "wsl"
    assert "convention" in call_args  # type from "always"
    assert "--classification" in call_args
    assert "tactical" in call_args


def test_mulch_not_found_exits_with_error(capsys):
    with patch("remember.subprocess.run", side_effect=FileNotFoundError):
        exit_code = main(["some observation"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "mulch" in captured.err.lower() or "ml" in captured.err


def test_mulch_record_failure_propagates_exit_code(capsys):
    mock_result = MagicMock()
    mock_result.returncode = 2
    mock_result.stdout = ""
    mock_result.stderr = "Error: domain 'bad' not found"

    with patch("remember.subprocess.run", return_value=mock_result):
        exit_code = main(["some observation"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "domain" in captured.err


def test_observation_joined_correctly():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch("remember.subprocess.run", return_value=mock_result) as mock_run:
        main(["brain", "auto-bootstraps", "when", "docs", "table", "is", "empty"])

    call_args = mock_run.call_args[0][0]
    assert "brain auto-bootstraps when docs table is empty" in call_args
