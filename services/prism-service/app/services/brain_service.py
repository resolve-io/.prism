"""Brain service — wrapper over the Brain engine."""

from __future__ import annotations

import sqlite3
import sys
from typing import Optional


import re as _re

_CAMEL_RE = _re.compile(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')


def _expand_identifiers(text: str) -> str:
    """Expand PascalCase/camelCase identifiers for better FTS matching.

    'FreshnessStatus' → 'FreshnessStatus Freshness Status'
    'getMatchesHandler' → 'getMatchesHandler get Matches Handler'

    Keeps original term + adds split parts so both exact and partial matches work.
    """
    words = text.split()
    expanded = []
    for word in words:
        expanded.append(word)
        # Only split words that look like identifiers (contain mixed case)
        if _CAMEL_RE.search(word) and len(word) > 2:
            parts = _CAMEL_RE.sub(' ', word).split()
            if len(parts) > 1:
                expanded.extend(parts)
    return ' '.join(expanded)


class BrainService:
    """Thin service layer over the Brain engine.

    Provides a single shared Brain instance and convenience methods
    callable from both the UI and MCP layers.
    """

    _brain = None
    _available: bool = False

    def __init__(self, brain_db: str, graph_db: str, scores_db: str) -> None:
        self._brain_db = brain_db
        self._graph_db = graph_db
        self._scores_db = scores_db
        self._init_brain()

    def _init_brain(self) -> None:
        """Attempt to initialise the Brain engine."""
        try:
            from app.engines.brain_engine import Brain

            self._brain = Brain(
                brain_db=self._brain_db,
                graph_db=self._graph_db,
                scores_db=self._scores_db,
            )
            self._available = True
        except Exception as exc:
            print(
                f"BrainService: Brain unavailable ({exc})",
                file=sys.stderr,
            )
            self._brain = None
            self._available = False

    # ------------------------------------------------------------------
    # Delegated methods
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
        domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """Search the knowledge base.

        Expands PascalCase/camelCase terms in the query so 'FreshnessStatus'
        matches documents containing 'Freshness' or 'Status' as well.
        """
        if not self._available or self._brain is None:
            return []
        expanded_query = _expand_identifiers(query)
        return self._brain.search(expanded_query, domain=domain, limit=limit, domains=domains)

    def system_context(
        self,
        story_file: Optional[str] = None,
        persona: Optional[str] = None,
        limit: int = 8,
    ) -> str:
        """Build system context string from Brain."""
        if not self._available or self._brain is None:
            return ""
        return self._brain.system_context(
            story_file=story_file, persona=persona, limit=limit,
        )

    def list_docs(
        self, domain: Optional[str] = None, limit: int = 100,
    ) -> list[dict]:
        """List indexed documents. Returns doc_id, domain, content_length."""
        if not self._available or self._brain is None:
            return []
        conn = self._brain._brain
        if domain:
            rows = conn.execute(
                "SELECT id, domain, length(content) as len FROM docs "
                "WHERE domain = ? ORDER BY id LIMIT ?",
                (domain, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, domain, length(content) as len FROM docs "
                "ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"doc_id": r[0], "domain": r[1], "content_length": r[2]} for r in rows]

    def graph_query(
        self,
        entity: str,
        relation: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Query the knowledge graph."""
        if not self._available or self._brain is None:
            return []
        return self._brain.graph_query(entity, relation=relation, limit=limit)

    def ingest(self, sources: list[str]) -> int:
        """Ingest source files into the knowledge base."""
        if not self._available or self._brain is None:
            return 0
        return self._brain.ingest(sources)

    def incremental_reindex(self) -> int:
        """Re-index changed files. Returns count of updated docs."""
        if not self._available or self._brain is None:
            return 0
        return self._brain.incremental_reindex()

    def index_doc(
        self,
        path: str,
        content: str,
        domain: str = "code",
        entities: list[dict] | None = None,
    ) -> str:
        """Index a document directly from content (no filesystem access needed).

        Claude reads the file on the host and sends content via MCP.
        Brain stores and indexes it for future search.

        Uses the Brain engine's own DB connections so FTS triggers fire.

        Returns the doc_id.
        """
        from datetime import datetime, timezone

        doc_id = f"{path}::main"
        now = datetime.now(timezone.utc).isoformat()
        filename = path.rsplit("/", 1)[-1] if "/" in path else path

        if not self._available or self._brain is None:
            return doc_id  # silently skip if Brain not available

        # Use the Brain engine's own connections so search sees the new data.
        # self._brain is the Brain engine instance.
        # self._brain._brain is its sqlite3 connection to brain.db.
        brain_conn = self._brain._brain

        # Expand PascalCase/camelCase for better FTS matching
        expanded_content = _expand_identifiers(content)

        # Hash the RAW content (not expanded) so callers can diff against
        # on-disk sha256 for drift detection via prism_status.
        import hashlib as _hashlib
        content_hash = _hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Delete first so the AFTER INSERT trigger fires for FTS sync
        brain_conn.execute("DELETE FROM docs WHERE id = ?", (doc_id,))
        brain_conn.execute(
            "INSERT INTO docs "
            "(id, source_file, content, domain, indexed_at, "
            " entity_name, entity_kind, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, path, expanded_content, domain, now,
             filename, "file", content_hash),
        )

        # Populate vector index so semantic search sees MCP-ingested docs.
        if getattr(self._brain, "vector_enabled", False):
            vec = self._brain._embed(content)
            if vec is not None:
                import struct
                blob = struct.pack(f"{len(vec)}f", *vec)
                try:
                    brain_conn.execute(
                        "DELETE FROM docs_vec WHERE doc_id = ?", (doc_id,)
                    )
                    brain_conn.execute(
                        "INSERT INTO docs_vec (doc_id, embedding) VALUES (?, ?)",
                        (doc_id, blob),
                    )
                except Exception as e:
                    print(f"index_doc vec insert failed: {e!r}",
                          file=sys.stderr, flush=True)

        brain_conn.commit()

        # Index entities into graph.db if provided
        if entities:
            graph_conn = self._brain._graph
            for ent in entities:
                ent_name = ent.get("name", "")
                ent_kind = ent.get("kind", "unknown")
                if ent_name:
                    graph_conn.execute(
                        "INSERT OR IGNORE INTO entities (name, kind, file) VALUES (?, ?, ?)",
                        (ent_name, ent_kind, path),
                    )
            graph_conn.commit()

        # Stage source file for the graphify code-graph pass.
        # graph_svc is wired in by ProjectContext when available; if the doc
        # has a known source-code suffix, stage_doc writes it to the project's
        # graphify-src/ dir so a later graph_rebuild picks it up.
        graph_svc = getattr(self, "graph_svc", None)
        if graph_svc is not None:
            try:
                graph_svc.stage_doc(path, content)
            except Exception as e:
                print(f"index_doc: graph staging failed: {e!r}",
                      file=sys.stderr, flush=True)

        return doc_id

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Return summary statistics about the Brain databases.

        Returns dict with doc_count, entity_count, vector_enabled,
        last_reindex.
        """
        result: dict = {
            "doc_count": 0,
            "entity_count": 0,
            "vector_enabled": False,
            "last_reindex": "",
            "available": self._available,
        }
        if not self._available:
            return result

        try:
            conn = sqlite3.connect(self._brain_db)
            row = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
            result["doc_count"] = row[0] if row else 0
            # Check for last reindex timestamp if the column exists
            try:
                ts_row = conn.execute(
                    "SELECT MAX(indexed_at) FROM documents"
                ).fetchone()
                result["last_reindex"] = ts_row[0] or "" if ts_row else ""
            except sqlite3.OperationalError:
                pass
            conn.close()
        except Exception:
            pass

        try:
            conn = sqlite3.connect(self._graph_db)
            row = conn.execute("SELECT COUNT(DISTINCT entity) FROM triples").fetchone()
            result["entity_count"] = row[0] if row else 0
            conn.close()
        except Exception:
            pass

        try:
            result["vector_enabled"] = getattr(self._brain, "_vec_available", False)
        except Exception:
            pass

        return result
