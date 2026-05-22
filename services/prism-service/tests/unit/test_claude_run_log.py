"""claude_run_log — persistent log of PRISM-initiated `claude -p` calls.

Validates the v5.1.7 observability layer. Uses tmp_path + monkeypatched
DATA_DIR so manifest writes never touch the live /data volume.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated_runs_dir(tmp_path, monkeypatch):
    """Repoint claude_run_log at tmp_path before any module-level code
    has cached the old DATA_DIR-derived paths."""
    import app.services.claude_run_log as crl
    # The module captures _RUNS_DIR and _MANIFEST at import time from
    # DATA_DIR. Patch those module-level constants directly.
    runs_dir = tmp_path / "claude_runs"
    monkeypatch.setattr(crl, "_RUNS_DIR", runs_dir)
    monkeypatch.setattr(crl, "_MANIFEST", runs_dir / "manifest.jsonl")
    return runs_dir


def _write_stream(path: Path, blocks: list[str]) -> None:
    """Write a fake stream-json file with one or more assistant text blocks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for b in blocks:
            evt = {"message": {"content": [{"type": "text", "text": b}]}}
            fh.write(json.dumps(evt) + "\n")


def test_record_and_list_round_trip(isolated_runs_dir):
    import app.services.claude_run_log as crl

    run_id, stream_path = crl.new_run()
    _write_stream(stream_path, ["Step 1", "Final answer"])

    crl.record_run(
        run_id=run_id, stream_path=stream_path,
        ts_start=1000.0, ts_end=1005.5,
        project="proj-x", purpose="tour_builder@abcd",
        exit_code=0,
        usage={"input_tokens": 100, "output_tokens": 50},
        stderr_text="",
    )

    runs = crl.list_recent(limit=10)
    assert len(runs) == 1
    r = runs[0]
    assert r["run_id"] == run_id
    assert r["project"] == "proj-x"
    assert r["purpose"] == "tour_builder@abcd"
    assert r["exit_code"] == 0
    assert r["tokens_used"] == 150
    assert r["duration_s"] == pytest.approx(5.5)
    # Final assistant text extracted from the last text block.
    assert r["final_text"] == "Final answer"
    assert r["stream_bytes"] > 0


def test_list_recent_filters_by_project(isolated_runs_dir):
    import app.services.claude_run_log as crl

    for project in ("alpha", "beta", "alpha"):
        run_id, stream_path = crl.new_run()
        _write_stream(stream_path, [f"text for {project}"])
        crl.record_run(
            run_id=run_id, stream_path=stream_path,
            ts_start=0.0, ts_end=1.0,
            project=project, purpose="x",
            exit_code=0, usage={}, stderr_text="",
        )

    assert len(crl.list_recent(limit=10)) == 3
    assert len(crl.list_recent(limit=10, project="alpha")) == 2
    assert len(crl.list_recent(limit=10, project="never-seen")) == 0


def test_get_run_returns_full_entry(isolated_runs_dir):
    import app.services.claude_run_log as crl

    run_id, stream_path = crl.new_run()
    _write_stream(stream_path, ["only block"])
    crl.record_run(
        run_id=run_id, stream_path=stream_path,
        ts_start=0.0, ts_end=1.0,
        project="p", purpose="purp",
        exit_code=2, usage={"output_tokens": 7},
        stderr_text="bad things happened",
    )

    entry = crl.get_run(run_id)
    assert entry is not None
    assert entry["exit_code"] == 2
    assert entry["stderr_excerpt"] == "bad things happened"

    assert crl.get_run("does-not-exist") is None


def test_stream_path_for_rejects_path_traversal(isolated_runs_dir):
    import app.services.claude_run_log as crl

    assert crl.stream_path_for("") is None
    assert crl.stream_path_for("../etc/passwd") is None
    assert crl.stream_path_for("a/b") is None
    assert crl.stream_path_for("a\\b") is None


def test_trim_to_limit_drops_oldest_and_deletes_streams(isolated_runs_dir, monkeypatch):
    import app.services.claude_run_log as crl
    monkeypatch.setattr(crl, "RUN_LOG_LIMIT", 2)

    paths = []
    for i in range(4):
        run_id, stream_path = crl.new_run()
        _write_stream(stream_path, [f"text {i}"])
        paths.append(stream_path)
        crl.record_run(
            run_id=run_id, stream_path=stream_path,
            ts_start=float(i), ts_end=float(i + 1),
            project="p", purpose=f"job-{i}",
            exit_code=0, usage={}, stderr_text="",
        )

    runs = crl.list_recent(limit=10)
    assert len(runs) == 2
    # The two oldest streams should be gone from disk.
    assert not paths[0].exists()
    assert not paths[1].exists()
    # The two newest should still exist.
    assert paths[2].exists()
    assert paths[3].exists()


def test_truncates_long_final_text(isolated_runs_dir):
    import app.services.claude_run_log as crl

    run_id, stream_path = crl.new_run()
    huge = "x" * 8192
    _write_stream(stream_path, [huge])
    crl.record_run(
        run_id=run_id, stream_path=stream_path,
        ts_start=0.0, ts_end=1.0,
        project="p", purpose="x",
        exit_code=0, usage={}, stderr_text="",
    )

    entry = crl.get_run(run_id)
    assert entry is not None
    # 4 KB cap from _FINAL_TEXT_MAX.
    assert len(entry["final_text"]) <= 4096
    assert entry["final_text"].endswith("…")


def test_record_run_failure_does_not_raise(isolated_runs_dir, monkeypatch):
    """A bad manifest path must not break the analyzer pipeline."""
    import app.services.claude_run_log as crl
    # Make _MANIFEST point at something that can't be opened in append
    # mode (a directory) — record_run should swallow the OSError.
    bad = isolated_runs_dir / "is_a_dir"
    bad.mkdir(parents=True)
    monkeypatch.setattr(crl, "_MANIFEST", bad)

    # Should not raise.
    crl.record_run(
        run_id="x", stream_path=isolated_runs_dir / "missing.jsonl",
        ts_start=0.0, ts_end=1.0,
        project="p", purpose="x",
        exit_code=0, usage={}, stderr_text="",
    )
