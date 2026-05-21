"""PRISM Service configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path

# Data directory — volume-mounted in Docker, local fallback for dev
DATA_DIR = Path(os.environ.get("PRISM_DATA_DIR", "/data"))

# Projects root — each project gets its own subdirectory
PROJECTS_DIR = DATA_DIR / "projects"

# Project directory — volume-mounted for Brain ingest
PROJECT_DIR = Path(os.environ.get("PRISM_PROJECT_DIR", "/project"))

# Ports
UI_PORT = int(os.environ.get("PRISM_UI_PORT", "7778"))
MCP_PORT = int(os.environ.get("PRISM_MCP_PORT", "7777"))

# Governance
GOVERNANCE_INTERVAL_SECONDS = int(os.environ.get("PRISM_GOVERNANCE_INTERVAL", "300"))  # 5 min

# Drift auto-reindex — how often a background thread runs
# incremental_reindex across all projects. 0 disables the loop
# entirely so ops can opt out.
DRIFT_INTERVAL_SECONDS = int(
    os.environ.get("PRISM_DRIFT_INTERVAL", "1800"),  # 30 min default
)

# Quality timer (LL-04) — how often to score merged tasks against git
# truth. 6h default so the 14d durability window has time to accumulate
# revert/churn/follow-up signals. 0 disables.
QUALITY_INTERVAL_SECONDS = int(
    os.environ.get("PRISM_QUALITY_INTERVAL", "21600"),  # 6h default
)

# Shelf-life defaults per domain (days)
DOMAIN_SHELF_LIFE: dict[str, int] = {
    "default": 30,
    "architecture": 60,
    "conventions": 60,
    "failures": 14,
    "tactical": 14,
}

DOMAIN_BUDGET_CAP = 100
DUPLICATE_THRESHOLD = 0.85
USAGE_DECAY_DAYS = 30
USAGE_ARCHIVE_DAYS = 60
TASK_STALE_HOURS = 24

DEFAULT_PROJECT = "default"


_UNDERSTAND_STATE_FILENAME = "understand_state.json"
_UNDERSTAND_STATE_DEFAULT: dict = {
    "tracked_ref": "origin/main",
    "last_analyzed_sha": None,
    "analyzers": {},
}


def project_data_dir(project_id: str) -> Path:
    """Return the data directory for a specific project, creating it if needed.

    Also seeds the v5.1 Understand-Anything layout:
      - source/                       (T5 fills with git clone)
      - graph/                        (T6 CAS root, keyed by SHA)
      - understand_state.json         (tracked ref + per-analyzer state)

    Existing subdirs (mulch/, workflow/) are preserved. The state file
    is written with a default skeleton only on first call; subsequent
    calls do not overwrite operator edits.
    """
    d = PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "mulch").mkdir(exist_ok=True)
    (d / "mulch" / "expertise").mkdir(exist_ok=True)
    (d / "workflow").mkdir(exist_ok=True)
    (d / "source").mkdir(exist_ok=True)
    (d / "graph").mkdir(exist_ok=True)
    state_path = d / _UNDERSTAND_STATE_FILENAME
    if not state_path.exists():
        state_path.write_text(
            json.dumps(_UNDERSTAND_STATE_DEFAULT, indent=2),
            encoding="utf-8",
        )
    return d


def list_projects() -> list[str]:
    """List all project IDs that have data directories."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
