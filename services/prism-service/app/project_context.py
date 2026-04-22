"""Project context — manages per-project service instances.

Each project gets its own isolated set of services (brain, tasks, memory,
workflow, conductor, governance) backed by its own data directory.

Service instances are lazily created and cached.
"""

from __future__ import annotations

import threading
from typing import Optional

from app.config import project_data_dir, list_projects, PROJECTS_DIR, DEFAULT_PROJECT


class ProjectContext:
    """Holds service instances for a single project."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._data_dir = project_data_dir(project_id)

        # Lazy service instances
        self._brain_svc = None
        self._graph_svc = None
        self._task_svc = None
        self._workflow_svc = None
        self._memory_svc = None
        self._conductor_svc = None
        self._governance = None

    @property
    def brain_svc(self):
        if self._brain_svc is None:
            from app.services.brain_service import BrainService
            self._brain_svc = BrainService(
                brain_db=str(self._data_dir / "brain.db"),
                graph_db=str(self._data_dir / "graph.db"),
                scores_db=str(self._data_dir / "scores.db"),
            )
            # Wire graph service for source-file staging
            self._brain_svc.graph_svc = self.graph_svc
        return self._brain_svc

    @property
    def graph_svc(self):
        if self._graph_svc is None:
            from app.services.graph_service import GraphService
            self._graph_svc = GraphService(
                project_data_dir=str(self._data_dir),
                graph_db_path=str(self._data_dir / "graph.db"),
            )
        return self._graph_svc

    @property
    def task_svc(self):
        if self._task_svc is None:
            from app.services.task_service import TaskService
            self._task_svc = TaskService(
                db_path=str(self._data_dir / "tasks.db"),
            )
        return self._task_svc

    @property
    def workflow_svc(self):
        if self._workflow_svc is None:
            from app.services.workflow_service import WorkflowService
            self._workflow_svc = WorkflowService(
                workflow_dir=str(self._data_dir / "workflow"),
            )
        return self._workflow_svc

    @property
    def memory_svc(self):
        if self._memory_svc is None:
            from app.services.memory_service import MemoryService
            self._memory_svc = MemoryService(
                mulch_dir=str(self._data_dir / "mulch"),
                task_svc=self.task_svc,
            )
        return self._memory_svc

    @property
    def conductor_svc(self):
        if self._conductor_svc is None:
            from app.services.conductor_service import ConductorService
            self._conductor_svc = ConductorService(
                scores_db=str(self._data_dir / "scores.db"),
            )
        return self._conductor_svc

    @property
    def governance(self):
        if self._governance is None:
            from app.services.governance import GovernanceEngine
            self._governance = GovernanceEngine(
                self.memory_svc, self.task_svc, self.brain_svc,
            )
        return self._governance


# ---------------------------------------------------------------------------
# Global registry of project contexts (thread-safe)
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_contexts: dict[str, ProjectContext] = {}


def get_project(project_id: Optional[str] = None) -> ProjectContext:
    """Get or create a ProjectContext for the given project ID."""
    pid = project_id or DEFAULT_PROJECT
    with _lock:
        if pid not in _contexts:
            _contexts[pid] = ProjectContext(pid)
        return _contexts[pid]


def get_all_projects() -> list[str]:
    """List all project IDs that have data on disk."""
    return list_projects()


def create_project(project_id: str) -> ProjectContext:
    """Create a new project (creates its data directory)."""
    project_data_dir(project_id)  # ensure dirs exist
    return get_project(project_id)
