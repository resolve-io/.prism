"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "0.2.0"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "graphify-backed code graph, pluggable embedder (MiniLM default), "
    "drift detection via content-hash, self-installing SessionStart hook"
)
