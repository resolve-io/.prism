"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.6"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.6: Adding a repo actually auto-processes. POST /api/projects "
    "with remote_url and /api/understand/configure both kick off the "
    "shared bootstrap (clone -> Brain + Graph ingest -> enqueue all "
    "four Understand-Anything analyzers). A server-side drainer picks "
    "up the queue every 15s (PRISM_UNDERSTAND_DRAIN_INTERVAL=0 to "
    "disable) and runs each analyzer via the existing claude_cli path "
    "- no host-side shell required. SettingsPage shows live queue "
    "depth, a drift badge when current_sha != last_analyzed_sha, and "
    "a manual Sync button. v5.1.4: GHCR publish + SPA auto-reload. "
    "v5.1: Understand-Anything. v5.0: Hermes-native React/Vite SPA."
)
