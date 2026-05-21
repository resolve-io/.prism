"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.4"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.4: Second proof bump — verifying auto-reload is repeatable. "
    "If the sidebar flipped from 5.1.3 to 5.1.4 without you touching "
    "the page, every future update lands the same way. v5.1.3: First "
    "auto-reload proof. v5.1.2: SPA auto-reload via /sse/live. "
    "v5.1.1: First Watchtower auto-update via GHCR CI."
)
