"""Version API — single source of truth for the SPA's footer + Settings."""

from fastapi import APIRouter

from app.__version__ import PRISM_VERSION, PRISM_VERSION_NOTES

router = APIRouter()


@router.get("")
def version() -> dict:
    """Return the live service version. The Sidebar footer and the
    Settings page both read this — never hardcode a version string in
    the React tree, or they'll drift apart on the next bump."""
    return {
        "version": PRISM_VERSION,
        "notes": PRISM_VERSION_NOTES,
    }
