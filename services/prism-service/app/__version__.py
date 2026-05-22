"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.7"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.7: Four follow-ups to make v5.1.6's auto-process actually "
    "run end-to-end. (1) The image bundles `@anthropic-ai/claude-code` "
    "so the in-container understand_drainer can run analyzers. Auth "
    "is set-once via `docker exec -it prism-service claude login` — "
    "tokens persist in /data/.claude-config (volume-backed, survives "
    "Watchtower swaps), CLI auto-refreshes the 8h access token "
    "against console.anthropic.com. Pattern borrowed from "
    "Auto-Claude's claude-profile-manager. INV-1 preserved — no API "
    "key. (2) Stale startup lock no longer kills background threads "
    "after a container swap. (3) DELETE /api/projects/{name} wipes "
    "the project's data dir (brain, graph, tasks, scores, source, "
    "queue, artifacts) with a type-the-name confirm; refuses "
    "'default'. (4) Every PRISM-initiated `claude -p` call is "
    "captured to /data/claude_runs/ — Settings shows a 'Recent "
    "claude executions' panel so you can verify the drainer is "
    "working. v5.1.6: bootstrap_after_clone + drainer + drift UI. "
    "v5.1: Understand-Anything. v5.0: Hermes-native React/Vite SPA."
)
