"""Regression tests for resolve-io/.prism#43.

`create_nav` was seeding the literal string `'default'` into
`app.storage.user['project']` on first visit and then passing it to
`ui.select(options=get_all_projects(), value=current)`, which raised
`ValueError: Invalid value: default` because the literal sentinel was
not in the real project list. Every dashboard page 500'd as a result.

These tests pin the resolution rules of `resolve_active_project`, the
pure helper extracted from `create_nav`, so the bug can't return.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _resolver():
    from app.ui.components.nav import resolve_active_project
    return resolve_active_project


def test_first_visit_picks_first_real_project_not_literal_default():
    """The exact #43 repro: no stored value, no qs hint, one real
    project. Must return the project — NOT the literal 'default'.
    """
    r = _resolver()
    assert r(stored=None, qs_proj=None, projects=["resolve-platform"]) == "resolve-platform"


def test_stored_value_wins_when_still_valid():
    r = _resolver()
    assert r(
        stored="proj-b",
        qs_proj=None,
        projects=["proj-a", "proj-b", "proj-c"],
    ) == "proj-b"


def test_query_string_overrides_stored_when_valid():
    r = _resolver()
    assert r(
        stored="proj-a",
        qs_proj="proj-c",
        projects=["proj-a", "proj-b", "proj-c"],
    ) == "proj-c"


def test_invalid_query_string_falls_through_to_stored():
    """A garbage ?project= shouldn't override a valid stored value or
    crash the selector."""
    r = _resolver()
    assert r(
        stored="proj-a",
        qs_proj="does-not-exist",
        projects=["proj-a", "proj-b"],
    ) == "proj-a"


def test_stored_project_was_deleted_self_heals_to_first_real_project():
    """Latent bug companion to #43: if the stored project is no longer
    in the project list (e.g. it got deleted), nav should self-heal
    rather than re-raise on every page."""
    r = _resolver()
    assert r(
        stored="proj-deleted",
        qs_proj=None,
        projects=["proj-a", "proj-b"],
    ) == "proj-a"


def test_no_projects_at_all_returns_default_sentinel():
    """The truly-empty-state case is the ONLY situation where the
    'default' literal is acceptable. The empty-state UI is responsible
    for guiding the user to onboard a project from there."""
    r = _resolver()
    assert r(stored=None, qs_proj=None, projects=[]) == "default"


def test_empty_string_stored_treated_as_unset():
    """An empty string in storage is functionally unset — must not be
    matched against a project list that doesn't contain it."""
    r = _resolver()
    assert r(stored="", qs_proj=None, projects=["proj-a"]) == "proj-a"
