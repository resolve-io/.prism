"""/api/github-auth — manage the GitHub credentials PRISM uses for clones.

Two paths, same storage:

1.  **OAuth Device Flow** (the click-buttons path, v5.1.11+). The operator
    registers a PRISM OAuth App on github.com once, pastes the Client ID
    into Settings → Connections, then `Connect GitHub` runs the standard
    device-flow dance. PRISM polls until the user confirms in the browser
    and writes the resulting access_token via github_auth.set_token().

2.  **Personal Access Token paste** (the v5.1.10 path). Still supported as
    a fallback for users who can't or won't register an OAuth app.

In both cases the token lands at `/data/.git-credentials` and is picked
up by the same credential helper at clone time. The token never leaves
the server — only a `user:•••last4` fingerprint is exposed.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import github_auth as gh
from app.services import github_oauth as ghoauth

router = APIRouter()

# In-process device-flow state. We keep only the device_code (which is
# short-lived, GitHub-issued, and useless without our client_id) plus the
# polling interval, keyed by a fresh nonce we hand the SPA.
_DEVICE_FLOWS: dict[str, dict] = {}


# --- payload shapes -----------------------------------------------------


class ConfigureBody(BaseModel):
    """PAT-paste path — kept for back-compat with v5.1.10 callers."""
    token: str
    user: str = "x-access-token"


class ClientIdBody(BaseModel):
    client_id: str


class DevicePollBody(BaseModel):
    flow_id: str


# --- status / clear (shared by both paths) ------------------------------


def _status_payload() -> dict:
    authed = gh.is_authenticated()
    meta = ghoauth.read_meta()
    client_id = ghoauth.get_client_id()
    return {
        "authenticated": authed,
        "credentials_path": str(gh.credentials_path()),
        "fingerprint": gh.token_fingerprint() if authed else "",
        # OAuth metadata (empty when the active token came from the PAT path)
        "login": meta.get("login", ""),
        "avatar_url": meta.get("avatar_url", ""),
        "scopes": meta.get("scopes", ""),
        "connected_at": meta.get("connected_at", 0),
        # Device-flow setup state
        "client_id_configured": bool(client_id),
        "client_id_preview": (client_id[:6] + "…" + client_id[-4:]) if client_id else "",
        "register_url": (
            "https://github.com/settings/applications/new"
            "?oauth_application%5Bname%5D=PRISM"
            "&oauth_application%5Burl%5D=http%3A%2F%2Flocalhost%3A7778"
            "&oauth_application%5Bcallback_url%5D=http%3A%2F%2Flocalhost%3A7778%2Fsettings%2Fconnections"
        ),
        "instructions": (
            "Register a `PRISM` OAuth App at github.com/settings/applications/new "
            "(any callback URL works; flip on `Enable Device Flow`), then paste "
            "the Client ID below. Or paste a Personal Access Token directly."
        ),
    }


@router.get("/status")
def status() -> dict:
    return _status_payload()


@router.post("/clear")
def clear() -> dict:
    gh.clear_token()
    ghoauth.clear_meta()
    return _status_payload()


# --- PAT-paste path (v5.1.10 compat) ------------------------------------


@router.post("/configure")
def configure(body: ConfigureBody) -> dict:
    try:
        gh.set_token(body.token, user=body.user or "x-access-token")
    except ValueError as e:
        raise HTTPException(400, str(e))
    # PAT-paste leaves OAuth metadata empty so the UI knows it's the
    # less-magical path and renders the fingerprint instead of the avatar.
    ghoauth.clear_meta()
    return _status_payload()


# --- OAuth Device Flow path (v5.1.11+) ----------------------------------


@router.get("/client-id")
def get_client_id() -> dict:
    cid = ghoauth.get_client_id()
    return {
        "configured": bool(cid),
        "preview": (cid[:6] + "…" + cid[-4:]) if cid else "",
        "from_env": bool(__import__("os").environ.get("PRISM_GITHUB_CLIENT_ID")),
    }


@router.post("/client-id")
def set_client_id(body: ClientIdBody) -> dict:
    try:
        ghoauth.set_client_id(body.client_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return get_client_id()


@router.post("/client-id/clear")
def clear_client_id() -> dict:
    ghoauth.clear_client_id()
    return get_client_id()


@router.post("/device/start")
def device_start() -> dict:
    client_id = ghoauth.get_client_id()
    if not client_id:
        raise HTTPException(
            400,
            "no Client ID configured — register a PRISM OAuth App on "
            "github.com and paste the Client ID into Settings → Connections "
            "first, or paste a Personal Access Token instead."
        )
    try:
        code = ghoauth.start_device_flow(client_id)
    except RuntimeError as e:
        raise HTTPException(502, f"github device-code request failed: {e}")
    flow_id = __import__("secrets").token_urlsafe(16)
    _DEVICE_FLOWS[flow_id] = {
        "device_code": code.device_code,
        "interval": code.interval,
        "client_id": client_id,
    }
    payload = code.public()
    payload["flow_id"] = flow_id
    return payload


@router.post("/device/poll")
def device_poll(body: DevicePollBody) -> dict:
    flow = _DEVICE_FLOWS.get(body.flow_id)
    if not flow:
        raise HTTPException(404, "unknown flow_id — start a new device flow")
    try:
        result = ghoauth.poll_device_flow(flow["client_id"], flow["device_code"])
    except RuntimeError as e:
        raise HTTPException(502, f"github poll failed: {e}")

    status_ = result.get("status")
    if status_ == "pending":
        out = {"status": "pending"}
        if result.get("slow_down"):
            flow["interval"] = flow["interval"] + 5
            out["interval"] = flow["interval"]
        return out
    if status_ in ("expired", "denied", "error"):
        # One-shot — drop the flow either way.
        _DEVICE_FLOWS.pop(body.flow_id, None)
        out = {"status": status_}
        if status_ == "error":
            out["error"] = result.get("error", "unknown error")
        return out

    # Success — exchange token for user info, store both.
    token = result["access_token"]
    try:
        user = ghoauth.fetch_user(token)
    except RuntimeError:
        user = {}
    login = user.get("login") or "x-access-token"
    avatar = user.get("avatar_url") or ""
    gh.set_token(token, user=login)
    ghoauth.write_meta(
        login=login,
        scopes=result.get("scope", ""),
        avatar_url=avatar,
    )
    _DEVICE_FLOWS.pop(body.flow_id, None)
    return {"status": "success", "login": login}


# --- Authenticated GitHub queries (used by the repo picker) -------------


@router.get("/repos")
def list_repos(q: str = "", page: int = 1) -> dict:
    """Read the current token out of the credentials file and ask GitHub
    for the operator's repos. Token never leaves the process."""
    token = _current_token()
    if not token:
        raise HTTPException(400, "not connected to GitHub")
    try:
        return ghoauth.fetch_repos(token, q=q, page=page)
    except RuntimeError as e:
        raise HTTPException(502, f"github repo list failed: {e}")


def _current_token() -> Optional[str]:
    """Pull the token out of `/data/.git-credentials` by reading the
    github.com line. We don't keep a long-lived in-memory copy — the
    credentials file is the single source of truth."""
    if not gh.CREDS_PATH.is_file():
        return None
    try:
        body = gh.CREDS_PATH.read_text(encoding="utf-8")
    except OSError:
        return None
    m = gh._GITHUB_PARSE_RE.search(body)
    if not m:
        return None
    return m.group(2)
