"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.8"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.8: Settings is now a sidebar mode, not a page. Clicking "
    "`Settings` in the footer replaces the left sidebar's Knowledge + "
    "Activity groups with the Settings categories (Projects, Claude "
    "auth, Jobs, Logs, Service). Each routes to /settings/<id> so "
    "deep-links and browser back/forward work. The footer button "
    "flips to `Application` while you're in Settings — single click "
    "back to the main app. Dashboard at the top of the sidebar still "
    "works as a parallel escape hatch. v5.1.7: claude CLI bundled in "
    "image, set-once subscription auth via /data/.claude-config, "
    "DELETE /api/projects, run log + observability, Jobs panel, "
    "scoped --allowedTools, stale-lock recovery, live scan strip, "
    "sidebar pulse while scanning. v5.1.6: bootstrap_after_clone + "
    "drainer + drift UI. v5.1: Understand-Anything. v5.0: "
    "Hermes-native React/Vite SPA."
)
