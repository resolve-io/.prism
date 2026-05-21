"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.1"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.1: First live Watchtower auto-update — published via GHCR CI, "
    "consumer compose with Watchtower picked up the new digest within 60s "
    "of the workflow finishing. v5.1: Understand-Anything — source-pinned "
    "ingestion, content-addressable artifact cache. v5.0: Hermes-native "
    "React/Vite SPA, /api surface backs all pages. Theme: Slate Blue."
)
