"""GitHub OAuth Device Flow — the click-buttons-to-connect path.

The operator registers a `PRISM` OAuth App at github.com/settings/applications/new
(Authorization callback URL can be anything; device flow doesn't use it),
enables the "Device Flow" checkbox, and pastes the resulting Client ID into
PRISM once. From then on `Connect GitHub` runs the standard device-flow
dance: request a short code, show it to the user, poll until they confirm
in the browser, store the access_token via github_auth.set_token().

We intentionally keep this stdlib-only — no httpx dependency to add — and
expose three small helpers the API layer calls in sequence. Token storage
lives in github_auth.py so the existing clone-time credential helper path
keeps working unchanged.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR

CLIENT_ID_PATH = DATA_DIR / ".github-client-id"
META_PATH = DATA_DIR / ".github-auth.json"

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
USER_URL = "https://api.github.com/user"
REPOS_URL = "https://api.github.com/user/repos"

# Scopes PRISM needs: `repo` is the only one that lets us clone private
# repos. `read:user` lets us look up the login name to display.
DEFAULT_SCOPES = "repo read:user"

# Standard OAuth App ID format is 20 hex chars. We don't enforce — GitHub
# can change format — but we use this to spot obvious paste errors.
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{8,128}$")


# --- client_id persistence ----------------------------------------------

def get_client_id() -> str:
    env = os.environ.get("PRISM_GITHUB_CLIENT_ID", "").strip()
    if env:
        return env
    if not CLIENT_ID_PATH.is_file():
        return ""
    try:
        return CLIENT_ID_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def set_client_id(client_id: str) -> None:
    client_id = (client_id or "").strip()
    if not client_id:
        raise ValueError("client_id is required")
    if not _CLIENT_ID_RE.match(client_id):
        raise ValueError(
            "client_id looks malformed — expected the 20-char ID "
            "from github.com/settings/applications/new"
        )
    CLIENT_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CLIENT_ID_PATH.with_suffix(CLIENT_ID_PATH.suffix + ".tmp")
    tmp.write_text(client_id + "\n", encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, CLIENT_ID_PATH)


def clear_client_id() -> None:
    try:
        CLIENT_ID_PATH.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


# --- OAuth metadata (login/scopes, never the token) ---------------------

def write_meta(login: str, scopes: str, avatar_url: str = "") -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({
        "login": login,
        "scopes": scopes,
        "avatar_url": avatar_url,
        "connected_at": int(time.time()),
    })
    tmp = META_PATH.with_suffix(META_PATH.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, META_PATH)


def read_meta() -> dict:
    if not META_PATH.is_file():
        return {}
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def clear_meta() -> None:
    try:
        META_PATH.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


# --- HTTP helpers (stdlib, no httpx dep) --------------------------------

def _post_form(url: str, data: dict, accept: str = "application/json") -> dict:
    body = urllib.parse.urlencode(data).encode("ascii")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Accept": accept, "User-Agent": "prism-service"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"github http {e.code}: {raw[:200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"github network error: {e.reason}") from e
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"github returned non-json: {raw[:200]}") from e


def _get_json(url: str, token: str, params: dict | None = None) -> tuple[dict | list, dict]:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url, method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "prism-service",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8")
            headers = dict(r.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise RuntimeError(f"github http {e.code}: {body[:200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"github network error: {e.reason}") from e
    return json.loads(raw), headers


# --- Device flow operations ---------------------------------------------

@dataclass
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval: int

    def public(self) -> dict:
        # `device_code` stays server-side — the SPA only needs the
        # short code + verification URL + a polling cadence.
        return {
            "user_code": self.user_code,
            "verification_uri": self.verification_uri,
            "expires_in": self.expires_in,
            "interval": self.interval,
        }


def start_device_flow(client_id: str, scopes: str = DEFAULT_SCOPES) -> DeviceCode:
    if not client_id:
        raise ValueError("client_id is required — set one in Settings → Connections")
    resp = _post_form(DEVICE_CODE_URL, {"client_id": client_id, "scope": scopes})
    try:
        return DeviceCode(
            device_code=resp["device_code"],
            user_code=resp["user_code"],
            verification_uri=resp.get("verification_uri", "https://github.com/login/device"),
            expires_in=int(resp.get("expires_in", 900)),
            interval=max(1, int(resp.get("interval", 5))),
        )
    except (KeyError, TypeError, ValueError) as e:
        raise RuntimeError(f"device_code response missing fields: {resp}") from e


def poll_device_flow(client_id: str, device_code: str) -> dict:
    """Returns one of:

        {"status": "pending", "interval": <new interval if slow_down>}
        {"status": "expired"}
        {"status": "denied"}
        {"status": "success", "access_token": "...", "scope": "..."}
        {"status": "error", "error": "<message>"}
    """
    resp = _post_form(
        ACCESS_TOKEN_URL,
        {
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        },
    )
    err = resp.get("error")
    if err == "authorization_pending":
        return {"status": "pending"}
    if err == "slow_down":
        # GitHub asked us to back off; pass the new interval through.
        return {"status": "pending", "slow_down": True}
    if err == "expired_token":
        return {"status": "expired"}
    if err == "access_denied":
        return {"status": "denied"}
    if err:
        return {"status": "error", "error": resp.get("error_description") or err}
    token = resp.get("access_token")
    if not token:
        return {"status": "error", "error": "no access_token in response"}
    return {
        "status": "success",
        "access_token": token,
        "scope": resp.get("scope", ""),
        "token_type": resp.get("token_type", "bearer"),
    }


# --- Authenticated GitHub calls -----------------------------------------

def fetch_user(token: str) -> dict:
    data, _ = _get_json(USER_URL, token)
    if isinstance(data, dict):
        return data
    return {}


def fetch_repos(token: str, q: str = "", page: int = 1, per_page: int = 30) -> dict:
    """List the user's repos. If `q` is present we filter client-side by
    full_name — GitHub's /user/repos has no `q` param; the proper search
    endpoint /search/repositories has a different shape we don't need.
    """
    params = {
        "per_page": str(per_page),
        "page": str(page),
        "sort": "pushed",
        "affiliation": "owner,collaborator,organization_member",
    }
    data, headers = _get_json(REPOS_URL, token, params=params)
    if not isinstance(data, list):
        return {"repos": [], "has_more": False}
    q_lower = q.strip().lower()
    repos = []
    for r in data:
        full_name = r.get("full_name", "")
        if q_lower and q_lower not in full_name.lower():
            continue
        repos.append({
            "full_name": full_name,
            "name": r.get("name", ""),
            "owner": (r.get("owner") or {}).get("login", ""),
            "private": bool(r.get("private")),
            "default_branch": r.get("default_branch", "main"),
            "description": r.get("description") or "",
            "clone_url": r.get("clone_url", ""),
            "html_url": r.get("html_url", ""),
            "pushed_at": r.get("pushed_at", ""),
            "stargazers_count": int(r.get("stargazers_count", 0) or 0),
        })
    # Crude has_more — Link header would be more accurate but this is fine
    # for the SPA's "Load more" button.
    link = headers.get("Link", "") or headers.get("link", "")
    has_more = 'rel="next"' in link
    return {"repos": repos, "has_more": has_more, "page": page}
