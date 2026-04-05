"""Governance engine — deterministic rules enforced on a timer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Optional

from app.config import (
    DOMAIN_BUDGET_CAP,
    DOMAIN_SHELF_LIFE,
    DUPLICATE_THRESHOLD,
    TASK_STALE_HOURS,
    USAGE_ARCHIVE_DAYS,
    USAGE_DECAY_DAYS,
)
from app.models.memory import HealthReport


class GovernanceEngine:
    """Runs deterministic governance rules over expertise, tasks, and brain.

    Designed to be invoked periodically (e.g. every 5 minutes) and caches
    the most recent HealthReport for fast serving.
    """

    def __init__(
        self,
        memory_service: object,
        task_service: object,
        brain_service: object,
    ) -> None:
        from app.services.memory_service import MemoryService
        from app.services.task_service import TaskService
        from app.services.brain_service import BrainService

        self._memory: MemoryService = memory_service  # type: ignore[assignment]
        self._tasks: TaskService = task_service  # type: ignore[assignment]
        self._brain: BrainService = brain_service  # type: ignore[assignment]
        self._cached_report: Optional[HealthReport] = None

    # ------------------------------------------------------------------
    # Main cycle
    # ------------------------------------------------------------------

    def run_cycle(self) -> HealthReport:
        """Execute all governance rules and return a health report."""
        report = HealthReport()
        report.last_governance_run = datetime.now(timezone.utc).isoformat()

        report.archived_this_cycle += self._enforce_ttl()
        report.archived_this_cycle += self._enforce_budget_caps()
        report.archived_this_cycle += self._detect_duplicates()
        report.archived_this_cycle += self._decay_unused()
        report.stale_brain_docs = self._flag_stale_brain_docs()
        report.flagged_conflicts = self._detect_conflicts()
        report.stuck_tasks = self._flag_stuck_tasks()
        report.domains_near_cap = self._domains_near_cap()

        self._cached_report = report
        return report

    def get_health_report(self) -> HealthReport:
        """Return the most recently cached health report."""
        if self._cached_report is None:
            return HealthReport()
        return self._cached_report

    # ------------------------------------------------------------------
    # Rule: TTL enforcement
    # ------------------------------------------------------------------

    def _enforce_ttl(self) -> int:
        """Archive entries that have exceeded their domain shelf life."""
        archived = 0
        now = datetime.now(timezone.utc)

        for domain in self._memory.list_domains():
            shelf_days = DOMAIN_SHELF_LIFE.get(domain, DOMAIN_SHELF_LIFE["default"])
            cutoff = now - timedelta(days=shelf_days)

            entries = self._memory.list_entries(domain, status_filter="active")
            for entry in entries:
                if not entry.recorded_at:
                    continue
                try:
                    recorded = datetime.fromisoformat(entry.recorded_at)
                    if recorded.tzinfo is None:
                        recorded = recorded.replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue
                if recorded < cutoff:
                    self._memory.update_entry(entry.id, status="archived")
                    archived += 1

        return archived

    # ------------------------------------------------------------------
    # Rule: budget caps
    # ------------------------------------------------------------------

    def _enforce_budget_caps(self) -> int:
        """Archive oldest entries when a domain exceeds the budget cap."""
        archived = 0

        for domain in self._memory.list_domains():
            entries = self._memory.list_entries(domain, status_filter="active")
            if len(entries) <= DOMAIN_BUDGET_CAP:
                continue

            # Sort by recorded_at ascending (oldest first)
            entries.sort(key=lambda e: e.recorded_at or "")
            excess = len(entries) - DOMAIN_BUDGET_CAP
            for entry in entries[:excess]:
                self._memory.update_entry(entry.id, status="archived")
                archived += 1

        return archived

    # ------------------------------------------------------------------
    # Rule: duplicate detection
    # ------------------------------------------------------------------

    def _detect_duplicates(self) -> int:
        """Auto-merge near-duplicate entries within each domain.

        Uses SequenceMatcher ratio on name+description. When a duplicate
        pair is found, the newer entry is archived.
        """
        archived = 0

        for domain in self._memory.list_domains():
            entries = self._memory.list_entries(domain, status_filter="active")
            archived_ids: set[str] = set()

            for i in range(len(entries)):
                if entries[i].id in archived_ids:
                    continue
                text_i = f"{entries[i].name} {entries[i].description}"
                for j in range(i + 1, len(entries)):
                    if entries[j].id in archived_ids:
                        continue
                    text_j = f"{entries[j].name} {entries[j].description}"
                    ratio = SequenceMatcher(None, text_i, text_j).ratio()
                    if ratio >= DUPLICATE_THRESHOLD:
                        # Archive the newer entry
                        self._memory.update_entry(entries[j].id, status="archived")
                        archived_ids.add(entries[j].id)
                        archived += 1

        return archived

    # ------------------------------------------------------------------
    # Rule: usage decay
    # ------------------------------------------------------------------

    def _decay_unused(self) -> int:
        """Archive entries that haven't been recalled within the decay window."""
        archived = 0
        now = datetime.now(timezone.utc)
        archive_cutoff = now - timedelta(days=USAGE_ARCHIVE_DAYS)

        for domain in self._memory.list_domains():
            entries = self._memory.list_entries(domain, status_filter="active")
            for entry in entries:
                if entry.recall_count > 0 and entry.last_recalled:
                    try:
                        last = datetime.fromisoformat(entry.last_recalled)
                        if last.tzinfo is None:
                            last = last.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        continue
                    if last < archive_cutoff:
                        self._memory.update_entry(entry.id, status="archived")
                        archived += 1
                elif entry.recall_count == 0 and entry.recorded_at:
                    # Never recalled — check if old enough to archive
                    try:
                        recorded = datetime.fromisoformat(entry.recorded_at)
                        if recorded.tzinfo is None:
                            recorded = recorded.replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        continue
                    if recorded < archive_cutoff:
                        self._memory.update_entry(entry.id, status="archived")
                        archived += 1

        return archived

    # ------------------------------------------------------------------
    # Rule: stale brain docs
    # ------------------------------------------------------------------

    def _flag_stale_brain_docs(self) -> int:
        """Count brain documents that may be stale.

        Uses the brain service status to get a rough count. A more
        sophisticated implementation would compare indexed_at to file
        mtime, but we keep it simple here.
        """
        status = self._brain.status()
        # A rough heuristic: if the brain has docs but hasn't reindexed
        # recently, flag them all
        if not status.get("last_reindex"):
            return status.get("doc_count", 0)
        return 0

    # ------------------------------------------------------------------
    # Rule: conflict detection
    # ------------------------------------------------------------------

    def _detect_conflicts(self) -> int:
        """Flag potentially contradictory entries within each domain.

        Simple heuristic: if two active entries in the same domain share
        keyword overlap and one contains negation words ('not', "don't",
        'never', 'avoid'), flag them as potential conflicts.
        """
        negation_words = {"not", "don't", "dont", "never", "avoid", "shouldn't", "shouldnt"}
        flagged = 0

        for domain in self._memory.list_domains():
            entries = self._memory.list_entries(domain, status_filter="active")
            for i in range(len(entries)):
                words_i = set(f"{entries[i].name} {entries[i].description}".lower().split())
                has_neg_i = bool(words_i & negation_words)

                for j in range(i + 1, len(entries)):
                    words_j = set(
                        f"{entries[j].name} {entries[j].description}".lower().split()
                    )
                    has_neg_j = bool(words_j & negation_words)

                    # Only flag when exactly one side has negation
                    if has_neg_i == has_neg_j:
                        continue

                    # Check keyword overlap (excluding common stop words)
                    content_i = words_i - negation_words
                    content_j = words_j - negation_words
                    overlap = content_i & content_j
                    if len(overlap) >= 2:
                        self._memory.update_entry(entries[j].id, status="needs_review")
                        flagged += 1

        return flagged

    # ------------------------------------------------------------------
    # Rule: stuck tasks
    # ------------------------------------------------------------------

    def _flag_stuck_tasks(self) -> int:
        """Flag tasks that have been in_progress beyond the stale threshold."""
        stuck = 0
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=TASK_STALE_HOURS)

        in_progress = self._tasks.list(status="in_progress")
        for task in in_progress:
            check_time = task.updated_at or task.created_at
            if not check_time:
                continue
            try:
                ts = datetime.fromisoformat(check_time)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if ts < cutoff:
                stuck += 1

        return stuck

    # ------------------------------------------------------------------
    # Helper: domains near cap
    # ------------------------------------------------------------------

    def _domains_near_cap(self) -> list[str]:
        """Return domains at 80% or more of budget cap."""
        near: list[str] = []
        threshold = int(DOMAIN_BUDGET_CAP * 0.8)
        for domain in self._memory.list_domains():
            entries = self._memory.list_entries(domain, status_filter="active")
            if len(entries) >= threshold:
                near.append(domain)
        return near
