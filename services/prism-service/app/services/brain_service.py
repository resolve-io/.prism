"""Brain service — wrapper over the Brain engine."""

from __future__ import annotations

import os as _os
import sqlite3
import sys
from typing import Optional


import re as _re

_CAMEL_RE = _re.compile(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')


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
            # Expand PascalCase/camelCase per chunk for FTS matching.
            expanded = _expand_identifiers(indexed_content)
            # Hash RAW chunk content so prism_status drift detection still
            # lines up with on-disk sha256 when the file is single-chunk.
            chash = _hashlib.sha256(chunk_content.encode("utf-8")).hexdigest()

            brain_conn.execute(
                "INSERT INTO docs "
                "(id, source_file, content, domain, indexed_at, "
                " entity_name, entity_kind, content_hash, "
                " line_start, line_end) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, path, expanded, domain, now,
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
