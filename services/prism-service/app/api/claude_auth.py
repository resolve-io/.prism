"""/api/claude-auth — Claude CLI authentication status for the SPA.

The container ships with `@anthropic-ai/claude-code` installed and
CLAUDE_CONFIG_DIR pointing into the data volume. Auth itself is a
one-time `claude /login` (or `claude setup-token`) the operator runs
inside the container; PRISM can't drive the OAuth browser redirect
itself without a full PTY-backed terminal in the SPA.

What this endpoint DOES provide:
  * GET /status — is .credentials.json present in CLAUDE_CONFIG_DIR?
    Returns the docker exec command line the operator should run when
    not authenticated, so the SPA can render a clear instruction.

A future Task #14 will add a PTY-backed in-browser login flow that
mirrors Auto-Claude's terminal/pty-manager pattern; until then, the
operator completes auth in their own terminal and watches the SPA
flip to "authenticated" on the next poll.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()


def _config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR", "/root/.claude"))


def _container_name() -> str:
    """Best-effort container identifier for the docker-exec hint shown in the UI.

    Prefers an operator-supplied PRISM_CONTAINER_NAME env var (set this
    in your compose file to e.g. `prism-service-v51` or `prism-consumer`
    so the SPA shows a friendly name). Falls back to /etc/hostname which
    is the short container ID - docker accepts either as the target of
    `docker exec`, so the command works regardless.
    """
    explicit = os.environ.get("PRISM_CONTAINER_NAME", "").strip()
    if explicit:
        return explicit
    try:
        return Path("/etc/hostname").read_text(encoding="utf-8").strip()
    except OSError:
        return "prism-service"


@router.get("/status")
def status() -> dict:
    cfg = _config_dir()
    cred = cfg / ".credentials.json"
    authenticated = cred.is_file()
    name = _container_name()
    return {
        "authenticated": authenticated,
        "config_dir": str(cfg),
        "credentials_path": str(cred),
        "container": name,
        "login_command": f"docker exec -it {name} claude /login",
        "instructions": (
            "Run the command above on your host to complete a one-time OAuth "
            "flow. Tokens land in CLAUDE_CONFIG_DIR (volume-backed) and the "
            "claude CLI auto-refreshes them - you should never need to log in "
            "again unless you revoke the session."
        ),
    }
