"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.0"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1: Understand-Anything — source-pinned ingestion, content-addressable "
    "artifact cache (tour/architecture/domain glossary/onboarding), filesystem "
    "job queue with budget gate. v5.0: Hermes-native React/Vite SPA, /api "
    "surface backs all pages. Theme: Slate Blue (was Hermes Teal)."
)
