#!/usr/bin/env python3
"""PRISM Service — Brain, Memory, Tasks, Workflow with web UI and MCP."""

import threading

from nicegui import ui, app

from app.config import (DATA_DIR, PROJECT_DIR, PROJECTS_DIR,
                         UI_PORT, MCP_PORT, GOVERNANCE_INTERVAL_SECONDS,
                         DRIFT_INTERVAL_SECONDS, QUALITY_INTERVAL_SECONDS)

# Ensure base directories exist
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def start_mcp_server():
    """Start MCP server in background thread."""
    from app.mcp.server import run_mcp_server
    run_mcp_server(MCP_PORT)


def start_governance_timer():
    """Run governance cycles for all active projects periodically."""
    import time
    from app.project_context import get_project, get_all_projects
    while True:
        try:
            for pid in get_all_projects():
                try:
                    ctx = get_project(pid)
                    ctx.governance.run_cycle()
                except Exception as e:
                    print(f"Governance cycle error ({pid}): {e}")
        except Exception as e:
            print(f"Governance timer error: {e}")
        time.sleep(GOVERNANCE_INTERVAL_SECONDS)


def start_drift_timer():
    """Walk every project, reindex drifted docs on a cadence.

    ``prism_status`` already exposes drift; this loop acts on it. Any
    project whose Brain.incremental_reindex returns >0 gets its
    reindexed count logged so ops can see the loop is earning its keep.
    PRISM_DRIFT_INTERVAL=0 disables entirely.

    Per project we keep a *dedicated* Brain instance with its own
    SQLite connections, distinct from the BrainService that request
    handlers use. Reindex writes can take seconds (embedding compute +
    FTS insert + graph mutate) and SQLite serializes operations on a
    single connection's mutex; sharing connections with the request
    path produced the customer hang in issue #38 — every MCP worker
    parked behind the drift thread's open transaction.
    """
    import sys as _sys
    import time
    if DRIFT_INTERVAL_SECONDS <= 0:
        print("Drift timer disabled (PRISM_DRIFT_INTERVAL=0)",
              file=_sys.stderr)
        return
    from app.project_context import get_project, get_all_projects
    from app.engines.brain_engine import Brain
    print(
        f"Drift timer running every {DRIFT_INTERVAL_SECONDS}s",
        file=_sys.stderr,
    )
    drift_brains: dict[str, Brain] = {}
    while True:
        try:
            for pid in get_all_projects():
                try:
                    ctx = get_project(pid)
                    db_dir = ctx._data_dir
                    brain = drift_brains.get(pid)
                    if brain is None:
                        brain = Brain(
                            brain_db=str(db_dir / "brain.db"),
                            graph_db=str(db_dir / "graph.db"),
                            scores_db=str(db_dir / "scores.db"),
                            tasks_db=str(db_dir / "tasks.db"),
                        )
                        drift_brains[pid] = brain
                    n = brain.incremental_reindex()
                    if n:
                        print(
                            f"[drift] {pid}: reindexed {n} drifted file(s)",
                            file=_sys.stderr,
                        )
                except Exception as e:
                    print(f"Drift cycle error ({pid}): {e}",
                          file=_sys.stderr)
        except Exception as e:
            print(f"Drift timer error: {e}", file=_sys.stderr)
        time.sleep(DRIFT_INTERVAL_SECONDS)


def start_quality_timer():
    """Score merged tasks against git truth on a cadence (LL-04).

    Walks every project, calls ``score_merged_tasks`` so any task that
    landed on main in the last 14 days gets a composite Layer-A quality
    score written to ``task_quality_rollup``. PRISM_QUALITY_INTERVAL=0
    disables entirely.
    """
    import sys as _sys
    import time
    if QUALITY_INTERVAL_SECONDS <= 0:
        print("Quality timer disabled (PRISM_QUALITY_INTERVAL=0)",
              file=_sys.stderr)
        return
    from app.project_context import get_project, get_all_projects
    from app.services.scoring_service import score_merged_tasks
    print(
        f"Quality timer running every {QUALITY_INTERVAL_SECONDS}s",
        file=_sys.stderr,
    )
    while True:
        try:
            for pid in get_all_projects():
                try:
                    ctx = get_project(pid)
                    scored = score_merged_tasks(
                        tasks_svc=ctx.task_svc,
                        scores_db=str(ctx._data_dir / "scores.db"),
                        repo_path=str(PROJECT_DIR),
                    )
                    if scored:
                        print(
                            f"[quality] {pid}: scored {len(scored)} merged "
                            f"task(s)",
                            file=_sys.stderr,
                        )
                except Exception as e:
                    print(f"Quality cycle error ({pid}): {e}",
                          file=_sys.stderr)
        except Exception as e:
            print(f"Quality timer error: {e}", file=_sys.stderr)
        time.sleep(QUALITY_INTERVAL_SECONDS)


# Import UI pages (they register routes with NiceGUI)
from app.ui import (
    dashboard, brain_page, graph_page, memory_page,
    tasks_page, conductor_page, sessions_page, retrievals_page,
    learning_page, consolidation_page,
    sse,  # /sse/sessions endpoint
)

# Guard against double-start using file lock
_LOCK_FILE = DATA_DIR / ".mcp_started"


def _install_stackdump_handler() -> None:
    """Dump every thread's stack to stderr on SIGUSR1.

    Lets operators capture what workers are blocked on without having
    to ``docker exec`` the container and run py-spy. Requested in
    issue #38 — the customer hung with all threads parked on a SQLite
    mutex and there was no way to confirm without external tooling.
    """
    import signal
    import sys as _sys
    import traceback

    if not hasattr(signal, "SIGUSR1"):
        # Windows / non-POSIX — silently skip.
        return

    def _dump(_signum, _frame):
        frames = _sys._current_frames()
        out = [f"=== thread stack dump ({len(frames)} threads) ==="]
        thread_names = {t.ident: t.name for t in threading.enumerate()}
        for tid, frame in frames.items():
            name = thread_names.get(tid, "?")
            out.append(f"\n# Thread {tid} ({name})")
            out.append("".join(traceback.format_stack(frame)))
        out.append("=== end stack dump ===\n")
        print("\n".join(out), file=_sys.stderr, flush=True)

    try:
        signal.signal(signal.SIGUSR1, _dump)
    except (ValueError, OSError):
        # signal.signal raises if not on the main thread — best-effort.
        pass


@app.on_startup
async def startup():
    if _LOCK_FILE.exists():
        return
    try:
        _LOCK_FILE.write_text(str(threading.get_ident()))
        _install_stackdump_handler()
        threading.Thread(target=start_mcp_server, daemon=True).start()
        threading.Thread(target=start_governance_timer, daemon=True).start()
        threading.Thread(target=start_drift_timer, daemon=True).start()
        threading.Thread(target=start_quality_timer, daemon=True).start()
    except Exception as e:
        print(f"Startup error: {e}")


@app.on_shutdown
async def shutdown():
    _LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    ui.run(
        title="PRISM Service",
        port=UI_PORT,
        host="0.0.0.0",
        reload=False,
        show=False,
        dark=False,
        storage_secret="prism-service-local",
    )
