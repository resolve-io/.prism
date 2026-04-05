"""Task data models for PRISM task management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class Task:
    """A work item tracked through the PRISM workflow."""

    id: str = ""
    title: str = ""
    description: str = ""
    status: str = "pending"  # pending | in_progress | done | blocked
    priority: int = 0
    story_file: str = ""
    assigned_agent: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: str = ""
    blocked_reason: str = ""
    dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class TaskHistory:
    """An audit record for a task state change."""

    id: int = 0
    task_id: str = ""
    actor: str = ""
    action: str = ""
    details: str = ""
    timestamp: str = ""
