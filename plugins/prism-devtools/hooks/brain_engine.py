#!/usr/bin/env python3
"""Brain Engine: 3-index hybrid search for PRISM.

Provides:
- FTS5 BM25 keyword search (always available, stdlib only)
- sqlite-vec vector search via model2vec embeddings (optional)
- GraphRAG entity/relationship search (always available)
- RRF fusion across all three indexes

Gracefully degrades to BM25+GraphRAG or BM25-only when optional
deps are unavailable.
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BrainCorruptError(Exception):
    """Raised when a Brain database file fails SQLite integrity check."""


# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------
_MODEL = None
_SQLITE_VEC_LOADED = False


def _try_enable_vector(db: sqlite3.Connection) -> bool:
    """Attempt to load sqlite-vec extension and model2vec. Returns True on success."""
    global _MODEL, _SQLITE_VEC_LOADED
    try:
        import sqlite_vec  # type: ignore
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        _SQLITE_VEC_LOADED = True
    except (ImportError, AttributeError, Exception):
        print(
            "Brain: running in BM25+GraphRAG mode "
            "(install sqlite-vec model2vec for vector search)",
            file=sys.stderr,
        )
        return False

    try:
        from model2vec import StaticModel  # type: ignore
        if _MODEL is None:
            _MODEL = StaticModel.from_pretrained("minishlab/potion-base-32M")
        return True
    except (ImportError, OSError, Exception):
        print(
            "Brain: running in BM25+GraphRAG mode "
            "(install sqlite-vec model2vec for vector search)",
            file=sys.stderr,
        )
        return False


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    result_lists: list[list[dict]], k: int = 60
) -> list[dict]:
    """Fuse multiple ranked result lists via Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    doc_data: dict[str, dict] = {}

    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            doc_id = item["doc_id"]
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in doc_data:
                doc_data[doc_id] = item

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [
        {"doc_id": doc_id, "rrf_score": score, **doc_data[doc_id]}
        for doc_id, score in fused
    ]


# ---------------------------------------------------------------------------
# Structural query detection
# ---------------------------------------------------------------------------

_STRUCTURAL_PATTERNS = [
    (r"what\s+(?:calls|invokes|uses)\s+(\w+)", "called_by"),
    (r"(?:dependencies|deps)\s+of\s+(\w+)", "depends_on"),
    (r"what\s+(?:imports|requires)\s+(\w+)", "imported_by"),
    (r"(?:callers|consumers)\s+of\s+(\w+)", "called_by"),
    (r"(?:extends|subclasses|inherits)\s+(\w+)", "extends"),
]


def _detect_structural_query(query: str) -> tuple[Optional[str], Optional[str]]:
    """Return (entity_name, relation) if structural query, else (None, None)."""
    for pattern, relation in _STRUCTURAL_PATTERNS:
        m = re.search(pattern, query, re.IGNORECASE)
        if m:
            return m.group(1), relation
    return None, None


# ---------------------------------------------------------------------------
# Brain class
# ---------------------------------------------------------------------------

class Brain:
    """3-index hybrid knowledge store: FTS5 BM25 + sqlite-vec + GraphRAG."""

    # PSP weights per (persona, step_id)
    PSP_WEIGHTS: dict[tuple[str, str], dict[str, float]] = {
        ("qa", "write_failing_tests"): {
            "gate_passed": 0.3,
            "traceability_pct": 0.3,
            "first_attempt": 0.2,
            "token_efficiency": 0.2,
        },
        ("dev", "implement_tasks"): {
            "gate_passed": 0.4,
            "coverage_pct": 0.3,
            "retry_rate": 0.15,
            "token_efficiency": 0.15,
        },
        ("sm", "draft_story"): {
            "probe_accuracy": 0.4,
            "story_completeness": 0.3,
            "token_efficiency": 0.3,
        },
    }
    DEFAULT_WEIGHTS: dict[str, float] = {
        "gate_passed": 0.4,
        "token_efficiency": 0.3,
        "retry_rate": 0.3,
    }

    _INDEXABLE_SUFFIXES = {
        ".py", ".ts", ".tsx", ".js", ".jsx",
        ".md", ".yaml", ".yml", ".json", ".txt", ".sh",
    }

    _EXCLUDED_PATH_SEGMENTS = {
        ".claude", ".prism", "__pycache__", "node_modules", ".git",
        ".venv", "venv", ".env", "dist", "build", ".tox",
        ".mypy_cache", ".pytest_cache", ".overstory",
    }

    def __init__(
        self,
        brain_db: str = ".prism/brain/brain.db",
        graph_db: str = ".prism/brain/graph.db",
        scores_db: str = ".prism/brain/scores.db",
    ) -> None:
        self._brain_db_path = brain_db
        self._graph_db_path = graph_db
        self._scores_db_path = scores_db
        self._current_step_id: Optional[str] = None
        self.last_result_count: int = 0

        for path in (brain_db, graph_db, scores_db):
            Path(path).parent.mkdir(parents=True, exist_ok=True)

        self._brain = self._connect(brain_db)
        self._graph = self._connect(graph_db)
        self._scores = self._connect(scores_db)

        for label, db in (
            (brain_db, self._brain),
            (graph_db, self._graph),
            (scores_db, self._scores),
        ):
            try:
                db.execute("PRAGMA journal_mode=WAL")
            except sqlite3.DatabaseError as exc:
                raise BrainCorruptError(f"{label} is corrupt: {exc}") from exc

        self._check_db_integrity()
        self.vector_enabled = _try_enable_vector(self._brain)

        self._init_brain_schema()
        self._init_graph_schema()
        self._init_scores_schema()

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _check_db_integrity(self) -> None:
        """Run PRAGMA integrity_check on each DB. Raise BrainCorruptError if any fails."""
        for label, conn in (
            (self._brain_db_path, self._brain),
            (self._graph_db_path, self._graph),
            (self._scores_db_path, self._scores),
        ):
            try:
                row = conn.execute("PRAGMA integrity_check").fetchone()
                result = row[0] if row else "no result"
            except Exception as exc:
                raise BrainCorruptError(f"{label} integrity check error: {exc}") from exc
            if result != "ok":
                raise BrainCorruptError(f"{label} is corrupt: {result}")

    # ------------------------------------------------------------------
    # Schema initialisation
    # ------------------------------------------------------------------

    def _init_brain_schema(self) -> None:
        self._brain.executescript("""
            CREATE TABLE IF NOT EXISTS docs (
                id TEXT PRIMARY KEY,
                source_file TEXT,
                content TEXT NOT NULL,
                domain TEXT,
                content_hash TEXT,
                indexed_at TEXT DEFAULT (datetime('now'))
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
                id UNINDEXED,
                content,
                domain UNINDEXED,
                content='docs',
                content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS docs_fts_ai AFTER INSERT ON docs BEGIN
                INSERT INTO docs_fts(rowid, id, content, domain)
                    VALUES(new.rowid, new.id, new.content, new.domain);
            END;
            CREATE TRIGGER IF NOT EXISTS docs_fts_ad AFTER DELETE ON docs BEGIN
                INSERT INTO docs_fts(docs_fts, rowid, id, content, domain)
                    VALUES('delete', old.rowid, old.id, old.content, old.domain);
            END;
            CREATE TRIGGER IF NOT EXISTS docs_fts_au AFTER UPDATE ON docs BEGIN
                INSERT INTO docs_fts(docs_fts, rowid, id, content, domain)
                    VALUES('delete', old.rowid, old.id, old.content, old.domain);
                INSERT INTO docs_fts(rowid, id, content, domain)
                    VALUES(new.rowid, new.id, new.content, new.domain);
            END;
            CREATE TABLE IF NOT EXISTS index_meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        if self.vector_enabled:
            try:
                self._brain.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS docs_vec "
                    "USING vec0(doc_id TEXT, embedding float[384])"
                )
                self._brain.commit()
            except Exception:
                self.vector_enabled = False

    def _init_graph_schema(self) -> None:
        self._graph.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT DEFAULT 'unknown',
                file TEXT,
                line INTEGER,
                UNIQUE(name, file)
            );
            CREATE TABLE IF NOT EXISTS relationships (
                source_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
                target_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
                relation TEXT,
                PRIMARY KEY (source_id, target_id, relation)
            );
            CREATE INDEX IF NOT EXISTS idx_ent_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_rel_src ON relationships(source_id);
            CREATE INDEX IF NOT EXISTS idx_rel_tgt ON relationships(target_id);
        """)

    def _init_scores_schema(self) -> None:
        self._scores.executescript("""
            CREATE TABLE IF NOT EXISTS prompt_scores (
                prompt_id TEXT,
                persona TEXT,
                step_id TEXT,
                score REAL,
                tokens_used INTEGER,
                context_tokens INTEGER,
                duration_s REAL,
                retries INTEGER,
                difficulty TEXT,
                tests_passed INTEGER,
                coverage_pct REAL,
                traceability_pct REAL,
                gate_passed INTEGER,
                probe_accuracy REAL,
                timestamp TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (prompt_id, persona, step_id, timestamp)
            );
            CREATE TABLE IF NOT EXISTS score_aggregates (
                prompt_id TEXT,
                persona TEXT,
                step_id TEXT,
                avg_score REAL DEFAULT 0.0,
                total_runs INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (prompt_id, persona, step_id)
            );
            CREATE TABLE IF NOT EXISTS prompt_variants (
                prompt_id TEXT PRIMARY KEY,
                persona TEXT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'learned',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS retired_variants (
                prompt_id TEXT PRIMARY KEY,
                persona TEXT,
                retired_at TEXT DEFAULT (datetime('now')),
                reason TEXT
            );
        """)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _content_hash(content: str) -> str:
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _embed(self, text: str) -> Optional[list[float]]:
        if not self.vector_enabled or _MODEL is None:
            return None
        try:
            vecs = _MODEL.encode([text[:2048]])
            return vecs[0].tolist()
        except Exception:
            return None

    def _should_index(self, filepath: str) -> bool:
        p = Path(filepath)
        if any(part in self._EXCLUDED_PATH_SEGMENTS for part in p.parts):
            return False
        return p.suffix in self._INDEXABLE_SUFFIXES

    def _get_last_index_timestamp(self) -> str:
        row = self._brain.execute(
            "SELECT value FROM index_meta WHERE key = 'last_indexed'"
        ).fetchone()
        return row["value"] if row else "1970-01-01T00:00:00"

    def _update_last_index_timestamp(self) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        self._brain.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES ('last_indexed', ?)",
            (ts,),
        )
        self._brain.commit()

    def _purge_deleted(self) -> int:
        """Remove DB entries for files that no longer exist or are now excluded.

        Returns count of purged documents.
        """
        rows = self._brain.execute(
            "SELECT id, source_file FROM docs WHERE source_file IS NOT NULL"
        ).fetchall()
        to_purge: list[str] = []
        for row in rows:
            sf = row["source_file"]
            if not Path(sf).exists() or not self._should_index(sf):
                to_purge.append(sf)
        if to_purge:
            self._remove_entries_by_source(to_purge)
        return len(to_purge)

    def _remove_entries_by_source(self, files: list[str]) -> None:
        for filepath in files:
            rows = self._brain.execute(
                "SELECT id FROM docs WHERE source_file = ?", (filepath,)
            ).fetchall()
            for row in rows:
                doc_id = row["id"]
                if self.vector_enabled:
                    try:
                        self._brain.execute(
                            "DELETE FROM docs_vec WHERE doc_id = ?", (doc_id,)
                        )
                    except Exception:
                        pass
                self._brain.execute("DELETE FROM docs WHERE id = ?", (doc_id,))
        self._brain.commit()

    def _index_files(self, files: list[str]) -> None:
        for filepath in files:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
                self._ingest_single(filepath, content, source_file=filepath,
                                    domain=Path(filepath).suffix.lstrip("."))
            except (IOError, OSError):
                pass

    def _ingest_single(
        self,
        doc_id: str,
        content: str,
        source_file: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> bool:
        """Ingest one document. Returns True if actually indexed (not skipped)."""
        chash = self._content_hash(content)
        existing = self._brain.execute(
            "SELECT content_hash FROM docs WHERE id = ?", (doc_id,)
        ).fetchone()
        if existing and existing["content_hash"] == chash:
            return False

        self._brain.execute(
            "INSERT OR REPLACE INTO docs "
            "(id, source_file, content, domain, content_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, source_file, content, domain, chash),
        )
        if self.vector_enabled:
            vec = self._embed(content)
            if vec is not None:
                import struct
                blob = struct.pack(f"{len(vec)}f", *vec)
                try:
                    self._brain.execute(
                        "DELETE FROM docs_vec WHERE doc_id = ?", (doc_id,)
                    )
                    self._brain.execute(
                        "INSERT INTO docs_vec (doc_id, embedding) VALUES (?, ?)",
                        (doc_id, blob),
                    )
                except Exception:
                    pass
        self._brain.commit()

        if source_file:
            self._index_graph(source_file, content)

        return True

    def _index_graph(self, filepath: str, content: str) -> None:
        """Extract entities from source and store in graph.db."""
        entities = self._extract_entities(filepath, content)
        for name, kind, line in entities:
            self._graph.execute(
                "INSERT OR IGNORE INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (name, kind, filepath, line),
            )
        self._graph.commit()

    @staticmethod
    def _extract_entities(
        filepath: str, content: str
    ) -> list[tuple[str, str, int]]:
        """Extract (name, kind, line) from source content via regex."""
        results: list[tuple[str, str, int]] = []
        for i, line in enumerate(content.splitlines(), start=1):
            # Python class
            m = re.match(r"^class\s+(\w+)", line)
            if m:
                results.append((m.group(1), "class", i))
                continue
            # Python def
            m = re.match(r"^(?:async\s+)?def\s+(\w+)", line)
            if m:
                results.append((m.group(1), "function", i))
                continue
            # JS/TS exported class
            m = re.match(r"^export\s+(?:default\s+)?class\s+(\w+)", line)
            if m:
                results.append((m.group(1), "class", i))
                continue
            # JS/TS exported function
            m = re.match(r"^export\s+(?:async\s+)?function\s+(\w+)", line)
            if m:
                results.append((m.group(1), "function", i))
                continue
        # File as module entity
        stem = Path(filepath).stem
        if stem:
            results.append((stem, "file", 0))
        return results

    # ------------------------------------------------------------------
    # FTS5 / vector / graph search
    # ------------------------------------------------------------------

    def _fts5_search(
        self, query: str, domain: Optional[str], limit: int
    ) -> list[dict]:
        safe = re.sub(r"[^\w\s]", " ", query).strip()
        if not safe:
            return []
        try:
            if domain:
                rows = self._brain.execute(
                    "SELECT id, bm25(docs_fts) AS score FROM docs_fts "
                    "WHERE docs_fts MATCH ? AND domain = ? ORDER BY score LIMIT ?",
                    (safe, domain, limit),
                ).fetchall()
            else:
                rows = self._brain.execute(
                    "SELECT id, bm25(docs_fts) AS score FROM docs_fts "
                    "WHERE docs_fts MATCH ? ORDER BY score LIMIT ?",
                    (safe, limit),
                ).fetchall()
            return [{"doc_id": r["id"], "score": -r["score"]} for r in rows]
        except Exception:
            return []

    def _vector_search(
        self, query: str, domain: Optional[str], limit: int
    ) -> list[dict]:
        if not self.vector_enabled:
            return []
        vec = self._embed(query)
        if vec is None:
            return []
        try:
            import struct
            blob = struct.pack(f"{len(vec)}f", *vec)
            rows = self._brain.execute(
                "SELECT doc_id, distance FROM docs_vec "
                "WHERE embedding MATCH ? AND k = ?",
                (blob, limit),
            ).fetchall()
            return [
                {"doc_id": r["doc_id"], "score": 1.0 / (1.0 + r["distance"])}
                for r in rows
            ]
        except Exception:
            return []

    def _graph_search(self, query: str, limit: int) -> list[dict]:
        entity_name, relation = _detect_structural_query(query)
        if entity_name:
            return self._traverse_graph(entity_name, relation, limit)

        tokens = [t for t in re.split(r"\W+", query) if len(t) > 3]
        if not tokens:
            return []
        seen: set[str] = set()
        results: list[dict] = []
        for token in tokens[:8]:
            try:
                rows = self._graph.execute(
                    "SELECT DISTINCT file FROM entities WHERE name LIKE ? LIMIT ?",
                    (f"%{token}%", limit),
                ).fetchall()
                for row in rows:
                    f = row["file"]
                    if f and f not in seen:
                        seen.add(f)
                        results.append({"doc_id": f, "score": 1.0})
            except Exception:
                pass
        return results[:limit]

    def _traverse_graph(
        self, entity_name: str, relation: Optional[str], limit: int
    ) -> list[dict]:
        try:
            ent = self._graph.execute(
                "SELECT id FROM entities WHERE name = ? LIMIT 1", (entity_name,)
            ).fetchone()
            if not ent:
                return []
            eid = ent["id"]
            if relation:
                rows = self._graph.execute(
                    "SELECT e.file FROM relationships r "
                    "JOIN entities e ON e.id = r.target_id "
                    "WHERE r.source_id = ? AND r.relation = ? LIMIT ?",
                    (eid, relation, limit),
                ).fetchall()
            else:
                rows = self._graph.execute(
                    "SELECT e.file FROM relationships r "
                    "JOIN entities e ON e.id = r.target_id "
                    "WHERE r.source_id = ? LIMIT ?",
                    (eid, limit),
                ).fetchall()
            return [{"doc_id": r["file"], "score": 1.0} for r in rows if r["file"]]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def search(
        self, query: str, domain: Optional[str] = None, limit: int = 5
    ) -> list[dict]:
        """3-index hybrid search with RRF fusion."""
        inner = limit * 2
        bm25 = self._fts5_search(query, domain, inner)
        vec = self._vector_search(query, domain, inner) if self.vector_enabled else []
        graph = self._graph_search(query, inner)

        fused = reciprocal_rank_fusion([bm25, vec, graph] if self.vector_enabled
                                       else [bm25, graph])
        top = fused[:limit]
        if not top:
            return []

        ids = [item["doc_id"] for item in top]
        placeholders = ",".join("?" * len(ids))
        rows = self._brain.execute(
            f"SELECT id, content, domain FROM docs WHERE id IN ({placeholders})", ids
        ).fetchall()
        content_map = {r["id"]: r for r in rows}

        results = []
        for item in top:
            row = content_map.get(item["doc_id"])
            if row:
                results.append({
                    "doc_id": item["doc_id"],
                    "content": row["content"],
                    "domain": row["domain"],
                    "rrf_score": item.get("rrf_score", 0.0),
                })
        return results

    def system_context(
        self,
        story_file: Optional[str] = None,
        persona: Optional[str] = None,
        limit: int = 8,
    ) -> str:
        """Run hybrid search from story/persona context and return formatted block."""
        query = ""
        if story_file:
            try:
                query = Path(story_file).read_text(
                    encoding="utf-8", errors="replace"
                )[:1000]
            except (IOError, OSError):
                pass
        if not query and persona:
            query = persona
        if not query:
            return ""

        results = self.search(query, limit=limit)
        if not results:
            self.last_result_count = 0
            return ""

        results = [r for r in results if r.get("rrf_score", 0.0) >= 0.02]
        if not results:
            self.last_result_count = 0
            return ""

        self.last_result_count = len(results)
        parts = ["<brain_context>"]
        for i, r in enumerate(results, 1):
            parts.append(f"[{i}] {r['doc_id']}")
            parts.append(r["content"][:600])
            parts.append("")
        parts.append("</brain_context>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Graph API
    # ------------------------------------------------------------------

    def graph_query(
        self,
        entity: str,
        relation: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Traverse entity relationships and return related entities."""
        ent_row = self._graph.execute(
            "SELECT id FROM entities WHERE name = ? LIMIT 1", (entity,)
        ).fetchone()
        if not ent_row:
            return []
        eid = ent_row["id"]
        try:
            if relation:
                rows = self._graph.execute(
                    "SELECT e.name, e.kind, e.file, r.relation FROM relationships r "
                    "JOIN entities e ON e.id = r.target_id "
                    "WHERE r.source_id = ? AND r.relation = ? LIMIT ?",
                    (eid, relation, limit),
                ).fetchall()
            else:
                rows = self._graph.execute(
                    "SELECT e.name, e.kind, e.file, r.relation FROM relationships r "
                    "JOIN entities e ON e.id = r.target_id "
                    "WHERE r.source_id = ? LIMIT ?",
                    (eid, limit),
                ).fetchall()
            return [
                {"name": r["name"], "kind": r["kind"],
                 "file": r["file"], "relation": r["relation"]}
                for r in rows
            ]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------

    def ingest(self, sources: list[str]) -> int:
        """Full index of all provided file paths or directories. Returns doc count."""
        count = 0
        for source in sources:
            p = Path(source)
            if not p.exists():
                continue
            if p.is_file() and self._should_index(source):
                content = p.read_text(encoding="utf-8", errors="replace")
                if self._ingest_single(source, content, source_file=source,
                                       domain=p.suffix.lstrip(".")):
                    count += 1
            elif p.is_dir():
                for child in p.rglob("*"):
                    if child.is_file() and self._should_index(str(child)):
                        try:
                            content = child.read_text(encoding="utf-8", errors="replace")
                            rel = str(child)
                            if self._ingest_single(rel, content, source_file=rel,
                                                   domain=child.suffix.lstrip(".")):
                                count += 1
                        except (IOError, OSError):
                            pass
        self._purge_deleted()
        self._update_last_index_timestamp()
        return count

    def incremental_reindex(self) -> int:
        """Re-index only files changed since last index. Returns count reindexed."""
        try:
            changed_out = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMRD", "HEAD"],
                capture_output=True, text=True,
            ).stdout.strip()
            deleted_out = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=D", "HEAD"],
                capture_output=True, text=True,
            ).stdout.strip()
            untracked_out = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True,
            ).stdout.strip()
        except (FileNotFoundError, subprocess.SubprocessError):
            changed_out, deleted_out, untracked_out = "", "", ""

        changed = changed_out.split("\n") if changed_out else []
        deleted = deleted_out.split("\n") if deleted_out else []
        untracked = untracked_out.split("\n") if untracked_out else []

        # Remove entries for explicitly deleted files
        deleted_indexed = [f for f in deleted if f]
        if deleted_indexed:
            self._remove_entries_by_source(deleted_indexed)

        to_index = [
            f for f in changed + untracked
            if f and self._should_index(f) and Path(f).exists()
        ]

        if to_index:
            self._remove_entries_by_source(to_index)
            self._index_files(to_index)

        self._purge_deleted()
        self._update_last_index_timestamp()
        return len(to_index)

    # ------------------------------------------------------------------
    # Prompt management
    # ------------------------------------------------------------------

    def best_prompt(
        self,
        persona: str,
        step_id: str,
        difficulty: Optional[str] = None,
    ) -> str:
        """Return highest-scoring prompt variant ID for persona/step.

        When difficulty is provided, prefers variants that have performed
        well on runs of that difficulty level, falling back to overall best.
        """
        if difficulty:
            row = self._scores.execute(
                "SELECT prompt_id, AVG(score) AS avg_score, COUNT(*) AS cnt "
                "FROM prompt_scores "
                "WHERE persona = ? AND step_id = ? AND difficulty = ? "
                "GROUP BY prompt_id HAVING cnt >= 3 "
                "ORDER BY avg_score DESC LIMIT 1",
                (persona, step_id, difficulty),
            ).fetchone()
            if row:
                return row["prompt_id"]

        row = self._scores.execute(
            "SELECT prompt_id FROM score_aggregates "
            "WHERE persona = ? AND step_id = ? AND total_runs >= 3 "
            "ORDER BY avg_score DESC LIMIT 1",
            (persona, step_id),
        ).fetchone()
        return row["prompt_id"] if row else f"{persona}/default"

    def get_prompt(self, persona: str, variant: str = "default") -> str:
        """Return prompt variant text from scores.db or shipped prompts."""
        row = self._scores.execute(
            "SELECT content FROM prompt_variants WHERE prompt_id = ?",
            (f"{persona}/{variant}",),
        ).fetchone()
        if row:
            return row["content"]
        prompt_file = (
            Path(__file__).parent.parent / "prompts" / persona / f"{variant}.md"
        )
        if prompt_file.exists():
            return prompt_file.read_text(encoding="utf-8")
        return ""

    # ------------------------------------------------------------------
    # Outcome tracking
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        prompt_id: str,
        persona: str,
        step_id: str,
        metrics: dict,
    ) -> None:
        """Store execution result in scores.db and append to outcomes.jsonl."""
        score = self._compute_psp_score(persona, step_id, metrics)
        ts = metrics.get("timestamp") or datetime.now(timezone.utc).isoformat()

        self._scores.execute(
            "INSERT OR REPLACE INTO prompt_scores "
            "(prompt_id, persona, step_id, score, tokens_used, context_tokens, "
            " duration_s, retries, difficulty, tests_passed, coverage_pct, "
            " traceability_pct, gate_passed, probe_accuracy, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                prompt_id, persona, step_id, score,
                metrics.get("tokens_used"), metrics.get("context_tokens"),
                metrics.get("duration_s"), metrics.get("retries"),
                metrics.get("difficulty"), metrics.get("tests_passed"),
                metrics.get("coverage_pct"), metrics.get("traceability_pct"),
                metrics.get("gate_passed"), metrics.get("probe_accuracy"), ts,
            ),
        )
        agg = self._scores.execute(
            "SELECT avg_score, total_runs FROM score_aggregates "
            "WHERE prompt_id = ? AND persona = ? AND step_id = ?",
            (prompt_id, persona, step_id),
        ).fetchone()
        if agg is None:
            self._scores.execute(
                "INSERT INTO score_aggregates "
                "(prompt_id, persona, step_id, avg_score, total_runs) "
                "VALUES (?, ?, ?, ?, 1)",
                (prompt_id, persona, step_id, score),
            )
        else:
            n = agg["total_runs"] + 1
            new_avg = (agg["avg_score"] * agg["total_runs"] + score) / n
            self._scores.execute(
                "UPDATE score_aggregates "
                "SET avg_score = ?, total_runs = ?, last_updated = datetime('now') "
                "WHERE prompt_id = ? AND persona = ? AND step_id = ?",
                (new_avg, n, prompt_id, persona, step_id),
            )
        self._scores.commit()

        outcomes_file = Path(self._scores_db_path).parent / "outcomes.jsonl"
        record = {"prompt_id": prompt_id, "persona": persona, "step_id": step_id,
                  "score": score, "timestamp": ts, **metrics}
        with outcomes_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def avg_tokens(self, step_id: str) -> int:
        """Historical average token usage for a step (for difficulty estimation)."""
        row = self._scores.execute(
            "SELECT AVG(tokens_used) AS avg FROM prompt_scores "
            "WHERE step_id = ? AND tokens_used IS NOT NULL",
            (step_id,),
        ).fetchone()
        if row and row["avg"] is not None:
            return int(row["avg"])
        return 4000

    def outcome_count(self, persona: str, step_id: str) -> int:
        """Total outcomes recorded for a persona/step combination."""
        row = self._scores.execute(
            "SELECT SUM(total_runs) AS total FROM score_aggregates "
            "WHERE persona = ? AND step_id = ?",
            (persona, step_id),
        ).fetchone()
        return int(row["total"]) if row and row["total"] else 0

    def top_outcomes(
        self, persona: str, step_id: str, limit: int = 5
    ) -> list[dict]:
        """Return highest-scoring outcomes for variant generation analysis."""
        rows = self._scores.execute(
            "SELECT prompt_id, score, tokens_used, duration_s, timestamp "
            "FROM prompt_scores WHERE persona = ? AND step_id = ? "
            "ORDER BY score DESC LIMIT ?",
            (persona, step_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # PSP scoring
    # ------------------------------------------------------------------

    def _compute_psp_score(
        self, persona: str, step_id: str, metrics: dict
    ) -> float:
        """Compute PSP composite score from execution metrics."""
        weights = self.PSP_WEIGHTS.get((persona, step_id), self.DEFAULT_WEIGHTS)
        score = 0.0
        for metric_name, weight in weights.items():
            value = metrics.get(metric_name)
            if value is not None:
                score += weight * self._normalize(metric_name, float(value), step_id)
        return round(score, 4)

    def _normalize(
        self, metric_name: str, value: float, step_id: str = ""
    ) -> float:
        """Normalize a metric value to 0-1 range."""
        if metric_name in ("gate_passed", "first_attempt"):
            return float(bool(value))
        if metric_name in (
            "coverage_pct", "traceability_pct", "probe_accuracy", "story_completeness"
        ):
            return min(1.0, value / 100.0)
        if metric_name == "token_efficiency":
            baseline = self.avg_tokens(step_id) if step_id else 4000
            return min(1.0, baseline / max(value, 1.0))
        if metric_name == "retry_rate":
            return max(0.0, 1.0 - (value / 3.0))
        return value


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _cli_source_dirs() -> list[str]:
    """Return source directories to index, mirroring brain_bootstrap logic."""
    sources: list[str] = []
    cwd = Path.cwd()
    plugin_root = Path(__file__).resolve().parent.parent
    docs_dir = cwd / "docs"
    if docs_dir.exists():
        sources.append(str(docs_dir))
    core_steps = plugin_root / "hooks" / "core-steps"
    if core_steps.exists():
        sources.append(str(core_steps))
    for src_dir in ("src", "lib", "scripts", "plugins", "hooks"):
        candidate = cwd / src_dir
        if candidate.exists() and candidate.is_dir():
            sources.append(str(candidate))
    if not sources:
        sources.append(str(cwd))
    return sources


def _cmd_init(brain: "Brain") -> int:
    sources = _cli_source_dirs()
    count = brain.ingest(sources)
    if brain.vector_enabled:
        mode = "Full \u2014 BM25+Vector+GraphRAG"
    else:
        mode = "BM25+GraphRAG"
    print(f"Brain: indexed {count} documents from {len(sources)} source(s) (mode: {mode})")
    return 0


def _cmd_search(brain: "Brain", query: str) -> int:
    results = brain.search(query)
    if not results:
        print("No results found.")
        return 0
    for i, r in enumerate(results, 1):
        score = round(r.get("rrf_score", 0.0), 4)
        print(f"[{i}] {r['doc_id']}  (score={score})")
        snippet = r.get("content", "")[:200].replace("\n", " ")
        print(f"    {snippet}")
    return 0


def _cmd_status(brain: "Brain") -> int:
    doc_count = brain._brain.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
    entity_count = brain._graph.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    last_indexed = brain._get_last_index_timestamp()
    if brain.vector_enabled:
        mode = "Full \u2014 BM25+Vector+GraphRAG"
    else:
        mode = "BM25+GraphRAG (install sqlite-vec model2vec for Full mode)"
    print(f"Mode              : {mode}")
    print(f"Documents indexed : {doc_count}")
    print(f"Graph entities    : {entity_count}")
    print(f"Last indexed      : {last_indexed}")
    return 0


def _print_usage() -> None:
    print("Usage: python3 brain_engine.py <command> [args]")
    print("")
    print("Commands:")
    print("  init              Index project source files")
    print("  ingest            Re-index all sources (same as init)")
    print("  search <query>    Search indexed knowledge")
    print("  status            Show index health and statistics")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        _print_usage()
        sys.exit(1)

    cmd = args[0]
    if cmd in ("init", "ingest"):
        try:
            import sqlite_vec  # type: ignore  # noqa: F401
            from model2vec import StaticModel  # type: ignore  # noqa: F401
        except ImportError:
            print("Brain: attempting to install optional deps (sqlite-vec model2vec)...",
                  file=sys.stderr)
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "sqlite-vec", "model2vec"],
                capture_output=True,
            )
            if result.returncode != 0:
                print(
                    "Brain: optional deps unavailable, continuing in BM25+GraphRAG mode",
                    file=sys.stderr,
                )

    try:
        b = Brain()
    except BrainCorruptError as exc:
        print(f"Brain: corrupt database ({exc}), deleting and re-initialising...",
              file=sys.stderr)
        brain_dir = Path(".prism/brain")
        for db_file in brain_dir.glob("*.db"):
            db_file.unlink(missing_ok=True)
        b = Brain()

    if cmd in ("init", "ingest"):
        rc = _cmd_init(b)
    elif cmd == "search":
        if len(args) < 2:
            print("Error: search requires a query argument", file=sys.stderr)
            _print_usage()
            sys.exit(1)
        rc = _cmd_search(b, " ".join(args[1:]))
    elif cmd == "status":
        rc = _cmd_status(b)
    else:
        print(f"Error: unknown command '{cmd}'", file=sys.stderr)
        _print_usage()
        sys.exit(1)

    sys.exit(rc)
