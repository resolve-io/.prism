"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.0.0"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "UI rewrite: Hermes-native React/Vite SPA replaces NiceGUI. New /api "
    "surface backs all 10 pages. @nous-research/ui DS + Hermes Teal theme. "
    "Breaking: /ui/* NiceGUI routes removed; web client now served from /."
)
