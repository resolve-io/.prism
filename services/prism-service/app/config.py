"""PRISM Service configuration."""

from __future__ import annotations

import os
from pathlib import Path

# Data directory — volume-mounted in Docker, local fallback for dev
DATA_DIR = Path(os.environ.get("PRISM_DATA_DIR", "/data"))

# Projects root — each project gets its own subdirectory
PROJECTS_DIR = DATA_DIR / "projects"

# Project directory — volume-mounted for Brain ingest
PROJECT_DIR = Path(os.environ.get("PRISM_PROJECT_DIR", "/project"))

# Ports
UI_PORT = int(os.environ.get("PRISM_UI_PORT", "8080"))
MCP_PORT = int(os.environ.get("PRISM_MCP_PORT", "8081"))

# Governance
GOVERNANCE_INTERVAL_SECONDS = int(os.environ.get("PRISM_GOVERNANCE_INTERVAL", "300"))  # 5 min

# Drift auto-reindex — how often a background thread runs
# incremental_reindex across all projects. 0 disables the loop
# entirely so ops can opt out.
DRIFT_INTERVAL_SECONDS = int(
    os.environ.get("PRISM_DRIFT_INTERVAL", "1800"),  # 30 min default
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


def project_data_dir(project_id: str) -> Path:
    """Return the data directory for a specific project, creating it if needed."""
    d = PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "mulch").mkdir(exist_ok=True)
    (d / "mulch" / "expertise").mkdir(exist_ok=True)
    (d / "workflow").mkdir(exist_ok=True)
    return d


def list_projects() -> list[str]:
    """List all project IDs that have data directories."""
    if not PROJECTS_DIR.exists():
        return []
    return sorted(
        p.name for p in PROJECTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
