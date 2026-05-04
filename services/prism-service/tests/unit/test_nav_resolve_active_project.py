"""Issue #43 tests — resolve_active_project never returns a value
that's outside the projects list.

resolve-io/.prism#43: nav.py used to seed app.storage.user['project']
to the literal 'default' sentinel even when real projects existed,
then pass that sentinel as value= to ui.select(options=projects)
where 'default' was not in options. NiceGUI raised ValueError and
every dashboard page 500'd.

The fix extracts a pure helper resolve_active_project(qs_proj, stored,
projects) that always returns a value guaranteed to be in projects
(or the 'default' sentinel only when projects is empty, in which case
the caller's `or ['default']` fallback covers it).
"""

from __future__ import annotations

import sys
from pathlib import Path


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


from app.ui.components.nav import resolve_active_project


PROJECTS = ['resolve-platform', 'talentsync', 'prism']


def test_url_project_wins_when_valid():
    """URL ?project= overrides stored value when it points at a real project."""
    assert resolve_active_project(
        'talentsync', 'prism', PROJECTS,
    ) == 'talentsync'


def test_url_project_ignored_when_not_in_options():
    """The bug from #43 — never return a value outside projects.
    Falls back to stored, then to first project."""
    assert resolve_active_project(
        'does-not-exist', 'prism', PROJECTS,
    ) == 'prism'


def test_stored_value_used_when_valid():
    """No URL hint, stored value is real → keep it."""
    assert resolve_active_project(None, 'prism', PROJECTS) == 'prism'


def test_stored_default_sentinel_replaced_by_real_project():
    """The exact #43 scenario: stored = 'default', real projects exist.
    Old code: returned 'default', NiceGUI 500. New code: first project."""
    assert resolve_active_project(
        None, 'default', PROJECTS,
    ) == 'resolve-platform'


def test_first_project_when_no_stored_value():
    """First visit, no cookies, projects exist → first project."""
    assert resolve_active_project(None, None, PROJECTS) == 'resolve-platform'


def test_first_project_when_stored_value_is_stale():
    """Project was deleted but cookie still references it → fall back."""
    assert resolve_active_project(
        None, 'deleted-project', PROJECTS,
    ) == 'resolve-platform'


def test_default_sentinel_only_when_projects_empty():
    """Truly empty install (first run, nothing onboarded) → return
    'default' so the caller's `or ['default']` options fallback aligns."""
    assert resolve_active_project(None, None, []) == 'default'
    assert resolve_active_project('foo', 'bar', []) == 'default'


def test_empty_string_qs_proj_does_not_match():
    """Empty string from URL parsing isn't a real project."""
    assert resolve_active_project('', 'prism', PROJECTS) == 'prism'


def test_returned_value_always_in_options_or_default():
    """Property test: for any combination of inputs, the result is
    either in projects OR the literal 'default' sentinel (which is
    fine because the caller falls back to `['default']` options when
    projects is empty)."""
    test_cases = [
        ('valid', 'valid-stored', PROJECTS),
        ('invalid', 'invalid', PROJECTS),
        (None, None, PROJECTS),
        ('', '', PROJECTS),
        ('resolve-platform', 'talentsync', PROJECTS),
        (None, None, []),
        ('foo', 'bar', []),
    ]
    for qs, stored, projects in test_cases:
        result = resolve_active_project(qs, stored, projects)
        assert result in projects or result == 'default', (
            f"resolve_active_project({qs!r}, {stored!r}, {projects!r}) "
            f"returned {result!r} which is neither in projects nor 'default'"
        )
