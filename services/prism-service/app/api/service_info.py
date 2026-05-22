"""/api/service-info — operator-useful runtime info for the Settings UI.

Single source for what the Settings → Service section shows: friendly
container name (so the docker-exec hints elsewhere have one place to
come from), version, key intervals, claude auth status one-liner, and
MCP endpoint hint. No secrets, just configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from app.__version__ import PRISM_VERSION, PRISM_VERSION_NOTES
from app.config import (
    DRIFT_INTERVAL_SECONDS,
    GOVERNANCE_INTERVAL_SECONDS,
    QUALITY_INTERVAL_SECONDS,
)

router = APIRouter()


def _container_name() -> str:
    """Same resolution as /api/claude-auth — explicit env var or /etc/hostname."""
    explicit = os.environ.get("PRISM_CONTAINER_NAME", "").strip()
    if explicit:
        return explicit
    try:
        return Path("/etc/hostname").read_text(encoding="utf-8").strip()
    except OSError:
        return "prism-service"


def _drain_interval() -> int:
    return int(os.environ.get("PRISM_UNDERSTAND_DRAIN_INTERVAL", "15"))


def _claude_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", "/root/.claude"))


@router.get("")
def service_info() -> dict:
    cfg = _claude_config_dir()
    return {
        "version": PRISM_VERSION,
        "notes": PRISM_VERSION_NOTES,
        "container": _container_name(),
        "claude_config_dir": str(cfg),
        "claude_authenticated": (cfg / ".credentials.json").is_file(),
        "understand_drain_interval_s": _drain_interval(),
        "drift_interval_s": DRIFT_INTERVAL_SECONDS,
        "governance_interval_s": GOVERNANCE_INTERVAL_SECONDS,
        "quality_interval_s": QUALITY_INTERVAL_SECONDS,
        "mcp_endpoint": "/mcp/?project=<name>",
    }
