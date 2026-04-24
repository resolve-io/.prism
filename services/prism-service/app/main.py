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
    """
    import sys as _sys
    import time
    if DRIFT_INTERVAL_SECONDS <= 0:
        print("Drift timer disabled (PRISM_DRIFT_INTERVAL=0)",
              file=_sys.stderr)
        return
    from app.project_context import get_project, get_all_projects
    print(
        f"Drift timer running every {DRIFT_INTERVAL_SECONDS}s",
        file=_sys.stderr,
    )
    while True:
        try:
            for pid in get_all_projects():
                try:
                    ctx = get_project(pid)
                    n = ctx.brain_svc.incremental_reindex()
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
)

# Guard against double-start using file lock
_LOCK_FILE = DATA_DIR / ".mcp_started"


@app.on_startup
async def startup():
    if _LOCK_FILE.exists():
        return
    try:
        _LOCK_FILE.write_text(str(threading.get_ident()))
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
