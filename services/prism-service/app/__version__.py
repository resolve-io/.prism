"""Single source of truth for PRISM's version.

Bump on user-visible changes — schema migrations, new tools, hook script
updates, install-manifest changes. Served alongside the install manifest
so users can tell which version is live and which one installed their hook.
"""

PRISM_VERSION = "5.1.10"

# Changelog-ish notes (free-form; keep short)
PRISM_VERSION_NOTES = (
    "v5.1.10: GitHub connection lives next to Claude auth in the new "
    "`Connections` sidebar section (renamed from `Claude auth`). Paste "
    "a Personal Access Token, click `Connect`, and PRISM stores it at "
    "`/data/.git-credentials` (volume-backed, chmod 600). Every `git "
    "clone` and `git fetch` PRISM runs picks the token up automatically "
    "via `git -c credential.helper=…`, so the next time you point a "
    "project at a private GitHub repo the clone Just Works. The token "
    "never appears in `understand_state.json`, in logs, or in API "
    "responses — only a `user:•••last4` fingerprint is shown back. "
    "Service tab gained a `GitHub` status row alongside `Claude auth`. "
    "Legacy `/settings/auth` redirects to the new `/settings/connections` "
    "URL so any bookmarks keep working. "
    "v5.1.9: Private-repo clone failures now surface as a clean HTTP "
    "400 from /api/projects and /api/understand/configure instead of "
    "silently creating an unscannable, head-less project. ensure_cloned() "
    "checks the return code of `git clone` and `git fetch`, raises "
    "SourceUnavailable with a credential-scrubbed message (PATs in the "
    "URL are stripped before the error reaches API responses or logs), "
    "and wipes the half-initialized source/ dir so a retry with corrected "
    "credentials starts clean. Customers can pick any credential shape "
    "they want — PAT-in-URL, SSH deploy key + git@ remote, or a "
    "credential helper baked into the container. "
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
