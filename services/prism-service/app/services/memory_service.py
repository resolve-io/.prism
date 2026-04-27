"""Memory service — manages mulch expertise JSONL files with learning loop."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.memory import ExpertiseEntry


_CREATE_RECALL_LOG_SQL = """
CREATE TABLE IF NOT EXISTS recall_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    entry_domain TEXT DEFAULT '',
    query TEXT DEFAULT '',
    recalled_at TEXT NOT NULL,
    task_id TEXT DEFAULT '',
    outcome TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_recall_log_task ON recall_log(task_id);
CREATE INDEX IF NOT EXISTS idx_recall_log_entry ON recall_log(entry_id);
"""


class MemoryService:
    """Reads and writes expertise entries stored as JSONL files in mulch.

    Each domain has its own ``{domain}.jsonl`` file under the expertise
    subdirectory of MULCH_DIR.

    The recall_log (SQLite) tracks which entries were recalled during which
    tasks, enabling automatic effectiveness scoring from task outcomes.
    """

    def __init__(self, mulch_dir: str, task_svc: object = None) -> None:
        self._dir = Path(mulch_dir) / "expertise"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._task_svc = task_svc

        # Recall log DB — operational data, separate from expertise JSONL
        recall_db_path = Path(mulch_dir) / "recall_log.db"
        self._recall_db = sqlite3.connect(str(recall_db_path), check_same_thread=False)
        self._recall_db.execute("PRAGMA journal_mode=WAL")
        self._recall_db.execute("PRAGMA busy_timeout=5000")
        self._recall_db.executescript(_CREATE_RECALL_LOG_SQL)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _domain_file(self, domain: str) -> Path:
        """Return the JSONL path for a domain."""
        safe = domain.replace("/", "_").replace("\\", "_")
        return self._dir / f"{safe}.jsonl"

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique entry ID in mx-XXXXXX format."""
        return f"mx-{secrets.token_hex(3)}"

    @staticmethod
    def _entry_from_dict(data: dict) -> ExpertiseEntry:
        """Construct an ExpertiseEntry from a JSON dict."""
        return ExpertiseEntry(
            id=data.get("id", ""),
            type=data.get("type", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            classification=data.get("classification", ""),
            recorded_at=data.get("recorded_at", ""),
            outcomes=data.get("outcomes", []),
            evidence=data.get("evidence", {}),
            domain=data.get("domain", ""),
            recall_count=data.get("recall_count", 0),
            last_recalled=data.get("last_recalled", ""),
            status=data.get("status", "active"),
            valid_at=data.get("valid_at", ""),
            invalid_at=data.get("invalid_at", ""),
            importance=data.get("importance", 5),
            memory_type=data.get("memory_type", "semantic"),
            generation=data.get("generation", 1),
            effectiveness=data.get("effectiveness", 0.0),
        )

    @staticmethod
    def _entry_to_dict(entry: ExpertiseEntry) -> dict:
        """Serialize an ExpertiseEntry to a JSON-safe dict."""
        return {
            "id": entry.id,
            "type": entry.type,
            "name": entry.name,
            "description": entry.description,
            "classification": entry.classification,
            "recorded_at": entry.recorded_at,
            "outcomes": entry.outcomes,
            "evidence": entry.evidence,
            "domain": entry.domain,
            "recall_count": entry.recall_count,
            "last_recalled": entry.last_recalled,
            "status": entry.status,
            "valid_at": entry.valid_at,
            "invalid_at": entry.invalid_at,
            "importance": entry.importance,
            "memory_type": entry.memory_type,
            "generation": entry.generation,
            "effectiveness": entry.effectiveness,
        }

    def _read_entries(self, domain: str) -> list[ExpertiseEntry]:
        """Load all entries from a domain file."""
        path = self._domain_file(domain)
        if not path.exists():
            return []
        entries: list[ExpertiseEntry] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(self._entry_from_dict(data))
            except json.JSONDecodeError:
                continue
        return entries

    def _write_entries(self, domain: str, entries: list[ExpertiseEntry]) -> None:
        """Overwrite a domain file with the given entries."""
        path = self._domain_file(domain)
        lines = [json.dumps(self._entry_to_dict(e)) for e in entries]
        path.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")

    def _all_entries(self) -> list[ExpertiseEntry]:
        """Load entries across all domains."""
        entries: list[ExpertiseEntry] = []
        for domain in self.list_domains():
            entries.extend(self._read_entries(domain))
        return entries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        domain: str,
        name: str,
        description: str,
        type: str,
        classification: str,
        evidence: Optional[dict] = None,
        importance: int = 5,
        memory_type: str = "semantic",
    ) -> ExpertiseEntry:
        """Create and persist a new expertise entry.

        Temporal dedup: if an active entry with the same name or >85%
        description similarity exists, the OLD entry is invalidated
        (invalid_at set) and a NEW entry is created. This preserves
        history while preventing rot.
        """
        from difflib import SequenceMatcher

        now = datetime.now(timezone.utc).isoformat()
        entries = self._read_entries(domain)
        superseded = None

        # Check for exact name match
        for existing in entries:
            if existing.status != "active" or existing.invalid_at:
                continue
            if existing.name == name:
                superseded = existing
                break

        # Check for high description similarity if no name match
        if not superseded:
            for existing in entries:
                if existing.status != "active" or existing.invalid_at:
                    continue
                ratio = SequenceMatcher(
                    None, existing.description.lower(), description.lower()
                ).ratio()
                if ratio > 0.85:
                    superseded = existing
                    break

        # Invalidate the old entry (don't delete — preserve history)
        next_generation = 1
        if superseded:
            superseded.invalid_at = now
            superseded.status = "archived"
            next_generation = superseded.generation + 1

        # Create new entry with valid_at
        entry = ExpertiseEntry(
            id=self._generate_id(),
            type=type,
            name=name,
            description=description,
            classification=classification,
            recorded_at=now,
            evidence=evidence or {},
            domain=domain,
            valid_at=now,
            importance=importance,
            memory_type=memory_type,
            generation=next_generation,
        )
        entries.append(entry)
        self._write_entries(domain, entries)

        # Also index into Brain for FTS search
        self._index_in_brain(entry)

        return entry

    def _index_in_brain(self, entry: ExpertiseEntry) -> None:
        """Index a memory entry into Brain's FTS5 for full-text recall."""
        try:
            from app.project_context import get_project
            # Find the project context that owns this memory service
            # by matching the mulch dir path
            import re
            match = re.search(r'projects/([^/]+)/', str(self._dir))
            if not match:
                return
            project_id = match.group(1)
            ctx = get_project(project_id)
            content = f"{entry.name}\n{entry.description}"
            if entry.evidence:
                content += f"\nEvidence: {json.dumps(entry.evidence)}"
            ctx.brain_svc.index_doc(
                path=f"memory/{entry.domain}/{entry.id}",
                content=content,
                domain="expertise",
            )
        except Exception:
            pass  # Best-effort — Brain may not be available

    def recall(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> list[ExpertiseEntry]:
        """Search expertise entries using Brain FTS5 with keyword fallback.

        Primary: routes through Brain's hybrid search (BM25 + graph)
        filtered to domain='expertise'. This handles natural language
        queries far better than simple keyword overlap.

        Fallback: if Brain search returns nothing, falls back to
        keyword overlap on name + description.

        Only returns active, temporally valid entries.
        """
        results: list[ExpertiseEntry] = []

        # Primary: Brain FTS5 search
        try:
            results = self._brain_recall(query, domain, limit * 2)
        except Exception:
            pass

        # Fallback: keyword overlap
        if not results:
            results = self._keyword_recall(query, domain, limit * 2)

        # Filter: only active + temporally valid (no invalid_at)
        results = [
            e for e in results
            if e.status == "active" and not e.invalid_at
        ]

        # Domain filter (Brain search may return cross-domain)
        if domain:
            results = [e for e in results if e.domain == domain]

        # Domain fallback: if we still have fewer results than requested,
        # supplement with remaining active entries from the domain file
        if domain and len(results) < limit:
            seen_ids = {e.id for e in results}
            extras = [
                e for e in self._read_entries(domain)
                if e.status == "active" and not e.invalid_at and e.id not in seen_ids
            ]
            results.extend(extras)

        # Sort by importance + effectiveness blend, then recall_count
        results.sort(
            key=lambda e: (e.importance + e.effectiveness * 2, e.recall_count),
            reverse=True,
        )

        # Update recall stats + log for learning loop
        now = datetime.now(timezone.utc).isoformat()
        current_task_id = self._get_current_task_id()
        for entry in results[:limit]:
            self._record_recall_stat(entry, now)
            self._log_recall(entry, query, now, current_task_id)

        return results[:limit]

    def _brain_recall(
        self, query: str, domain: Optional[str], limit: int,
    ) -> list[ExpertiseEntry]:
        """Search via Brain FTS5 for expertise-domain docs, then hydrate.

        Converts query words to OR-joined tokens for FTS5 so that
        partial-match queries like "never avoid do not" find entries
        containing ANY of those words rather than requiring ALL.
        """
        import re
        match = re.search(r'projects[/\\]([^/\\]+)[/\\]', str(self._dir))
        if not match:
            return []
        project_id = match.group(1)

        # Convert query to OR-joined FTS5 tokens for broader matching
        words = re.sub(r"[^\w\s]", " ", query).split()
        or_query = " OR ".join(w for w in words if len(w) > 2)
        if not or_query:
            or_query = query

        from app.project_context import get_project
        ctx = get_project(project_id)
        hits = ctx.brain_svc.search(or_query, domain="expertise", limit=limit)

        # Hydrate: match Brain doc_ids back to JSONL entries
        entry_map = {}
        for e in self._all_entries():
            entry_map[e.id] = e

        results = []
        for hit in hits:
            doc_id = hit.get("doc_id", "")
            # doc_id format: memory/{domain}/{mx-id}::main
            parts = doc_id.replace("::main", "").split("/")
            if len(parts) >= 3:
                entry_id = parts[-1]
                if entry_id in entry_map:
                    results.append(entry_map[entry_id])
        return results

    def _keyword_recall(
        self, query: str, domain: Optional[str], limit: int,
    ) -> list[ExpertiseEntry]:
        """Fallback keyword-overlap + substring search.

        Combines word-set overlap with substring matching so that
        short descriptions still match relevant queries.  Name tokens
        are weighted 2x because they're usually the most distinctive.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        if not query_words and not query_lower.strip():
            return []

        candidates = self._read_entries(domain) if domain else self._all_entries()
        candidates = [e for e in candidates if e.status == "active"]

        scored: list[tuple[float, ExpertiseEntry]] = []
        for entry in candidates:
            # Include type, domain, and name in searchable text
            name_text = entry.name.replace("-", " ").replace("/", " ").lower()
            desc_text = entry.description.lower()
            full_text = f"{name_text} {desc_text} {entry.type} {entry.domain}"
            text_words = set(full_text.split())

            # Word overlap (name tokens weighted 2x)
            name_words = set(name_text.split())
            name_overlap = len(query_words & name_words) * 2
            desc_overlap = len(query_words & text_words)
            score = name_overlap + desc_overlap

            # Substring matching for multi-word phrases and short texts
            for qw in query_words:
                if len(qw) > 2 and qw in full_text and qw not in text_words:
                    score += 0.5  # partial substring match

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]

    def _record_recall_stat(self, entry: ExpertiseEntry, now: str) -> None:
        """Increment recall_count and last_recalled for an entry."""
        try:
            entries = self._read_entries(entry.domain)
            for e in entries:
                if e.id == entry.id:
                    e.recall_count += 1
                    e.last_recalled = now
                    break
            self._write_entries(entry.domain, entries)
        except Exception:
            pass

    def list_domains(self) -> list[str]:
        """Return domain names derived from .jsonl file names."""
        domains: list[str] = []
        for path in sorted(self._dir.glob("*.jsonl")):
            domains.append(path.stem)
        return domains

    def list_entries(
        self,
        domain: str,
        type_filter: Optional[str] = None,
        classification_filter: Optional[str] = None,
        status_filter: str = "active",
    ) -> list[ExpertiseEntry]:
        """List entries in a domain with optional filters."""
        entries = self._read_entries(domain)

        if status_filter:
            entries = [e for e in entries if e.status == status_filter]
        if type_filter:
            entries = [e for e in entries if e.type == type_filter]
        if classification_filter:
            entries = [e for e in entries if e.classification == classification_filter]

        return entries

    def get_entry(self, entry_id: str) -> Optional[ExpertiseEntry]:
        """Look up a single entry by ID across all domains."""
        for entry in self._all_entries():
            if entry.id == entry_id:
                return entry
        return None

    def update_entry(self, entry_id: str, **kwargs: object) -> Optional[ExpertiseEntry]:
        """Update fields on an existing entry and persist."""
        for domain in self.list_domains():
            entries = self._read_entries(domain)
            for i, entry in enumerate(entries):
                if entry.id != entry_id:
                    continue
                for key, value in kwargs.items():
                    if hasattr(entry, key) and key != "id":
                        setattr(entry, key, value)
                entries[i] = entry
                self._write_entries(domain, entries)
                return entry
        return None

    def record_recall(self, entry_id: str) -> None:
        """Increment recall_count and update last_recalled timestamp."""
        for domain in self.list_domains():
            entries = self._read_entries(domain)
            for i, entry in enumerate(entries):
                if entry.id != entry_id:
                    continue
                entry.recall_count += 1
                entry.last_recalled = datetime.now(timezone.utc).isoformat()
                entries[i] = entry
                self._write_entries(domain, entries)
                return

    # ------------------------------------------------------------------
    # Learning loop — recall logging and outcome correlation
    # ------------------------------------------------------------------

    def _get_current_task_id(self) -> str:
        """Find the in_progress task ID from task_svc, if available."""
        if self._task_svc is None:
            return ""
        try:
            in_progress = self._task_svc.list(status="in_progress")
            if in_progress:
                return in_progress[0].id
        except Exception:
            pass
        return ""

    def _log_recall(
        self, entry: ExpertiseEntry, query: str, now: str, task_id: str,
    ) -> None:
        """Log a recall event for later outcome correlation."""
        try:
            self._recall_db.execute(
                "INSERT INTO recall_log (entry_id, entry_domain, query, recalled_at, task_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (entry.id, entry.domain, query, now, task_id),
            )
            self._recall_db.commit()
        except Exception:
            pass

    def record_outcome(self, task_id: str, outcome: str) -> int:
        """Record task outcome against all recalls for that task.

        Called when a task transitions to done (positive) or blocked (negative).
        Updates recall_log rows and recalculates effectiveness on affected entries.
        Returns count of recall_log rows updated.
        """
        if not task_id:
            return 0

        # Update all recall_log rows for this task
        cur = self._recall_db.execute(
            "UPDATE recall_log SET outcome = ? WHERE task_id = ? AND outcome = ''",
            (outcome, task_id),
        )
        self._recall_db.commit()
        updated = cur.rowcount

        if updated == 0:
            return 0

        # Get distinct entry IDs affected
        rows = self._recall_db.execute(
            "SELECT DISTINCT entry_id FROM recall_log WHERE task_id = ?",
            (task_id,),
        ).fetchall()

        # Recalculate effectiveness for each affected entry
        for (entry_id,) in rows:
            self._recalculate_effectiveness(entry_id)

        return updated

    def _recalculate_effectiveness(self, entry_id: str) -> None:
        """Recalculate effectiveness score for an entry from its recall_log.

        Score = (positive_count - negative_count) / total_with_outcome
        Range: -1.0 to +1.0. Entries with no outcomes stay at 0.0.
        """
        rows = self._recall_db.execute(
            "SELECT outcome, COUNT(*) FROM recall_log "
            "WHERE entry_id = ? AND outcome != '' GROUP BY outcome",
            (entry_id,),
        ).fetchall()

        if not rows:
            return

        counts = {outcome: count for outcome, count in rows}
        positive = counts.get("positive", 0)
        negative = counts.get("negative", 0)
        total = positive + negative

        if total == 0:
            return

        score = (positive - negative) / total

        # Persist to the JSONL entry
        entry = self.get_entry(entry_id)
        if entry:
            self.update_entry(entry_id, effectiveness=round(score, 3))

    def get_effectiveness_scores(self) -> dict[str, dict]:
        """Aggregate effectiveness data for governance.

        Returns {entry_id: {positive: N, negative: N, total: N, score: float}}
        for entries that have at least one outcome.
        """
        rows = self._recall_db.execute(
            "SELECT entry_id, outcome, COUNT(*) FROM recall_log "
            "WHERE outcome != '' GROUP BY entry_id, outcome"
        ).fetchall()

        scores: dict[str, dict] = {}
        for entry_id, outcome, count in rows:
            if entry_id not in scores:
                scores[entry_id] = {"positive": 0, "negative": 0}
            scores[entry_id][outcome] = count

        for entry_id, data in scores.items():
            total = data["positive"] + data["negative"]
            data["total"] = total
            data["score"] = round((data["positive"] - data["negative"]) / total, 3) if total else 0.0

        return scores

    def domain_stats(self) -> dict:
        """Return entry counts per domain and archived totals."""
        stats: dict = {}
        for domain in self.list_domains():
            entries = self._read_entries(domain)
            active = sum(1 for e in entries if e.status == "active")
            archived = sum(1 for e in entries if e.status == "archived")
            stats[domain] = {"active": active, "archived": archived, "total": len(entries)}
        return stats
