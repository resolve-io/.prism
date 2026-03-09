"""Shared plugin root resolution for hooks.

Handles the ``claude plugin update`` cache bug where the entire marketplace
repo root is cached instead of the ``plugins/prism-devtools/`` subdirectory.
Works on both Windows (junctions) and Linux (symlinks).
"""

from __future__ import annotations

import os
from pathlib import Path

_PLUGIN_JSON_REL = Path(".claude-plugin") / "plugin.json"


def resolve_plugin_root(anchor: str | Path | None = None) -> Path:
    """Resolve the plugin root, self-healing for the wrong-depth cache bug.

    Parameters
    ----------
    anchor:
        A file path inside the plugin (typically ``__file__`` from the
        calling hook).  Used as the starting point for the walk-up
        fallback when ``CLAUDE_PLUGIN_ROOT`` is unset or invalid.
    """
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env_root:
        candidate = Path(env_root)
        if (candidate / _PLUGIN_JSON_REL).is_file():
            return candidate
        nested = candidate / "plugins" / "prism-devtools"
        if (nested / _PLUGIN_JSON_REL).is_file():
            return nested

    # Walk up from anchor to find .claude-plugin/plugin.json dynamically
    if anchor:
        p = Path(anchor).resolve().parent
        while p != p.parent:
            if (p / _PLUGIN_JSON_REL).is_file():
                return p
            p = p.parent

    # Last resort: assume hooks/ is one level below plugin root
    return Path(__file__).resolve().parent.parent


def resolve_hooks_dir(anchor: str | Path | None = None) -> Path:
    """Return the hooks directory inside the resolved plugin root."""
    return resolve_plugin_root(anchor) / "hooks"
