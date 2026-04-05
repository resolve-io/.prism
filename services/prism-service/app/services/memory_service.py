"""Memory service — manages mulch expertise JSONL files."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.memory import ExpertiseEntry


class MemoryService:
    """Reads and writes expertise entries stored as JSONL files in mulch.

    Each domain has its own ``{domain}.jsonl`` file under the expertise
    subdirectory of MULCH_DIR.
    """

    def __init__(self, mulch_dir: str) -> None:
        self._dir = Path(mulch_dir) / "expertise"
        self._dir.mkdir(parents=True, exist_ok=True)

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
        if superseded:
            superseded.invalid_at = now
            superseded.status = "archived"

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

        # Sort by importance descending, then recall_count
        results.sort(key=lambda e: (e.importance, e.recall_count), reverse=True)

        # Update recall stats
        now = datetime.now(timezone.utc).isoformat()
        for entry in results[:limit]:
            self._record_recall_stat(entry, now)

        return results[:limit]

    def _brain_recall(
        self, query: str, domain: Optional[str], limit: int,
    ) -> list[ExpertiseEntry]:
        """Search via Brain FTS5 for expertise-domain docs, then hydrate."""
        import re
        match = re.search(r'projects/([^/]+)/', str(self._dir))
        if not match:
            return []
        project_id = match.group(1)

        from app.project_context import get_project
        ctx = get_project(project_id)
        hits = ctx.brain_svc.search(query, domain="expertise", limit=limit)

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
        """Fallback keyword-overlap search."""
        query_words = set(query.lower().split())
        if not query_words:
            return []

        candidates = self._read_entries(domain) if domain else self._all_entries()
        candidates = [e for e in candidates if e.status == "active"]

        scored: list[tuple[float, ExpertiseEntry]] = []
        for entry in candidates:
            text = f"{entry.name} {entry.description}".lower()
            text_words = set(text.split())
            overlap = len(query_words & text_words)
            if overlap > 0:
                scored.append((overlap, entry))

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

    def domain_stats(self) -> dict:
        """Return entry counts per domain and archived totals."""
        stats: dict = {}
        for domain in self.list_domains():
            entries = self._read_entries(domain)
            active = sum(1 for e in entries if e.status == "active")
            archived = sum(1 for e in entries if e.status == "archived")
            stats[domain] = {"active": active, "archived": archived, "total": len(entries)}
        return stats
