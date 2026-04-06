"""Memory / expertise data models for PRISM mulch layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExpertiseEntry:
    """A single expertise record stored in mulch JSONL files."""

    id: str = ""  # mx-XXXXXX format
    type: str = ""  # pattern | convention | failure | decision
    name: str = ""
    description: str = ""
    classification: str = ""  # tactical | foundational | strategic
    recorded_at: str = ""  # ISO datetime
    outcomes: list[dict] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    domain: str = ""
    recall_count: int = 0
    last_recalled: str = ""
    status: str = "active"  # active | archived | needs_review

    # Temporal validity (Graphiti-inspired)
    valid_at: str = ""  # ISO datetime — when this fact became true
    invalid_at: str = ""  # ISO datetime — when superseded (empty = still valid)

    # Quality signals
    importance: int = 5  # 1-10 scale, caller provides at write time
    memory_type: str = "semantic"  # semantic | episodic | procedural

    # Learning loop (MetaClaw-inspired)
    generation: int = 1  # increments when entry supersedes another
    effectiveness: float = 0.0  # -1.0 (hurts) to +1.0 (helps), from task outcome correlation


@dataclass
class RecallLogEntry:
    """A record of a memory entry being recalled during a task."""

    id: int = 0
    entry_id: str = ""
    entry_domain: str = ""
    query: str = ""
    recalled_at: str = ""
    task_id: str = ""  # in_progress task at time of recall
    outcome: str = ""  # positive | negative | "" (pending)


@dataclass
class HealthReport:
    """Result of a governance cycle run."""

    stale_brain_docs: int = 0
    flagged_conflicts: int = 0
    archived_this_cycle: int = 0
    stuck_tasks: int = 0
    domains_near_cap: list[str] = field(default_factory=list)
    last_governance_run: str = ""

    # Learning loop stats
    ineffective_flagged: int = 0
    effective_boosted: int = 0
