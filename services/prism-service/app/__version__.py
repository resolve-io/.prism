"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.3"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.3: Proof bump — if you're reading this in the sidebar and "
    "you didn't refresh the page, the SPA auto-reload watchdog "
    "(v5.1.2) is working end-to-end. v5.1.2: SPA auto-reloads on "
    "container swap via /sse/live. v5.1.1: First live Watchtower "
    "auto-update via GHCR CI. v5.1: Understand-Anything. v5.0: "
    "Hermes-native React/Vite SPA, Slate Blue theme."
)
