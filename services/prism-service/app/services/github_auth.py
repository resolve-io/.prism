"""GitHub credentials management for PRISM's git operations.

Customers configure a Personal Access Token (or any github username +
token pair) through the SPA Connections panel. We store them in
`/data/.git-credentials` (volume-backed, chmod 600, so they survive
container swaps) and inject git's `store` credential helper into every
_run_git call when the file exists. The token never lands in
remote_url, understand_state.json, logs, or API responses — only a
fingerprint (user + last-4 of the token) is ever returned.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from app.config import DATA_DIR

CREDS_FILENAME = ".git-credentials"
CREDS_PATH = DATA_DIR / CREDS_FILENAME

# Matches a `https://user:token@github.com` line — we use this both to
# detect whether a github.com entry is present and to scrub/replace it.
_GITHUB_LINE_RE = re.compile(r"^https://[^@\s]+@github\.com\b", re.MULTILINE)
_GITHUB_PARSE_RE = re.compile(r"https://([^:]+):([^@]+)@github\.com")


def credentials_path() -> Path:
    return CREDS_PATH


def is_authenticated() -> bool:
    if not CREDS_PATH.is_file():
        return False
    try:
        body = CREDS_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(_GITHUB_LINE_RE.search(body))


def token_fingerprint() -> str:
    """Return a UI-safe identifier — never the token itself.

    Format: `<user>:•••<last4>` so the operator can recognize which
    token is in use without it leaking through the API surface.
    """
    if not CREDS_PATH.is_file():
        return ""
    try:
        body = CREDS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""
    m = _GITHUB_PARSE_RE.search(body)
    if not m:
        return ""
    user, token = m.group(1), m.group(2)
    tail = token[-4:] if len(token) >= 4 else token
    return f"{user}:•••{tail}"


def set_token(token: str, user: str = "x-access-token") -> None:
    """Atomically write a github.com credential line, preserving other hosts."""
    token = (token or "").strip()
    user = (user or "x-access-token").strip() or "x-access-token"
    if not token:
        raise ValueError("token is required")
    CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if CREDS_PATH.is_file():
        try:
            existing = CREDS_PATH.read_text(encoding="utf-8")
        except OSError:
            existing = ""
    kept = [
        ln for ln in existing.splitlines()
        if ln.strip() and not _GITHUB_LINE_RE.match(ln)
    ]
    kept.append(f"https://{user}:{token}@github.com")
    body = "\n".join(kept) + "\n"

    tmp = CREDS_PATH.with_suffix(CREDS_PATH.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        # Best-effort: Windows / restricted filesystems may not support chmod.
        pass
    os.replace(tmp, CREDS_PATH)


def clear_token() -> bool:
    """Remove the github.com line. Returns True if a line was removed."""
    if not CREDS_PATH.is_file():
        return False
    try:
        body = CREDS_PATH.read_text(encoding="utf-8")
    except OSError:
        return False
    lines = body.splitlines()
    kept = [ln for ln in lines if not _GITHUB_LINE_RE.match(ln)]
    if len(kept) == len(lines):
        return False
    if any(ln.strip() for ln in kept):
        CREDS_PATH.write_text("\n".join(kept) + "\n", encoding="utf-8")
    else:
        try:
            CREDS_PATH.unlink()
        except OSError:
            pass
    return True


def git_credential_helper_args() -> list[str]:
    """Return `-c credential.helper=…` args to inject into every git call.

    Empty list when no creds file exists, so the no-auth path stays
    untouched (and existing tests against local bare repos keep passing).
    """
    if not CREDS_PATH.is_file():
        return []
    return ["-c", f"credential.helper=store --file={CREDS_PATH}"]
