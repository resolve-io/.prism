"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.4"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.4: GHCR publish pipeline + SPA auto-reload. New release "
    "workflow builds ghcr.io/<owner>/prism-service on every v* tag "
    "(no main-push trigger). The SPA opens /sse/live and reloads "
    "itself when the backend reports a new version after a container "
    "swap (e.g. Watchtower auto-update), so users no longer need to "
    "hard-refresh. v5.1: Understand-Anything. v5.0: Hermes-native "
    "React/Vite SPA, Slate Blue theme."
)
