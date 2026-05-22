"""/api/github-auth — manage the GitHub credentials PRISM uses for clones.

Mirrors /api/claude-auth in shape: a status endpoint the SPA polls, plus
configure/clear write endpoints driven from the Connections panel. The
token itself is never echoed back — only a fingerprint (user + last-4
of the token) is exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import github_auth as gh

router = APIRouter()


class ConfigureBody(BaseModel):
    token: str
    user: str = "x-access-token"


def _status_payload() -> dict:
    authed = gh.is_authenticated()
    return {
        "authenticated": authed,
        "credentials_path": str(gh.credentials_path()),
        "fingerprint": gh.token_fingerprint() if authed else "",
        "instructions": (
            "Create a fine-grained Personal Access Token at "
            "https://github.com/settings/tokens with `Contents: read` "
            "for the repos PRISM should clone. Paste it below — it's "
            "stored only in the data volume (chmod 600) and never "
            "echoed back."
        ),
    }


@router.get("/status")
def status() -> dict:
    return _status_payload()


@router.post("/configure")
def configure(body: ConfigureBody) -> dict:
    try:
        gh.set_token(body.token, user=body.user or "x-access-token")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _status_payload()


@router.post("/clear")
def clear() -> dict:
    gh.clear_token()
    return _status_payload()
