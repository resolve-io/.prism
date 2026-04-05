#!/usr/bin/env python3
"""PRISM Service — Brain, Memory, Tasks, Workflow with web UI and MCP."""

import threading

from nicegui import ui, app

from app.config import (DATA_DIR, PROJECTS_DIR,
                         UI_PORT, MCP_PORT, GOVERNANCE_INTERVAL_SECONDS)

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


# Import UI pages (they register routes with NiceGUI)
from app.ui import dashboard, brain_page, memory_page, tasks_page, conductor_page, sessions_page

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
