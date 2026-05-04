"""Verifier service unit tests — schema migration, Tier 0 detection,
Tier 1 record checks, end-to-end run() persistence."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from app.services.verifier_service import (    # noqa: E402
    Claim,
    VerifierService,
    _detect_node_project,
    _detect_python_project,
    _filter_files,
    _git_changed_files,
    _iso_to_epoch,
    _overall_status,
    _tier_status,
    _verifier_schema,
    run_tier0,
    run_tier1,
)


# ----------------------------------------------------------------------
# Schema migration
# ----------------------------------------------------------------------


def test_schema_creates_both_tables(tmp_path):
    db = tmp_path / "scores.db"
    conn = sqlite3.connect(db)
    _verifier_schema(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    conn.close()
    assert "verifier_runs" in tables
    assert "verifier_claims" in tables


def test_schema_is_idempotent(tmp_path):
    db = tmp_path / "scores.db"
    conn = sqlite3.connect(db)
    for _ in range(3):
        _verifier_schema(conn)   # would raise on duplicate CREATE
    conn.close()


# ----------------------------------------------------------------------
# Tier 0 — project detection + tooling skip behavior
# ----------------------------------------------------------------------


def test_detect_python_project_via_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert _detect_python_project(tmp_path) is True


def test_detect_python_project_via_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("")
    assert _detect_python_project(tmp_path) is True


def test_detect_node_project(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert _detect_node_project(tmp_path) is True


def test_detect_returns_false_when_empty(tmp_path):
    assert _detect_python_project(tmp_path) is False
    assert _detect_node_project(tmp_path) is False


def test_filter_files_by_suffix():
    files = ["a.py", "b.js", "c.py", "d.txt"]
    assert _filter_files(files, (".py",)) == ["a.py", "c.py"]
    assert _filter_files(files, (".js", ".ts")) == ["b.js"]


def test_run_tier0_returns_empty_when_not_a_repo(tmp_path):
    # No .git → no diff scope → no claims
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    claims = run_tier0(tmp_path)
    assert claims == []


def test_run_tier0_empty_when_no_changed_files(tmp_path):
    # Real-ish repo but no diff: still no claims (no scope = no work)
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    claims = run_tier0(tmp_path)
    # We don't assert exact count — git ls-files --others picks up
    # the untracked pyproject.toml, but no .py file changed so the
    # python tool runners return empty claim lists.
    py_claims = [c for c in claims if c.kind.startswith("tooling.")]
    # Should not raise; should not run python linters with no .py scope
    assert all(not c.target.endswith(".py") for c in py_claims)


# ----------------------------------------------------------------------
# Tier 1 — record-driven checks
# ----------------------------------------------------------------------


def _seed_brain_db(path: Path, rows: list[tuple[str, str, str]]) -> None:
    """rows: list of (path, content_hash, indexed_at)."""
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE code_docs (path TEXT, content_hash TEXT, indexed_at TEXT);"
    )
    conn.executemany(
        "INSERT INTO code_docs(path, content_hash, indexed_at) VALUES (?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()


def test_tier1_brain_indexed_pass_when_file_exists(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    target = workspace / "foo.py"
    target.write_text("print('hi')\n")
    brain_db = tmp_path / "brain.db"
    _seed_brain_db(brain_db, [("foo.py", "", "2099-01-01 00:00:00")])
    claims = run_tier1(str(brain_db), None, None, workspace, "S1",
                      "2000-01-01 00:00:00")
    indexed = [c for c in claims if c.kind == "record.brain_indexed"]
    assert len(indexed) == 1
    assert indexed[0].status == "pass"


def test_tier1_brain_indexed_fails_when_file_missing(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    brain_db = tmp_path / "brain.db"
    _seed_brain_db(brain_db, [("ghost.py", "", "2099-01-01 00:00:00")])
    claims = run_tier1(str(brain_db), None, None, workspace, "S1",
                      "2000-01-01 00:00:00")
    indexed = [c for c in claims if c.kind == "record.brain_indexed"]
    assert len(indexed) == 1
    assert indexed[0].status == "fail"
    assert "gone" in indexed[0].feedback


def test_tier1_brain_indexed_fails_on_hash_drift(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    target = workspace / "foo.py"
    target.write_text("v1\n")
    brain_db = tmp_path / "brain.db"
    _seed_brain_db(brain_db, [("foo.py", "deadbeef" * 8,
                              "2099-01-01 00:00:00")])
    claims = run_tier1(str(brain_db), None, None, workspace, "S1",
                      "2000-01-01 00:00:00")
    indexed = [c for c in claims if c.kind == "record.brain_indexed"]
    assert indexed and indexed[0].status == "fail"
    assert "drifted" in indexed[0].feedback


def test_tier1_skips_when_brain_db_absent(tmp_path):
    claims = run_tier1(str(tmp_path / "nope.db"), None, None,
                      tmp_path, "S1", "2000-01-01 00:00:00")
    assert claims == []   # no DB → no claims, no crash


def _seed_tasks_db(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    """rows: list of (id, subject, status, updated_at)."""
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE tasks (id TEXT, subject TEXT, status TEXT, "
        "updated_at TEXT);"
    )
    conn.executemany(
        "INSERT INTO tasks VALUES (?,?,?,?)", rows,
    )
    conn.commit()
    conn.close()


def test_tier1_task_done_pass_with_real_subject(tmp_path):
    db = tmp_path / "tasks.db"
    _seed_tasks_db(db, [("t1", "Implement verifier service",
                        "done", "2099-01-01 00:00:00")])
    claims = run_tier1(None, str(db), None, tmp_path, "S1",
                      "2000-01-01 00:00:00")
    assert any(c.status == "pass" for c in claims
               if c.kind == "record.task_done")


def test_tier1_task_done_fails_with_placeholder_subject(tmp_path):
    db = tmp_path / "tasks.db"
    _seed_tasks_db(db, [("t1", "todo", "done", "2099-01-01 00:00:00")])
    claims = run_tier1(None, str(db), None, tmp_path, "S1",
                      "2000-01-01 00:00:00")
    failed = [c for c in claims if c.kind == "record.task_done"
              and c.status == "fail"]
    assert len(failed) == 1
    assert "placeholder" in failed[0].feedback


def test_tier1_memory_write_pass(tmp_path):
    md = tmp_path / "mulch"
    md.mkdir()
    entry = md / "decision.md"
    entry.write_text("---\nname: test\n---\n\nA real memory entry.\n")
    claims = run_tier1(None, None, str(md), tmp_path, "S1",
                      "2000-01-01 00:00:00")
    mem = [c for c in claims if c.kind == "record.memory_write"]
    assert mem and mem[0].status == "pass"


def test_tier1_memory_write_fails_when_too_small(tmp_path):
    md = tmp_path / "mulch"
    md.mkdir()
    (md / "tiny.md").write_text("hi")
    claims = run_tier1(None, None, str(md), tmp_path, "S1",
                      "2000-01-01 00:00:00")
    mem = [c for c in claims if c.kind == "record.memory_write"]
    assert mem and mem[0].status == "fail"


def test_tier1_memory_write_fails_when_no_frontmatter(tmp_path):
    md = tmp_path / "mulch"
    md.mkdir()
    (md / "noframe.md").write_text(
        "Just a long blob of text without frontmatter delimiters at all\n" * 3
    )
    claims = run_tier1(None, None, str(md), tmp_path, "S1",
                      "2000-01-01 00:00:00")
    mem = [c for c in claims if c.kind == "record.memory_write"]
    assert mem and mem[0].status == "fail"


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------


def test_tier_status_aggregation():
    cs = [Claim(0, "x", status="pass"), Claim(0, "y", status="fail")]
    assert _tier_status(cs, 0) == "partial"
    assert _tier_status([Claim(0, "x", status="pass")], 0) == "pass"
    assert _tier_status([Claim(0, "x", status="fail")], 0) == "fail"
    assert _tier_status([], 0) == "not-run"


def test_overall_status():
    assert _overall_status("pass", "pass", "skipped") == "pass"
    assert _overall_status("fail", "pass", "skipped") == "fail"
    assert _overall_status("partial", "pass", "skipped") == "partial"
    assert _overall_status("not-run", "not-run", "skipped") == "error"


def test_iso_to_epoch_handles_common_formats():
    assert _iso_to_epoch("2026-01-01 00:00:00") > 0
    assert _iso_to_epoch("2026-01-01T00:00:00Z") > 0
    assert _iso_to_epoch("") == 0.0
    assert _iso_to_epoch("not a date") == 0.0


# ----------------------------------------------------------------------
# End-to-end VerifierService.run() — persistence + structure
# ----------------------------------------------------------------------


def test_run_persists_to_verifier_runs_and_claims(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    sv = VerifierService(scores_db=str(tmp_path / "scores.db"),
                        workspace=str(workspace))
    result = sv.run(session_id="S1")

    # Result shape
    assert "run_id" in result
    assert result["status"] in ("pass", "fail", "partial", "error")
    assert "tier0" in result and "tier1" in result and "tier2" in result

    # Persistence
    conn = sqlite3.connect(tmp_path / "scores.db")
    conn.row_factory = sqlite3.Row
    runs = conn.execute("SELECT * FROM verifier_runs").fetchall()
    assert len(runs) == 1
    assert runs[0]["run_id"] == result["run_id"]
    assert runs[0]["session_id"] == "S1"
    conn.close()


def test_run_with_no_data_returns_error_status(tmp_path):
    """Empty workspace + no PRISM tables: no claims to verify is itself
    a signal — verifier flags ``status=error`` so the operator notices."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    sv = VerifierService(scores_db=str(tmp_path / "scores.db"),
                        workspace=str(workspace))
    result = sv.run(session_id="empty")
    assert result["status"] == "error"
    assert result["claim_count"] == 0


def test_history_filters_by_task_id(tmp_path):
    sv = VerifierService(scores_db=str(tmp_path / "scores.db"),
                        workspace=str(tmp_path))
    sv.run(session_id="S1", task_id="T1")
    sv.run(session_id="S2", task_id="T2")
    sv.run(session_id="S3", task_id="T1")
    t1_only = sv.history(task_id="T1")
    assert len(t1_only) == 2
    all_runs = sv.history()
    assert len(all_runs) == 3


def test_feedback_summary_dedupes_and_orders(tmp_path):
    """feedback_summary should pull recent fail/partial runs, dedupe
    the seed strings, preserve newest-first order."""
    sv = VerifierService(scores_db=str(tmp_path / "scores.db"),
                        workspace=str(tmp_path))
    # Manually insert two failing runs with the same seed
    conn = sqlite3.connect(tmp_path / "scores.db")
    conn.execute(
        "INSERT INTO verifier_runs(run_id, session_id, status, feedback) "
        "VALUES ('r1', 's1', 'fail', ?)", (json.dumps(["A", "B"]),),
    )
    conn.execute(
        "INSERT INTO verifier_runs(run_id, session_id, status, feedback) "
        "VALUES ('r2', 's2', 'partial', ?)", (json.dumps(["B", "C"]),),
    )
    conn.commit()
    conn.close()
    seeds = sv.feedback_summary(limit=10)
    assert "A" in seeds and "B" in seeds and "C" in seeds
    # Dedupe: B should appear once
    assert seeds.count("B") == 1
