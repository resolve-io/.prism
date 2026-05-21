"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.2"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.2: SPA auto-reloads on container swap — /sse/live emits the "
    "build version on connect, EventSource reconnect after a Watchtower "
    "swap surfaces a new version and the SPA reloads itself. No more "
    "hard-refresh after auto-updates. v5.1.1: First live Watchtower "
    "auto-update via GHCR CI. v5.1: Understand-Anything. v5.0: "
    "Hermes-native React/Vite SPA, Slate Blue theme."
)
