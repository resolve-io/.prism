"""Brain service — wrapper over the Brain engine."""

from __future__ import annotations

import os as _os
import sqlite3
import sys
from typing import Optional

from app.engines.brain_engine import _expand_identifiers


def _build_context_header(
    source_file: str,
    entity_name: Optional[str],
    entity_kind: Optional[str],
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
) -> str:
    """Short structural prefix prepended to a chunk before embedding/BM25.

    Anthropic Contextual Retrieval: anchoring a chunk in its parent document
    (path, qualified name, line range) cuts retrieval failures 35-67% without
    any LLM call. We use structural metadata we already carry per chunk.
    """
    lines = [f"File: {source_file}"]
    if entity_name == "__file__":
        lines.append("Scope: entire file")
    elif entity_name == "__module__":
        lines.append("Scope: module-level code outside any function or class")
    elif entity_kind == "window":
        if line_start and line_end:
            lines.append(f"Scope: window over lines {line_start}-{line_end}")
        else:
            lines.append("Scope: sliding window")
    elif entity_name and entity_kind:
        qual = f"{entity_kind} {entity_name}"
        if line_start and line_end:
            qual += f" (lines {line_start}-{line_end})"
        lines.append(f"Scope: {qual}")
    return "\n".join(lines)


class BrainService:
    """Thin service layer over the Brain engine.

    Provides a single shared Brain instance and convenience methods
    callable from both the UI and MCP layers.
    """

    _brain = None
    _available: bool = False

    def __init__(
        self, brain_db: str, graph_db: str, scores_db: str,
        tasks_db: Optional[str] = None,
    ) -> None:
        self._brain_db = brain_db
        self._graph_db = graph_db
        self._scores_db = scores_db
        self._tasks_db = tasks_db
        self._init_brain()

    def _init_brain(self) -> None:
        """Attempt to initialise the Brain engine."""
        try:
            from app.engines.brain_engine import Brain

            self._brain = Brain(
                brain_db=self._brain_db,
                graph_db=self._graph_db,
                scores_db=self._scores_db,
                tasks_db=self._tasks_db,
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

    def recent_searches(self, limit: int = 50) -> list[dict]:
        """Return the most recent ``limit`` search events from brain.db."""
        if not self._available or self._brain is None:
            return []
        return self._brain.get_recent_searches(limit=limit)

    def record_search_feedback(
        self,
        search_id: int,
        doc_id: str,
        signal: str,
        note: Optional[str] = None,
    ) -> Optional[int]:
        """Write one thumbs-up/thumbs-down on a search result doc."""
        if not self._available or self._brain is None:
            return None
        return self._brain.record_search_feedback(
            search_id=search_id, doc_id=doc_id,
            signal=signal, note=note,
        )

    def search_feedback(self, search_id: int) -> list[dict]:
        """Return all feedback rows tied to ``search_id``."""
        if not self._available or self._brain is None:
            return []
        return self._brain.get_search_feedback(search_id=search_id)

    def feedback_stats(self) -> dict:
        """Aggregate up/down counts + worst-offender docs."""
        if not self._available or self._brain is None:
            return {"up": 0, "down": 0, "worst": []}
        return self._brain.feedback_stats()

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

    def find_symbol(
        self,
        name: str,
        kind: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Find chunks matching entity_name; token-efficient alternative to Read."""
        if not self._available or self._brain is None:
            return []
        return self._brain.find_symbol(name=name, kind=kind, limit=limit)

    def outline(self, source_file: str) -> list[dict]:
        """Return symbol outline of a file — metadata only, ~200 tokens."""
        if not self._available or self._brain is None:
            return []
        return self._brain.outline(source_file=source_file)

    def find_references(
        self, name: str, limit: int = 20,
    ) -> list[dict]:
        """Return callers of ``name`` from the graph (caller_name/kind/file)."""
        if not self._available or self._brain is None:
            return []
        return self._brain.find_references(name=name, limit=limit)

    def call_chain(
        self, entity: str, depth: int = 2, limit: int = 50,
    ) -> list[dict]:
        """Bounded BFS over the call graph from ``entity``."""
        if not self._available or self._brain is None:
            return []
        return self._brain.call_chain(
            entity=entity, depth=depth, limit=limit,
        )

    def record_session_outcome(
        self, session_id: str, duration_s: int, tokens_used: int,
        files_read: int, files_modified: int, skills_invoked: int,
    ) -> bool:
        """Persist one session outcome row (server-side scores.db)."""
        if not self._available or self._brain is None:
            return False
        try:
            self._brain.record_session_outcome(
                session_id=session_id, duration_s=int(duration_s),
                tokens_used=int(tokens_used), files_read=int(files_read),
                files_modified=int(files_modified),
                skills_invoked=int(skills_invoked),
            )
            return True
        except Exception:
            return False

    def record_skill_usage(
        self, session_id: str, skill_name: str,
        timestamp: str = "",
    ) -> bool:
        """Persist one skill invocation row."""
        if not self._available or self._brain is None:
            return False
        try:
            self._brain.record_skill_usage(
                session_id=session_id, skill_name=skill_name,
                timestamp=timestamp,
            )
            return True
        except Exception:
            return False

    def record_outcome(
        self, prompt_id: str, persona: str, step_id: str, metrics: dict,
    ) -> bool:
        """Persist one PSP-scored execution outcome (subagents + workflow)."""
        if not self._available or self._brain is None:
            return False
        try:
            self._brain.record_outcome(
                prompt_id=prompt_id, persona=persona,
                step_id=step_id, metrics=metrics or {},
            )
            return True
        except Exception:
            return False

    def record_subagent_outcome(
        self, prompt_id: str, validator: str, recommendation: str,
        evidence_count: int = 0, certificate_complete: int = 0,
        certificate_blocked: int = 0, timed_out: int = 0,
        tokens_used: int = 0, duration_s: float = 0.0,
    ) -> bool:
        """Persist one SFR outcome row for a validator sub-agent."""
        if not self._available or self._brain is None:
            return False
        try:
            self._brain.record_subagent_outcome(
                prompt_id=prompt_id, validator=validator,
                recommendation=recommendation,
                evidence_count=evidence_count,
                certificate_complete=certificate_complete,
                certificate_blocked=certificate_blocked,
                timed_out=timed_out, tokens_used=tokens_used,
                duration_s=duration_s,
            )
            return True
        except Exception:
            return False

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
        """Index a document, chunked at function/class boundaries when possible.

        Code files (suffix in _TS_LANG_MAP): chunked via Brain._chunk_source_file
        into per-function/class docs with ``path::EntityName`` ids, each with
        its own embedding. Prose (md/txt): single whole-file doc with
        ``path::main`` (legacy id format preserved for backward-compat).

        Replaces any prior chunks for the same source_file so re-indexing
        leaves no stale rows. Returns the first chunk's doc_id.
        """
        from datetime import datetime, timezone
        import hashlib as _hashlib
        import struct

        if not self._available or self._brain is None:
            return f"{path}::main"

        brain_conn = self._brain._brain
        now = datetime.now(timezone.utc).isoformat()
        vector_on = getattr(self._brain, "vector_enabled", False)

        # Purge any prior rows for this source file (by source_file column,
        # plus the legacy path::main and path-only ids) so a re-index leaves
        # no stale chunks behind.
        stale = brain_conn.execute(
            "SELECT id FROM docs WHERE source_file = ? OR id = ? OR id = ?",
            (path, path, f"{path}::main"),
        ).fetchall()
        stale_ids = [r[0] for r in stale]
        if stale_ids:
            ph = ",".join("?" * len(stale_ids))
            if vector_on:
                try:
                    brain_conn.execute(
                        f"DELETE FROM docs_vec WHERE doc_id IN ({ph})",
                        stale_ids,
                    )
                except Exception:
                    pass
            brain_conn.execute(
                f"DELETE FROM docs WHERE id IN ({ph})", stale_ids,
            )

        # Chunk via Brain's native chunker (tree-sitter for .py, regex
        # fallback for .ts/.tsx/.js/.jsx/.cs, whole-file for everything else).
        chunks = self._brain._chunk_source_file(path, content)

        first_doc_id = ""
        for chunk in chunks:
            doc_id = chunk["doc_id"]
            # Non-code files come back with doc_id == filepath (no "::").
            # Normalise to the legacy path::main form for prose compat.
            if "::" not in doc_id:
                doc_id = f"{path}::main"
            if not first_doc_id:
                first_doc_id = doc_id

            chunk_content = chunk["content"]
            # Contextual prefix (PRISM_CONTEXT_PREFIX=on default): prepend a
            # short header with file path + entity scope so the embedder and
            # BM25 see chunks anchored in their parent document. Hash and the
            # chunker's raw content are unchanged so drift detection still
            # aligns with on-disk sha256.
            if _os.environ.get(
                "PRISM_CONTEXT_PREFIX", "on"
            ).strip().lower() != "off":
                header = _build_context_header(
                    path,
                    chunk.get("entity_name"),
                    chunk.get("entity_kind"),
                    chunk.get("line_start"),
                    chunk.get("line_end"),
                )
                indexed_content = (
                    f"{header}\n\n{chunk_content}" if header else chunk_content
                )
            else:
                indexed_content = chunk_content
            # Hash RAW chunk content so prism_status drift detection still
            # lines up with on-disk sha256 when the file is single-chunk.
            chash = _hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()

            # docs.content stores the RAW chunk (with optional contextual
            # header). Identifier expansion happens in the FTS5 trigger
            # via expand_identifiers() — see brain_engine._init_brain_schema.
            # Fix for resolve-io/.prism#34: previously this wrote the
            # pre-expanded form, corrupting any consumer of docs.content
            # (notably graph_service.backfill_from_brain).
            brain_conn.execute(
                "INSERT INTO docs "
                "(id, source_file, content, domain, indexed_at, "
                " entity_name, entity_kind, content_hash, "
                " line_start, line_end) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, path, indexed_content, domain, now,
                 chunk["entity_name"], chunk["entity_kind"], chash,
                 chunk["line_start"], chunk["line_end"]),
            )

            if vector_on:
                vec = self._brain._embed(indexed_content)
                if vec is not None:
                    blob = struct.pack(f"{len(vec)}f", *vec)
                    try:
                        brain_conn.execute(
                            "INSERT INTO docs_vec (doc_id, embedding) "
                            "VALUES (?, ?)",
                            (doc_id, blob),
                        )
                    except Exception as e:
                        print(f"index_doc vec insert failed: {e!r}",
                              file=sys.stderr, flush=True)

        brain_conn.commit()

        # Index caller-supplied entities into graph.db (unchanged).
        if entities:
            graph_conn = self._brain._graph
            for ent in entities:
                ent_name = ent.get("name", "")
                ent_kind = ent.get("kind", "unknown")
                if ent_name:
                    graph_conn.execute(
                        "INSERT OR IGNORE INTO entities (name, kind, file) "
                        "VALUES (?, ?, ?)",
                        (ent_name, ent_kind, path),
                    )
            graph_conn.commit()

        # Stage source for graphify's code-graph pass (unchanged).
        graph_svc = getattr(self, "graph_svc", None)
        if graph_svc is not None:
            try:
                graph_svc.stage_doc(path, content)
            except Exception as e:
                print(f"index_doc: graph staging failed: {e!r}",
                      file=sys.stderr, flush=True)

        return first_doc_id or f"{path}::main"

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
            row = conn.execute("SELECT COUNT(*) FROM docs").fetchone()
            result["doc_count"] = row[0] if row else 0
            try:
                ts_row = conn.execute(
                    "SELECT MAX(indexed_at) FROM docs"
                ).fetchone()
                result["last_reindex"] = ts_row[0] or "" if ts_row else ""
            except sqlite3.OperationalError:
                pass
            conn.close()
        except Exception:
            pass

        try:
            conn = sqlite3.connect(self._graph_db)
            row = conn.execute(
                "SELECT COUNT(*) FROM entities"
            ).fetchone()
            result["entity_count"] = row[0] if row else 0
            conn.close()
        except Exception:
            pass

        try:
            result["vector_enabled"] = bool(
                getattr(self._brain, "vector_enabled", False)
            )
        except Exception:
            pass

        return result
