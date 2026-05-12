"""TaskService publishes task_changed events on create/update.

The Tasks board UI subscribes via SSE to refresh on actual change rather
than polling. These tests lock in the contract: every create/update path
publishes an event scoped to the service's project_id, and a service
constructed without project_id is silent (so headless / test contexts
don't spam the bus).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


@pytest.fixture
def captured_events(monkeypatch) -> list[dict]:
    """Replace app.events.bus.publish with a list-appender for the test."""
    from app.events import bus as _bus
    events: list[dict] = []
    monkeypatch.setattr(_bus, "publish", lambda e: events.append(e))
    return events


def _mk_service(tmp_path: Path, project_id: str | None = None):
    from app.services.task_service import TaskService
    return TaskService(
        str(tmp_path / "tasks.db"),
        project_id=project_id,
    )


def test_create_publishes_task_changed(tmp_path, captured_events):
    svc = _mk_service(tmp_path, project_id="proj-a")
    task = svc.create(title="Hello", description="world")
    assert any(
        e["type"] == "task_changed"
        and e["project"] == "proj-a"
        and e["task_id"] == task.id
        and e["change"] == "created"
        for e in captured_events
    ), captured_events


def test_update_publishes_task_changed(tmp_path, captured_events):
    svc = _mk_service(tmp_path, project_id="proj-b")
    task = svc.create(title="t")
    captured_events.clear()
    svc.update(task.id, status="in_progress")
    assert any(
        e["type"] == "task_changed"
        and e["project"] == "proj-b"
        and e["task_id"] == task.id
        and e["change"] == "updated"
        for e in captured_events
    ), captured_events


def test_update_no_changes_does_not_publish(tmp_path, captured_events):
    """Idempotent update (no field actually changed) should not publish."""
    svc = _mk_service(tmp_path, project_id="proj-c")
    task = svc.create(title="t", description="d")
    captured_events.clear()
    svc.update(task.id, title="t", description="d")
    assert captured_events == [], captured_events


def test_service_without_project_id_is_silent(tmp_path, captured_events):
    """Tests / hook smoke scripts that instantiate TaskService bare
    must not spam the bus."""
    svc = _mk_service(tmp_path, project_id=None)
    task = svc.create(title="t")
    svc.update(task.id, status="done")
    assert captured_events == [], captured_events


def test_publish_failure_does_not_break_crud(tmp_path, monkeypatch):
    """If the bus raises (e.g. shut down during tests), CRUD still
    returns the task — observability must not break correctness."""
    from app.services.task_service import TaskService

    def _exploding_publish(_event: Any) -> None:
        raise RuntimeError("simulated bus failure")

    from app.events import bus as _bus
    monkeypatch.setattr(_bus, "publish", _exploding_publish)

    svc = TaskService(str(tmp_path / "tasks.db"), project_id="proj-d")
    task = svc.create(title="resilient")
    assert task.title == "resilient"
    updated = svc.update(task.id, status="in_progress")
    assert updated is not None
    assert updated.status == "in_progress"
