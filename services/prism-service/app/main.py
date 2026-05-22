#!/usr/bin/env python3
"""PRISM Service v5.0.0 — Brain/Memory/Tasks/Workflow with React SPA + MCP.

Cutover from NiceGUI to plain FastAPI/uvicorn. The React/Vite SPA is built
at image-build time into app/web_dist/ and served from /. The /api/* JSON
surface backs every page; /sse/sessions streams events; /graph/viewer and
/graphify-visual/* serve the standalone graph viewer + its data files.

MCP runs on a separate uvicorn started in a background thread on MCP_PORT.
"""

from __future__ import annotations

import sys as _sys
import threading
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.config import (
    DATA_DIR, PROJECT_DIR, PROJECTS_DIR,
    UI_PORT, MCP_PORT,
    GOVERNANCE_INTERVAL_SECONDS, DRIFT_INTERVAL_SECONDS, QUALITY_INTERVAL_SECONDS,
)

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
_LOCK_FILE = DATA_DIR / ".mcp_started"
WEB_DIST = Path(__file__).parent / "web_dist"


def start_mcp_server():
    """Start MCP server in background thread."""
    from app.mcp.server import run_mcp_server
    run_mcp_server(MCP_PORT)


def start_governance_timer():
    """Run governance cycles for every project on a cadence."""
    from app.project_context import get_project, get_all_projects
    while True:
        try:
            for pid in get_all_projects():
                try:
                    get_project(pid).governance.run_cycle()
                except Exception as e:
                    print(f"Governance cycle error ({pid}): {e}")
        except Exception as e:
            print(f"Governance timer error: {e}")
        time.sleep(GOVERNANCE_INTERVAL_SECONDS)


def start_drift_timer():
    """Reindex drifted Brain docs per project on a cadence.

    Uses a dedicated Brain per project (separate SQLite connections from
    the request path) so a long reindex transaction doesn't park MCP
    workers behind the same connection mutex — same fix as issue #38.
    """
    if DRIFT_INTERVAL_SECONDS <= 0:
        print("Drift timer disabled (PRISM_DRIFT_INTERVAL=0)", file=_sys.stderr)
        return
    from app.project_context import get_project, get_all_projects
    from app.engines.brain_engine import Brain
    print(f"Drift timer running every {DRIFT_INTERVAL_SECONDS}s", file=_sys.stderr)
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
                        print(f"[drift] {pid}: reindexed {n} drifted file(s)", file=_sys.stderr)
                except Exception as e:
                    print(f"Drift cycle error ({pid}): {e}", file=_sys.stderr)
        except Exception as e:
            print(f"Drift timer error: {e}", file=_sys.stderr)
        time.sleep(DRIFT_INTERVAL_SECONDS)


def start_quality_timer():
    """Score merged tasks against git truth on a cadence (LL-04)."""
    if QUALITY_INTERVAL_SECONDS <= 0:
        print("Quality timer disabled (PRISM_QUALITY_INTERVAL=0)", file=_sys.stderr)
        return
    from app.project_context import get_project, get_all_projects
    from app.services.scoring_service import score_merged_tasks
    print(f"Quality timer running every {QUALITY_INTERVAL_SECONDS}s", file=_sys.stderr)
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
                        print(f"[quality] {pid}: scored {len(scored)} merged task(s)", file=_sys.stderr)
                except Exception as e:
                    print(f"Quality cycle error ({pid}): {e}", file=_sys.stderr)
        except Exception as e:
            print(f"Quality timer error: {e}", file=_sys.stderr)
        time.sleep(QUALITY_INTERVAL_SECONDS)


def _install_stackdump_handler() -> None:
    """Dump every thread's stack to stderr on SIGUSR1 (preserved from #38)."""
    import signal
    if not hasattr(signal, "SIGUSR1"):
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
        pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Start MCP + governance/drift/quality/drainer timers on lifespan boot.

    The lock file only exists to prevent double-start within one
    process. A fresh process — including the container Watchtower just
    swapped in — must always start its own threads. The old code
    treated any pre-existing lock as "already running" and silently
    skipped every background timer after a swap (drift, governance,
    quality, and the v5.1.6 understand_drainer). v5.1.7 reclaims a
    stale lock instead of bailing.
    """
    if _LOCK_FILE.exists():
        try:
            stale_tid = _LOCK_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            stale_tid = "?"
        print(
            f"[lifespan] stale lock detected (was tid={stale_tid}); "
            f"reclaiming for tid={threading.get_ident()}",
            file=_sys.stderr, flush=True,
        )
    try:
        _LOCK_FILE.write_text(str(threading.get_ident()))
        _install_stackdump_handler()
        threading.Thread(target=start_mcp_server, daemon=True).start()
        threading.Thread(target=start_governance_timer, daemon=True).start()
        threading.Thread(target=start_drift_timer, daemon=True).start()
        threading.Thread(target=start_quality_timer, daemon=True).start()
        from app.services.understand_drainer import start_understand_drainer
        threading.Thread(target=start_understand_drainer, daemon=True).start()
    except Exception as e:
        print(f"Startup error: {e}", file=_sys.stderr, flush=True)
    yield
    _LOCK_FILE.unlink(missing_ok=True)


app = FastAPI(title="PRISM Service", lifespan=lifespan)

# JSON API for the SPA + non-API routes (SSE, graph viewer).
from app.api import api_router
from app.routes import routes_router
app.include_router(api_router)
app.include_router(routes_router)


# Static SPA. /assets/* served directly; everything else falls through to
# index.html so client-side routing handles deep links.
_RESERVED_PREFIXES = ("api/", "sse/", "graph/", "graphify-visual/", "mcp/", "openapi.json", "docs", "redoc")

if WEB_DIST.exists():
    _assets_dir = WEB_DIST / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def _spa_fallback(full_path: str):
        if any(full_path.startswith(p) for p in _RESERVED_PREFIXES):
            return JSONResponse({"detail": "not found"}, status_code=404)
        # Serve favicon/static-at-root files if they exist next to index.html
        candidate = WEB_DIST / full_path if full_path else WEB_DIST / "index.html"
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(WEB_DIST / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def _no_spa():
        return JSONResponse(
            {"detail": "SPA build missing — run `npm run build` in app/web/ or rebuild the image."},
            status_code=503,
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=UI_PORT)
