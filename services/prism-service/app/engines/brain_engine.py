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

import ctypes
import json
import re
import sqlite3
import subprocess
import sys
import warnings
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

# ---------------------------------------------------------------------------
# Tree-sitter language loader
# ---------------------------------------------------------------------------
_TS_PARSER_CACHE: dict[str, object] = {}
_TS_LANGS_LIB: Optional[ctypes.CDLL] = None
_TS_AVAILABLE = False


def _init_treesitter_lib() -> None:
    """Load the bundled tree-sitter-languages .so and mark availability."""
    global _TS_LANGS_LIB, _TS_AVAILABLE
    if _TS_AVAILABLE:
        return
    try:
        import tree_sitter_languages as _tsl
        lib_path = Path(_tsl.__path__[0]) / "languages.so"
        if not lib_path.exists():
            return
        _TS_LANGS_LIB = ctypes.cdll.LoadLibrary(str(lib_path))
        _TS_AVAILABLE = True
    except Exception:
        pass


def _get_treesitter_parser(lang_name: str) -> Optional[object]:
    """Return a cached tree_sitter.Parser for the given language, or None."""
    if lang_name in _TS_PARSER_CACHE:
        return _TS_PARSER_CACHE[lang_name]
    _init_treesitter_lib()
    if not _TS_AVAILABLE or _TS_LANGS_LIB is None:
        return None
    try:
        import tree_sitter
        fn_name = f"tree_sitter_{lang_name}"
        fn = getattr(_TS_LANGS_LIB, fn_name, None)
        if fn is None:
            return None
        fn.restype = ctypes.c_void_p
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            lang = tree_sitter.Language(fn())
        parser = tree_sitter.Parser(lang)
        _TS_PARSER_CACHE[lang_name] = parser
        return parser
    except Exception:
        return None


# Map file suffix -> tree-sitter language name (as in languages.so symbol)
_TS_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".cs": "c_sharp",
}


_EMBEDDER_PRESETS = {
    # key -> (backend, model_id)
    # backend in {"model2vec", "sentence-transformers"}
    "potion": ("model2vec", "minishlab/potion-base-32M"),
    "minilm": ("sentence-transformers", "sentence-transformers/all-MiniLM-L6-v2"),
    "nomic-code": ("sentence-transformers", "nomic-ai/nomic-embed-code"),
    "bge-small": ("sentence-transformers", "BAAI/bge-small-en-v1.5"),
    "jina-code": ("sentence-transformers", "jinaai/jina-embeddings-v2-base-code"),
}


def _load_sentence_transformer(model_id: str):
    """Load a sentence-transformers model. Returns object with .encode([str]) API."""
    from sentence_transformers import SentenceTransformer  # type: ignore
    return SentenceTransformer(model_id)


def _load_model2vec(model_id: str):
    from model2vec import StaticModel  # type: ignore
    return StaticModel.from_pretrained(model_id)


def _try_enable_vector(db: sqlite3.Connection) -> bool:
    """Attempt to load sqlite-vec extension and an embedding model.

    The embedding model is chosen via env var PRISM_EMBEDDER (one of the keys
    in _EMBEDDER_PRESETS); defaults to 'potion'. Returns True on success.
    """
    import os
    global _MODEL, _SQLITE_VEC_LOADED
    try:
        import sqlite_vec  # type: ignore
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
        _SQLITE_VEC_LOADED = True
    except (ImportError, AttributeError, Exception):
        print("Brain: running in BM25+GraphRAG mode (sqlite-vec unavailable)",
              file=sys.stderr)
        return False

    preset = os.environ.get("PRISM_EMBEDDER", "potion").strip().lower()
    if preset not in _EMBEDDER_PRESETS:
        print(f"Brain: unknown PRISM_EMBEDDER={preset!r}; falling back to 'potion'",
              file=sys.stderr)
        preset = "potion"
    backend, model_id = _EMBEDDER_PRESETS[preset]

    if _MODEL is not None:
        return True  # already loaded (same process reuse)

    try:
        if backend == "model2vec":
            _MODEL = _load_model2vec(model_id)
        elif backend == "sentence-transformers":
            _MODEL = _load_sentence_transformer(model_id)
        print(f"Brain: embedder = {preset} ({backend}: {model_id})",
              file=sys.stderr)
        return True
    except Exception as e:
        print(f"Brain: embedder load failed ({preset}: {e!r}); BM25+GraphRAG only",
              file=sys.stderr)
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

    # Deterministic tie-breaking: sort by score DESC then doc_id ASC
    # so equal-score results always appear in the same order.
    fused = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
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

    # Role → preferred Brain domain list for system_context() filtering.
    # SM/PO/Architect: architecture decisions and docs live in expertise+md.
    # QA: test conventions live in expertise records.
    # DEV/Engineer: code patterns live in source code domains.
    ROLE_DOMAIN_MAP: dict[str, list[str]] = {
        "sm": ["expertise", "md"],
        "po": ["expertise", "md"],
        "architect": ["expertise", "md"],
        "qa": ["expertise"],
        "dev": ["py", "ts", "js", "expertise"],
        "engineer": ["py", "ts", "js", "expertise"],
    }

    def __init__(
        self,
        brain_db: str = "/data/brain.db",
        graph_db: str = "/data/graph.db",
        scores_db: str = "/data/scores.db",
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
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
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
                indexed_at TEXT DEFAULT (datetime('now')),
                entity_name TEXT,
                entity_kind TEXT,
                line_start INTEGER,
                line_end INTEGER
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
        # Migrate existing DBs: add chunk metadata columns if missing
        _meta_cols = [
            ("entity_name", "TEXT"),
            ("entity_kind", "TEXT"),
            ("line_start", "INTEGER"),
            ("line_end", "INTEGER"),
        ]
        existing_cols = {
            row[1]
            for row in self._brain.execute("PRAGMA table_info(docs)").fetchall()
        }
        for _col, _col_type in _meta_cols:
            if _col not in existing_cols:
                try:
                    self._brain.execute(
                        f"ALTER TABLE docs ADD COLUMN {_col} {_col_type}"
                    )
                    self._brain.commit()
                except sqlite3.OperationalError:
                    pass

        if self.vector_enabled:
            # Discover the model's native embedding dimension at startup so
            # the vec0 table matches whatever local model is loaded
            # (potion-base-32M is 512-dim; MiniLM-L6 is 384-dim).
            try:
                probe = _MODEL.encode(["probe"])[0]
                dim = len(probe)
            except Exception:
                dim = 384
            try:
                self._brain.execute(
                    f"CREATE VIRTUAL TABLE IF NOT EXISTS docs_vec "
                    f"USING vec0(doc_id TEXT, embedding float[{dim}])"
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
            CREATE TABLE IF NOT EXISTS session_outcomes (
                session_id TEXT PRIMARY KEY,
                duration_s INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                files_read INTEGER DEFAULT 0,
                files_modified INTEGER DEFAULT 0,
                skills_invoked INTEGER DEFAULT 0,
                timestamp TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS skill_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                skill_name TEXT NOT NULL,
                timestamp TEXT DEFAULT (datetime('now'))
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

    # ------------------------------------------------------------------
    # Chunking helpers
    # ------------------------------------------------------------------

    def _chunk_source_file(self, filepath: str, content: str) -> list[dict]:
        """Split a source file into multi-granular chunks.

        Returns a list of chunk dicts with keys:
          doc_id, content, entity_name, entity_kind, line_start, line_end

        Three granularity tiers (all emitted when PRISM_MULTIGRAN=on, default):
          - coarse: one whole-file chunk (``path::__file__`` for code, or the
            existing single-chunk ``filepath`` id for prose)
          - mid: semantic chunks at function/class boundaries (code only,
            ``path::EntityName``) and a ``path::__module__`` for loose
            top-level statements
          - fine: sliding 2048-char windows with 256-char overlap over the
            whole content (``path::win_N``). Emitted when content is large
            enough that windows carry new signal (>= min_chars).

        Chars/4 approximation: 2048 chars ~ 512 tokens, 256 chars ~ 64 tokens,
        matching the [512, 128]-token mid/fine target plus a file-level
        coarse pass. Per brain_engine.search() matches `_embed()`'s own
        2048-char truncation, so windows are sized to fit one embedding.

        Set PRISM_MULTIGRAN=off to fall back to the original single-tier
        semantic-only chunking (useful for A/B comparisons).
        """
        import os as _os

        multigran = _os.environ.get("PRISM_MULTIGRAN", "on").strip().lower() != "off"

        suffix = Path(filepath).suffix.lower()
        lines = content.splitlines()
        n = len(lines) or 1

        if suffix not in _TS_LANG_MAP:
            # Prose/config/unknown: keep the legacy single whole-file chunk
            # as the coarse tier, then add sliding windows for large files.
            chunks: list[dict] = [{
                "doc_id": filepath,
                "content": content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": n,
            }]
            if multigran:
                chunks.extend(
                    self._sliding_window_chunks(filepath, content, min_chars=2048)
                )
            return chunks

        lang_name = _TS_LANG_MAP[suffix]
        parser = _get_treesitter_parser(lang_name)

        if parser is not None and suffix == ".py":
            chunks = self._chunk_python_treesitter(filepath, content, parser, lines)
        else:
            chunks = self._chunk_regex_fallback(filepath, content, lines, suffix)

        if not multigran:
            return chunks

        # Coarse tier: whole-file view, distinct from __module__ (which only
        # covers lines NOT covered by any def/class). Only worth emitting when
        # the file has multiple semantic chunks AND is substantial.
        if len(chunks) > 1 and len(content) >= 2048:
            chunks.append({
                "doc_id": f"{filepath}::__file__",
                "content": content,
                "entity_name": "__file__",
                "entity_kind": "file",
                "line_start": 1,
                "line_end": n,
            })

        # Fine tier: sliding windows over full content. Skips small files
        # where the semantic chunks already cover everything.
        chunks.extend(
            self._sliding_window_chunks(filepath, content, min_chars=2048)
        )

        return chunks

    def _sliding_window_chunks(
        self,
        filepath: str,
        content: str,
        *,
        min_chars: int = 2048,
        window_chars: int = 2048,
        overlap_chars: int = 256,
    ) -> list[dict]:
        """Emit overlapping content windows for the fine-granularity tier.

        Returns an empty list when content is shorter than ``min_chars``
        (no new signal vs. the whole-file chunk). Windows are ``window_chars``
        wide with ``overlap_chars`` overlap between consecutive windows.
        Line ranges are computed from newline counts so UI linking stays
        accurate on arbitrary offsets.
        """
        total = len(content)
        if total < min_chars:
            return []
        step = max(1, window_chars - overlap_chars)
        windows: list[dict] = []
        pos = 0
        idx = 0
        while pos < total:
            end_pos = min(pos + window_chars, total)
            windows.append({
                "doc_id": f"{filepath}::win_{idx}",
                "content": content[pos:end_pos],
                "entity_name": f"win_{idx}",
                "entity_kind": "window",
                "line_start": content.count("\n", 0, pos) + 1,
                "line_end": content.count("\n", 0, end_pos) + 1,
            })
            idx += 1
            if end_pos >= total:
                break
            pos += step
        return windows

    def _chunk_python_treesitter(
        self, filepath: str, content: str, parser: object, lines: list[str]
    ) -> list[dict]:
        """Chunk a Python file using tree-sitter AST."""
        raw = content.encode("utf-8", errors="replace")
        tree = parser.parse(raw)  # type: ignore[attr-defined]
        root = tree.root_node

        chunks: list[dict] = []
        covered: set[int] = set()  # 0-indexed line numbers

        for child in root.children:  # type: ignore[attr-defined]
            # Handle decorated definitions (decorators + def/class)
            if child.type == "decorated_definition":
                inner = next(
                    (c for c in child.children  # type: ignore[attr-defined]
                     if c.type in ("function_definition", "class_definition")),
                    None,
                )
                if inner is None:
                    continue
                def_node = inner
                outer_node = child
            elif child.type in ("function_definition", "class_definition"):
                def_node = child
                outer_node = child
            else:
                continue

            kind = "function" if def_node.type == "function_definition" else "class"
            name_node = next(
                (c for c in def_node.children if c.type == "identifier"),  # type: ignore[attr-defined]
                None,
            )
            if name_node is None:
                continue
            name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]

            start = outer_node.start_point[0]  # type: ignore[attr-defined]
            end = outer_node.end_point[0]      # type: ignore[attr-defined]

            chunk_lines = lines[start:end + 1]
            chunk_content = "\n".join(chunk_lines)

            # Prepend docstring summary for richer embeddings
            summary = self._extract_python_docstring(def_node)
            if summary:
                chunk_content = f"{summary}\n\n{chunk_content}"

            for i in range(start, end + 1):
                covered.add(i)

            chunks.append({
                "doc_id": f"{filepath}::{name}",
                "content": chunk_content,
                "entity_name": name,
                "entity_kind": kind,
                "line_start": start + 1,
                "line_end": end + 1,
            })

        # Module-level chunk: non-empty lines not covered by any definition
        module_lines = [
            lines[i] for i in range(len(lines))
            if i not in covered and lines[i].strip()
        ]
        if module_lines:
            # Check for a module-level docstring
            module_summary = self._summarize_chunk(
                "\n".join(lines[:10]), "module"
            )
            module_content = "\n".join(module_lines)
            if module_summary and not module_content.startswith(module_summary):
                module_content = f"{module_summary}\n\n{module_content}"
            chunks.append({
                "doc_id": f"{filepath}::__module__",
                "content": module_content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": len(lines) or 1,
            })

        if not chunks:
            return [{
                "doc_id": filepath,
                "content": content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": len(lines) or 1,
            }]

        return chunks

    @staticmethod
    def _extract_python_docstring(func_or_class_node: object) -> str:
        """Extract docstring text from a Python function/class AST node."""
        body = next(
            (c for c in func_or_class_node.children if c.type == "block"),  # type: ignore[attr-defined]
            None,
        )
        if body is None:
            return ""
        for child in body.children:  # type: ignore[attr-defined]
            if child.type == "expression_statement":
                str_node = next(
                    (c for c in child.children if c.type == "string"),  # type: ignore[attr-defined]
                    None,
                )
                if str_node is not None:
                    raw = str_node.text.decode("utf-8", errors="replace").strip()  # type: ignore[attr-defined]
                    for q in ('"""', "'''"):
                        if raw.startswith(q) and len(raw) > len(q) * 2:
                            return raw[len(q):raw.rfind(q)].strip()
                    if len(raw) > 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
                        return raw[1:-1]
                break
            elif child.type not in ("comment", "newline", "indent", "\n"):
                break
        return ""

    @staticmethod
    def _summarize_chunk(chunk_content: str, entity_kind: str) -> str:
        """Extract a summary from chunk content for improved embedding quality.

        Looks for the first triple-quoted docstring or leading comment block
        after the entity definition line.  Returns summary text or empty string.
        """
        lines = chunk_content.splitlines()
        i = 0
        # Skip leading decorator / def / class / shebang lines
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith(("@", "def ", "async def ", "class ", "#!")):
                i += 1
                continue
            break

        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                continue
            # Triple-quoted docstring
            for q in ('"""', "'''"):
                if stripped.startswith(q):
                    rest = stripped[len(q):]
                    end_idx = rest.find(q)
                    if end_idx >= 0:
                        # Single-line docstring
                        return rest[:end_idx].strip()
                    # Multi-line: keep scanning
                    doc_parts = [rest]
                    i += 1
                    while i < len(lines):
                        l = lines[i]
                        s = l.strip()
                        end_idx = s.find(q)
                        if end_idx >= 0:
                            doc_parts.append(s[:end_idx])
                            return "\n".join(doc_parts).strip()
                        doc_parts.append(l)
                        i += 1
                    return "\n".join(doc_parts).strip()
            # Leading comment block
            if stripped.startswith("#"):
                comment_lines = []
                while i < len(lines) and lines[i].strip().startswith("#"):
                    comment_lines.append(lines[i].strip().lstrip("#").strip())
                    i += 1
                return "\n".join(comment_lines)
            break  # non-docstring content
        return ""

    def _chunk_regex_fallback(
        self, filepath: str, content: str, lines: list[str], suffix: str
    ) -> list[dict]:
        """Chunk a source file using regex patterns (fallback without tree-sitter)."""
        if suffix == ".py":
            patterns = [
                (re.compile(r"^(?:async\s+)?def\s+(\w+)"), "function"),
                (re.compile(r"^class\s+(\w+)"), "class"),
            ]
        elif suffix in (".ts", ".tsx", ".js", ".jsx"):
            patterns = [
                (re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"), "function"),
                (re.compile(r"^(?:export\s+)?class\s+(\w+)"), "class"),
            ]
        elif suffix == ".cs":
            patterns = [
                (re.compile(r"^\s*(?:public|private|protected|internal|static).*\s+(\w+)\s*\("), "function"),
                (re.compile(r"^\s*(?:public|private|protected|internal)?\s*class\s+(\w+)"), "class"),
            ]
        else:
            patterns = []

        if not patterns:
            return [{
                "doc_id": filepath,
                "content": content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": len(lines) or 1,
            }]

        # Find all top-level definition start lines
        definitions: list[tuple[int, str, str]] = []  # (0-indexed line, name, kind)
        for i, line in enumerate(lines):
            for pattern, kind in patterns:
                m = pattern.match(line)
                if m:
                    definitions.append((i, m.group(1), kind))
                    break

        if not definitions:
            return [{
                "doc_id": filepath,
                "content": content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": len(lines) or 1,
            }]

        chunks: list[dict] = []
        covered: set[int] = set()

        for idx, (start, name, kind) in enumerate(definitions):
            end = (
                definitions[idx + 1][0] - 1
                if idx + 1 < len(definitions)
                else len(lines) - 1
            )
            chunk_lines = lines[start:end + 1]
            chunk_content = "\n".join(chunk_lines)
            summary = self._summarize_chunk(chunk_content, kind)
            if summary and not chunk_content.startswith(summary):
                chunk_content = f"{summary}\n\n{chunk_content}"
            for i in range(start, end + 1):
                covered.add(i)
            chunks.append({
                "doc_id": f"{filepath}::{name}",
                "content": chunk_content,
                "entity_name": name,
                "entity_kind": kind,
                "line_start": start + 1,
                "line_end": end + 1,
            })

        module_lines = [
            lines[i] for i in range(len(lines))
            if i not in covered and lines[i].strip()
        ]
        if module_lines:
            module_content = "\n".join(module_lines)
            chunks.append({
                "doc_id": f"{filepath}::__module__",
                "content": module_content,
                "entity_name": "__module__",
                "entity_kind": "module",
                "line_start": 1,
                "line_end": len(lines) or 1,
            })

        return chunks

    def _index_files(self, files: list[str]) -> None:
        for filepath in files:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
                domain = Path(filepath).suffix.lstrip(".")
                chunks = self._chunk_source_file(filepath, content)
                for chunk in chunks:
                    self._ingest_single(
                        chunk["doc_id"], chunk["content"],
                        source_file=filepath, domain=domain,
                        entity_name=chunk["entity_name"],
                        entity_kind=chunk["entity_kind"],
                        line_start=chunk["line_start"],
                        line_end=chunk["line_end"],
                    )
            except (IOError, OSError):
                pass

    def _ingest_single(
        self,
        doc_id: str,
        content: str,
        source_file: Optional[str] = None,
        domain: Optional[str] = None,
        entity_name: Optional[str] = None,
        entity_kind: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
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
            "(id, source_file, content, domain, content_hash, "
            " entity_name, entity_kind, line_start, line_end) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, source_file, content, domain, chash,
             entity_name, entity_kind, line_start, line_end),
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
        """Extract entities and relationships from source and store in graph.db."""
        suffix = Path(filepath).suffix.lower()
        lang_name = _TS_LANG_MAP.get(suffix)
        parser = _get_treesitter_parser(lang_name) if lang_name else None

        if parser is not None:
            entities, relationships = self._extract_entities_treesitter(
                filepath, content, parser, suffix
            )
        else:
            entities = self._extract_entities(filepath, content)
            relationships = []

        for name, kind, line in entities:
            self._graph.execute(
                "INSERT OR IGNORE INTO entities (name, kind, file, line) "
                "VALUES (?, ?, ?, ?)",
                (name, kind, filepath, line),
            )

        # Ensure all relationship endpoint entities exist before inserting
        for src_name, tgt_name, relation in relationships:
            for ename in (src_name, tgt_name):
                self._graph.execute(
                    "INSERT OR IGNORE INTO entities (name, kind, file, line) "
                    "VALUES (?, ?, ?, ?)",
                    (ename, "unknown", filepath, 0),
                )
            row_src = self._graph.execute(
                "SELECT id FROM entities WHERE name = ? AND file = ? LIMIT 1",
                (src_name, filepath),
            ).fetchone()
            row_tgt = self._graph.execute(
                "SELECT id FROM entities WHERE name = ? LIMIT 1", (tgt_name,)
            ).fetchone()
            if row_src and row_tgt:
                self._graph.execute(
                    "INSERT OR IGNORE INTO relationships (source_id, target_id, relation) "
                    "VALUES (?, ?, ?)",
                    (row_src["id"], row_tgt["id"], relation),
                )

        self._graph.commit()

    @staticmethod
    def _extract_entities_treesitter(
        filepath: str, content: str, parser: object, suffix: str
    ) -> tuple[list[tuple[str, str, int]], list[tuple[str, str, str]]]:
        """Extract entities and relationships via tree-sitter AST.

        Returns:
            (entities, relationships) where:
              entities: list of (name, kind, line_number)
              relationships: list of (source_name, target_name, relation)
                relation in {'calls', 'imports', 'extends'}
        """
        entities: list[tuple[str, str, int]] = []
        relationships: list[tuple[str, str, str]] = []

        raw = content.encode("utf-8", errors="replace")
        tree = parser.parse(raw)  # type: ignore[attr-defined]
        root = tree.root_node
        file_stem = Path(filepath).stem

        if suffix == ".py":
            Brain._ts_extract_python(root, file_stem, entities, relationships)
        elif suffix in (".ts", ".tsx", ".js", ".jsx"):
            Brain._ts_extract_js_ts(root, file_stem, entities, relationships)
        elif suffix == ".cs":
            Brain._ts_extract_csharp(root, file_stem, entities, relationships)

        # File as module entity (always)
        if file_stem:
            entities.append((file_stem, "file", 0))

        return entities, relationships

    @staticmethod
    def _ts_collect_calls(
        node: object,
        container_name: str,
        relationships: list[tuple[str, str, str]],
        call_node_types: tuple[str, ...],
        call_name_extractor,  # callable(call_node) -> str | None
    ) -> None:
        """Walk node subtree collecting call relationships."""
        stack = [node]
        while stack:
            n = stack.pop()
            if n.type in call_node_types:  # type: ignore[attr-defined]
                callee = call_name_extractor(n)
                if callee:
                    relationships.append((container_name, callee, "calls"))
            stack.extend(reversed(n.children))  # type: ignore[attr-defined]

    @staticmethod
    def _ts_extract_python(
        root: object,
        file_stem: str,
        entities: list[tuple[str, str, int]],
        relationships: list[tuple[str, str, str]],
    ) -> None:
        """Extract Python entities and relationships from AST root."""

        def _py_call_name(node: object) -> Optional[str]:
            func = next(
                (c for c in node.children if c.type in ("identifier", "attribute")),  # type: ignore[attr-defined]
                None,
            )
            if func is None:
                return None
            if func.type == "identifier":
                return func.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
            # attribute: foo.bar -> take last identifier
            parts = [c for c in func.children if c.type == "identifier"]  # type: ignore[attr-defined]
            return parts[-1].text.decode("utf-8", errors="replace") if parts else None  # type: ignore[attr-defined]

        def _walk_top(node: object) -> None:
            for child in node.children:  # type: ignore[attr-defined]
                t = child.type
                if t == "import_statement":
                    # import os, sys
                    for name_node in child.children:  # type: ignore[attr-defined]
                        if name_node.type in ("dotted_name", "identifier"):
                            mod = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                            relationships.append((file_stem, mod, "imports"))
                elif t == "import_from_statement":
                    # from pathlib import Path
                    mod_node = next(
                        (c for c in child.children if c.type in ("dotted_name", "relative_import", "identifier")),  # type: ignore[attr-defined]
                        None,
                    )
                    if mod_node:
                        mod = mod_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                        relationships.append((file_stem, mod, "imports"))
                elif t == "class_definition":
                    name_node = next(
                        (c for c in child.children if c.type == "identifier"), None  # type: ignore[attr-defined]
                    )
                    if name_node:
                        cls_name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                        line = name_node.start_point[0] + 1  # type: ignore[attr-defined]
                        entities.append((cls_name, "class", line))
                        # Extends: argument_list children that are identifiers
                        arg_list = next(
                            (c for c in child.children if c.type == "argument_list"), None  # type: ignore[attr-defined]
                        )
                        if arg_list:
                            for base in arg_list.children:  # type: ignore[attr-defined]
                                if base.type == "identifier":
                                    base_name = base.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                                    relationships.append((cls_name, base_name, "extends"))
                        # Methods inside class body
                        body = next(
                            (c for c in child.children if c.type == "block"), None  # type: ignore[attr-defined]
                        )
                        if body:
                            _walk_class_body(body, cls_name)
                elif t == "function_definition" or t == "decorated_definition":
                    _handle_func(child, file_stem)
                elif t == "block":
                    _walk_top(child)

        def _handle_func(node: object, container: str) -> None:
            fn_node = node if node.type == "function_definition" else next(  # type: ignore[attr-defined]
                (c for c in node.children if c.type == "function_definition"), None  # type: ignore[attr-defined]
            )
            if fn_node is None:
                return
            name_node = next(
                (c for c in fn_node.children if c.type == "identifier"), None  # type: ignore[attr-defined]
            )
            if name_node:
                fn_name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                line = name_node.start_point[0] + 1  # type: ignore[attr-defined]
                entities.append((fn_name, "function", line))
                body = next((c for c in fn_node.children if c.type == "block"), None)  # type: ignore[attr-defined]
                if body:
                    Brain._ts_collect_calls(body, fn_name, relationships, ("call",), _py_call_name)

        def _walk_class_body(body: object, cls_name: str) -> None:
            for member in body.children:  # type: ignore[attr-defined]
                if member.type in ("function_definition", "decorated_definition"):
                    _handle_func(member, cls_name)

        _walk_top(root)

    @staticmethod
    def _ts_extract_js_ts(
        root: object,
        file_stem: str,
        entities: list[tuple[str, str, int]],
        relationships: list[tuple[str, str, str]],
    ) -> None:
        """Extract JS/TS entities and relationships from AST root."""

        def _js_call_name(node: object) -> Optional[str]:
            func = next(
                (c for c in node.children if c.type in ("identifier", "member_expression")),  # type: ignore[attr-defined]
                None,
            )
            if func is None:
                return None
            if func.type == "identifier":
                return func.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
            # member_expression: obj.method -> last identifier
            parts = [c for c in func.children if c.type in ("identifier", "property_identifier")]  # type: ignore[attr-defined]
            return parts[-1].text.decode("utf-8", errors="replace") if parts else None  # type: ignore[attr-defined]

        def _walk(node: object) -> None:
            for child in node.children:  # type: ignore[attr-defined]
                t = child.type
                if t == "import_statement":
                    src_node = next(
                        (c for c in child.children if c.type == "string"), None  # type: ignore[attr-defined]
                    )
                    if src_node:
                        raw_mod = src_node.text.decode("utf-8", errors="replace").strip("'\"")  # type: ignore[attr-defined]
                        mod = Path(raw_mod).stem if raw_mod.startswith(".") else raw_mod
                        relationships.append((file_stem, mod, "imports"))
                elif t in ("class_declaration", "class"):
                    _handle_class(child)
                elif t == "export_statement":
                    # export class / export function
                    inner = next(
                        (c for c in child.children if c.type in ("class_declaration", "function_declaration")),  # type: ignore[attr-defined]
                        None,
                    )
                    if inner:
                        if inner.type == "class_declaration":
                            _handle_class(inner)
                        else:
                            _handle_func(inner, file_stem)
                elif t == "function_declaration":
                    _handle_func(child, file_stem)
                elif t in ("lexical_declaration", "variable_declaration"):
                    _walk(child)
                elif t == "variable_declarator":
                    # const Foo = class { ... } or const fn = () => { ... }
                    inner = next(
                        (c for c in child.children if c.type in ("class", "arrow_function", "function")),  # type: ignore[attr-defined]
                        None,
                    )
                    if inner:
                        name_node = next((c for c in child.children if c.type == "identifier"), None)  # type: ignore[attr-defined]
                        if name_node:
                            nm = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                            if inner.type == "class":
                                entities.append((nm, "class", name_node.start_point[0] + 1))  # type: ignore[attr-defined]
                            else:
                                entities.append((nm, "function", name_node.start_point[0] + 1))  # type: ignore[attr-defined]

        def _handle_class(node: object) -> None:
            name_node = next(
                (c for c in node.children if c.type in ("identifier", "type_identifier")), None  # type: ignore[attr-defined]
            )
            if not name_node:
                return
            cls_name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
            entities.append((cls_name, "class", name_node.start_point[0] + 1))  # type: ignore[attr-defined]
            heritage = next((c for c in node.children if c.type == "class_heritage"), None)  # type: ignore[attr-defined]
            if heritage:
                extends = next((c for c in heritage.children if c.type == "extends_clause"), None)  # type: ignore[attr-defined]
                if extends:
                    base = next(
                        (c for c in extends.children if c.type in ("identifier", "type_identifier")), None  # type: ignore[attr-defined]
                    )
                    if base:
                        relationships.append((cls_name, base.text.decode("utf-8", errors="replace"), "extends"))  # type: ignore[attr-defined]
            body = next((c for c in node.children if c.type == "class_body"), None)  # type: ignore[attr-defined]
            if body:
                for member in body.children:  # type: ignore[attr-defined]
                    if member.type == "method_definition":
                        mname_node = next(
                            (c for c in member.children if c.type in ("identifier", "property_identifier")), None  # type: ignore[attr-defined]
                        )
                        if mname_node:
                            mname = mname_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                            entities.append((mname, "method", mname_node.start_point[0] + 1))  # type: ignore[attr-defined]
                            mbody = next((c for c in member.children if c.type == "statement_block"), None)  # type: ignore[attr-defined]
                            if mbody:
                                Brain._ts_collect_calls(mbody, mname, relationships, ("call_expression",), _js_call_name)

        def _handle_func(node: object, container: str) -> None:
            name_node = next((c for c in node.children if c.type == "identifier"), None)  # type: ignore[attr-defined]
            if name_node:
                fn_name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                entities.append((fn_name, "function", name_node.start_point[0] + 1))  # type: ignore[attr-defined]
                body = next((c for c in node.children if c.type == "statement_block"), None)  # type: ignore[attr-defined]
                if body:
                    Brain._ts_collect_calls(body, fn_name, relationships, ("call_expression",), _js_call_name)

        _walk(root)

    @staticmethod
    def _ts_extract_csharp(
        root: object,
        file_stem: str,
        entities: list[tuple[str, str, int]],
        relationships: list[tuple[str, str, str]],
    ) -> None:
        """Extract C# entities and relationships from AST root."""

        def _cs_call_name(node: object) -> Optional[str]:
            func = next(
                (c for c in node.children if c.type in ("identifier", "member_access_expression")),  # type: ignore[attr-defined]
                None,
            )
            if func is None:
                return None
            if func.type == "identifier":
                return func.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
            parts = [c for c in func.children if c.type == "identifier"]  # type: ignore[attr-defined]
            return parts[-1].text.decode("utf-8", errors="replace") if parts else None  # type: ignore[attr-defined]

        def _walk(node: object) -> None:
            for child in node.children:  # type: ignore[attr-defined]
                t = child.type
                if t == "using_directive":
                    name_node = next(
                        (c for c in child.children if c.type in ("identifier", "qualified_name")), None  # type: ignore[attr-defined]
                    )
                    if name_node:
                        mod = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                        relationships.append((file_stem, mod, "imports"))
                elif t in ("namespace_declaration", "declaration_list", "compilation_unit"):
                    _walk(child)
                elif t == "class_declaration":
                    _handle_class(child)

        def _handle_class(node: object) -> None:
            name_node = next((c for c in node.children if c.type == "identifier"), None)  # type: ignore[attr-defined]
            if not name_node:
                return
            cls_name = name_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
            entities.append((cls_name, "class", name_node.start_point[0] + 1))  # type: ignore[attr-defined]
            base_list = next((c for c in node.children if c.type == "base_list"), None)  # type: ignore[attr-defined]
            if base_list:
                for base in base_list.children:  # type: ignore[attr-defined]
                    if base.type == "identifier":
                        relationships.append((cls_name, base.text.decode("utf-8", errors="replace"), "extends"))  # type: ignore[attr-defined]
            body = next((c for c in node.children if c.type == "declaration_list"), None)  # type: ignore[attr-defined]
            if body:
                for member in body.children:  # type: ignore[attr-defined]
                    if member.type == "method_declaration":
                        mname_node = next((c for c in member.children if c.type == "identifier"), None)  # type: ignore[attr-defined]
                        if mname_node:
                            mname = mname_node.text.decode("utf-8", errors="replace")  # type: ignore[attr-defined]
                            entities.append((mname, "method", mname_node.start_point[0] + 1))  # type: ignore[attr-defined]
                            mbody = next((c for c in member.children if c.type == "block"), None)  # type: ignore[attr-defined]
                            if mbody:
                                Brain._ts_collect_calls(mbody, mname, relationships, ("invocation_expression",), _cs_call_name)

        _walk(root)

    @staticmethod
    def _extract_entities(
        filepath: str, content: str
    ) -> list[tuple[str, str, int]]:
        """Extract (name, kind, line) from source content via regex (fallback)."""
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
        self,
        query: str,
        domain: Optional[str],
        limit: int,
        domains: Optional[list[str]] = None,
    ) -> list[dict]:
        safe = re.sub(r"[^\w\s]", " ", query).strip()
        if not safe:
            return []
        try:
            # Multi-domain list takes precedence over single domain.
            if domains:
                placeholders = ",".join("?" * len(domains))
                rows = self._brain.execute(
                    f"SELECT id, bm25(docs_fts) AS score FROM docs_fts "
                    f"WHERE docs_fts MATCH ? AND domain IN ({placeholders}) "
                    f"ORDER BY score, id LIMIT ?",
                    (safe, *domains, limit),
                ).fetchall()
            elif domain:
                rows = self._brain.execute(
                    "SELECT id, bm25(docs_fts) AS score FROM docs_fts "
                    "WHERE docs_fts MATCH ? AND domain = ? ORDER BY score, id LIMIT ?",
                    (safe, domain, limit),
                ).fetchall()
            else:
                rows = self._brain.execute(
                    "SELECT id, bm25(docs_fts) AS score FROM docs_fts "
                    "WHERE docs_fts MATCH ? ORDER BY score, id LIMIT ?",
                    (safe, limit),
                ).fetchall()
            return [{"doc_id": r["id"], "score": -r["score"]} for r in rows]
        except Exception:
            return []

    def _vector_search(
        self,
        query: str,
        domain: Optional[str],
        limit: int,
        domains: Optional[list[str]] = None,
    ) -> list[dict]:
        if not self.vector_enabled:
            return []
        vec = self._embed(query)
        if vec is None:
            return []
        try:
            import struct
            blob = struct.pack(f"{len(vec)}f", *vec)
            # sqlite-vec vec0 doesn't support WHERE on non-vec columns,
            # so over-fetch by 3x when domain filtering is needed, then
            # post-filter by joining doc_id back to the docs table.
            need_filter = bool(domains or domain)
            fetch_limit = limit * 3 if need_filter else limit
            rows = self._brain.execute(
                "SELECT doc_id, distance FROM docs_vec "
                "WHERE embedding MATCH ? AND k = ?",
                (blob, fetch_limit),
            ).fetchall()
            results = [
                {"doc_id": r["doc_id"], "score": 1.0 / (1.0 + r["distance"])}
                for r in rows
            ]
            # Multi-domain list takes precedence over single domain.
            if domains and results:
                doc_ids = [r["doc_id"] for r in results]
                placeholders_ids = ",".join("?" * len(doc_ids))
                placeholders_dom = ",".join("?" * len(domains))
                domain_rows = self._brain.execute(
                    f"SELECT id FROM docs WHERE id IN ({placeholders_ids}) "
                    f"AND domain IN ({placeholders_dom})",
                    (*doc_ids, *domains),
                ).fetchall()
                allowed = {r["id"] for r in domain_rows}
                results = [r for r in results if r["doc_id"] in allowed][:limit]
            elif domain and results:
                doc_ids = [r["doc_id"] for r in results]
                placeholders = ",".join("?" * len(doc_ids))
                domain_rows = self._brain.execute(
                    f"SELECT id FROM docs WHERE id IN ({placeholders}) AND domain = ?",
                    (*doc_ids, domain),
                ).fetchall()
                allowed = {r["id"] for r in domain_rows}
                results = [r for r in results if r["doc_id"] in allowed][:limit]
            return results
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
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
        domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """3-index hybrid search with RRF fusion.

        Auto-bootstraps on first call when the index is empty, and runs
        incremental_reindex() on subsequent calls to stay current.

        Args:
            query: Search query string.
            domain: Single domain filter (e.g. 'py', 'expertise').
            limit: Maximum results to return.
            domains: Multi-domain filter list; takes precedence over ``domain``.
                     When provided, results are restricted to docs whose domain
                     is in this list (e.g. ['expertise', 'md'] for SM persona).
        """
        # NOTE: Auto-bootstrap disabled for service mode.
        # In CLI mode the Brain auto-ingests CWD on first search.
        # In service mode, documents are indexed via brain_index_doc MCP tool.
        # The old CLI auto-ingest would index /app (the container code) which is wrong.
        import os as _os

        inner = limit * 2

        # Experimental: PRISM_SEARCH_MODE controls which indices contribute.
        #   hybrid (default) = BM25 + vector + graph, fused via RRF
        #   vector           = vector search only (when vector_enabled)
        #   bm25             = BM25 only
        mode = _os.environ.get("PRISM_SEARCH_MODE", "hybrid").strip().lower()

        if mode == "vector" and self.vector_enabled:
            fused = self._vector_search(query, domain, inner, domains=domains)
        elif mode == "bm25":
            fused = self._fts5_search(query, domain, inner, domains=domains)
        else:
            bm25 = self._fts5_search(query, domain, inner, domains=domains)
            vec = (
                self._vector_search(query, domain, inner, domains=domains)
                if self.vector_enabled
                else []
            )
            graph = self._graph_search(query, inner)
            fused = reciprocal_rank_fusion(
                [bm25, vec, graph] if self.vector_enabled else [bm25, graph]
            )
        top = fused[:limit]
        if not top:
            return []

        ids = [item["doc_id"] for item in top]
        placeholders = ",".join("?" * len(ids))
        rows = self._brain.execute(
            f"SELECT id, content, domain, entity_name, entity_kind, line_start, line_end "
            f"FROM docs WHERE id IN ({placeholders})",
            ids,
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
                    "entity_name": row["entity_name"],
                    "entity_kind": row["entity_kind"],
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "rrf_score": item.get("rrf_score", 0.0),
                })
        return results

    def system_context(
        self,
        story_file: Optional[str] = None,
        persona: Optional[str] = None,
        limit: int = 8,
    ) -> str:
        """Run hybrid search from story/persona context and return formatted block.

        When ``persona`` matches a known PRISM role (sm/qa/dev/po/architect/engineer),
        search results are filtered to role-relevant domains via ROLE_DOMAIN_MAP.
        If the filtered search yields no results, falls back to unfiltered search.
        """
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

        # Resolve role-specific domain filter from persona.
        role_domains: Optional[list[str]] = None
        if persona:
            role_key = persona.lower().strip()
            role_domains = self.ROLE_DOMAIN_MAP.get(role_key)

        results = self.search(query, limit=limit, domains=role_domains)
        # If role-filtered search returned nothing, fall back to unfiltered.
        if not results and role_domains:
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

    def _ingest_mulch_expertise(self) -> int:
        """Ingest .mulch/expertise/*.jsonl files into Brain with domain='expertise'.

        Each JSONL record is indexed as a separate document. Content is built from
        description, content, and resolution fields (whichever are present).
        The domain name from the filename stem is embedded in the content.

        Returns count of newly indexed records.
        """
        expertise_dir = Path(".mulch") / "expertise"
        if not expertise_dir.exists():
            return 0

        count = 0
        for jsonl_file in sorted(expertise_dir.glob("*.jsonl")):
            domain_name = jsonl_file.stem  # e.g. "brain", "cli", "hooks"
            try:
                lines = jsonl_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except (IOError, OSError):
                continue
            for raw in lines:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue

                rec_id = record.get("id") or ""
                if not rec_id:
                    continue

                doc_id = f"expertise:{domain_name}:{rec_id}"
                parts: list[str] = [f"[expertise:{domain_name}]"]
                if record.get("name"):
                    parts.append(f"name: {record['name']}")
                if record.get("type"):
                    parts.append(f"type: {record['type']}")
                if record.get("description"):
                    parts.append(record["description"])
                if record.get("content"):
                    parts.append(record["content"])
                if record.get("resolution"):
                    parts.append(f"resolution: {record['resolution']}")

                content = "\n".join(parts)
                if self._ingest_single(
                    doc_id,
                    content,
                    source_file=str(jsonl_file),
                    domain="expertise",
                ):
                    count += 1
        return count

    def _ingest_overstory_logs(self) -> int:
        """Ingest .overstory/logs/**/*.ndjson into Brain with domain='sessions'.

        Each NDJSON file is indexed as one document. Content is built from
        event fields (timestamp, event, agentName, data). Uses source_file=None
        to avoid _purge_deleted() conflicts (.overstory is an excluded path segment).

        Returns count of newly indexed records.
        """
        logs_dir = Path(".overstory") / "logs"
        if not logs_dir.exists():
            return 0

        count = 0
        for ndjson_file in sorted(logs_dir.rglob("*.ndjson")):
            try:
                lines = ndjson_file.read_text(encoding="utf-8", errors="replace").splitlines()
            except (IOError, OSError):
                continue

            events = []
            for raw in lines:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                    if isinstance(event, dict):
                        events.append(event)
                except json.JSONDecodeError:
                    continue

            if not events:
                continue

            # Build searchable content from event fields
            rel = str(ndjson_file)
            parts: list[str] = [f"[sessions] {ndjson_file.parent.name} {ndjson_file.stem}"]
            for event in events:
                ts = event.get("timestamp", "")[:19]
                ev = event.get("event", "")
                agent = event.get("agentName", "")
                data = event.get("data") or {}
                msg = ""
                if isinstance(data, dict):
                    msg = (
                        data.get("message")
                        or data.get("toolName")
                        or data.get("text")
                        or ""
                    )
                line_parts = [x for x in [ts, ev, agent, str(msg)[:80]] if x]
                if line_parts:
                    parts.append(" ".join(line_parts))

            doc_id = f"sessions:{rel}"
            content = "\n".join(parts)
            # source_file=None: .overstory is excluded from _should_index(), so
            # passing the real path would cause _purge_deleted() to remove this entry.
            if self._ingest_single(doc_id, content, source_file=None, domain="sessions"):
                count += 1

        return count

    def ingest(self, sources: list[str]) -> int:
        """Full index of all provided file paths or directories. Returns doc count."""
        count = 0
        for source in sources:
            p = Path(source)
            if not p.exists():
                continue
            if p.is_file() and self._should_index(source):
                content = p.read_text(encoding="utf-8", errors="replace")
                domain = p.suffix.lstrip(".")
                chunks = self._chunk_source_file(source, content)
                for chunk in chunks:
                    if self._ingest_single(
                        chunk["doc_id"], chunk["content"],
                        source_file=source, domain=domain,
                        entity_name=chunk["entity_name"],
                        entity_kind=chunk["entity_kind"],
                        line_start=chunk["line_start"],
                        line_end=chunk["line_end"],
                    ):
                        count += 1
            elif p.is_dir():
                for child in p.rglob("*"):
                    if child.is_file() and self._should_index(str(child)):
                        try:
                            content = child.read_text(encoding="utf-8", errors="replace")
                            rel = str(child)
                            domain = child.suffix.lstrip(".")
                            chunks = self._chunk_source_file(rel, content)
                            for chunk in chunks:
                                if self._ingest_single(
                                    chunk["doc_id"], chunk["content"],
                                    source_file=rel, domain=domain,
                                    entity_name=chunk["entity_name"],
                                    entity_kind=chunk["entity_kind"],
                                    line_start=chunk["line_start"],
                                    line_end=chunk["line_end"],
                                ):
                                    count += 1
                        except (IOError, OSError):
                            pass
        count += self._ingest_mulch_expertise()
        count += self._ingest_overstory_logs()
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

    def record_session_outcome(
        self,
        session_id: str,
        duration_s: int,
        tokens_used: int,
        files_read: int,
        files_modified: int,
        skills_invoked: int,
    ) -> None:
        """Upsert session-level outcome metrics into session_outcomes table."""
        self._scores.execute(
            "INSERT OR REPLACE INTO session_outcomes "
            "(session_id, duration_s, tokens_used, files_read, files_modified, skills_invoked, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (session_id, duration_s, tokens_used, files_read, files_modified, skills_invoked),
        )
        self._scores.commit()

    def record_skill_usage(
        self,
        session_id: str,
        skill_name: str,
        timestamp: str = "",
    ) -> None:
        """Record a skill invocation into skill_usage table."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        self._scores.execute(
            "INSERT INTO skill_usage (session_id, skill_name, timestamp) VALUES (?, ?, ?)",
            (session_id, skill_name, ts),
        )
        self._scores.commit()


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

def _cli_source_dirs() -> list[str]:
    """Return source directories to index, mirroring brain_bootstrap logic.

    NOTE: Legacy CLI-only function. Not used in MCP service mode — documents
    are indexed via the brain_index_doc MCP tool instead.
    """
    sources: list[str] = []
    cwd = Path.cwd()
    engine_root = Path(__file__).resolve().parent.parent  # legacy: was plugin_root
    docs_dir = cwd / "docs"
    if docs_dir.exists():
        sources.append(str(docs_dir))
    core_steps = engine_root / "hooks" / "core-steps"
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


def _cmd_graph(brain: "Brain", entity: str) -> int:
    results = brain.graph_query(entity)
    if not results:
        print(f"No relationships found for entity '{entity}'")
        return 0
    for r in results:
        name = r.get("name", "?")
        kind = r.get("kind", "?")
        file_ = r.get("file", "?")
        relation = r.get("relation", "?")
        print(f"  --[{relation}]--> {name} ({kind})  {file_}")
    return 0


def _cmd_explain(brain: "Brain", filepath: str) -> int:
    rows = brain._brain.execute(
        "SELECT id, domain, content FROM docs WHERE source_file = ? OR id LIKE ? ORDER BY id",
        (filepath, f"%{filepath}%"),
    ).fetchall()
    if not rows:
        print(f"No indexed chunks found for '{filepath}'")
        return 0
    print(f"Brain knowledge for: {filepath}")
    print(f"  {len(rows)} chunk(s) indexed")
    for row in rows:
        snippet = row["content"][:200].replace("\n", " ")
        domain = row["domain"] or "—"
        print(f"\n  [chunk] {row['id']}  domain={domain}")
        print(f"    {snippet}")
    entities = brain._graph.execute(
        "SELECT name, kind FROM entities WHERE file = ? LIMIT 20", (filepath,)
    ).fetchall()
    if entities:
        print(f"\n  Graph entities ({len(entities)}):")
        for e in entities:
            print(f"    {e['name']} ({e['kind']})")
    return 0


def _cmd_rebuild(brain: "Brain") -> int:
    brain._purge_deleted()
    sources = _cli_source_dirs()
    count = brain.ingest(sources)
    if brain.vector_enabled:
        mode = "Full \u2014 BM25+Vector+GraphRAG"
    else:
        mode = "BM25+GraphRAG"
    print(f"Brain: rebuilt index — {count} documents from {len(sources)} source(s) (mode: {mode})")
    return 0


def _cmd_analytics(brain: "Brain") -> int:
    outcomes_file = Path(brain._scores_db_path).parent / "outcomes.jsonl"
    if not outcomes_file.exists():
        print("No outcomes recorded yet.")
        return 0

    records: list[dict] = []
    try:
        for raw in outcomes_file.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    except (IOError, OSError):
        print("Error reading outcomes.jsonl", file=sys.stderr)
        return 1

    if not records:
        print("No outcomes recorded yet.")
        return 0

    print(f"Brain Analytics — {len(records)} total outcome(s)\n")

    # Group by persona/step
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in records:
        key = (r.get("persona") or "?", r.get("step_id") or "?")
        groups.setdefault(key, []).append(r)

    print(f"{'Persona/Step':<42} {'Runs':>5} {'Avg':>7} {'Best':>7} {'Worst':>7}")
    print("-" * 72)
    for (persona, step), outcomes in sorted(groups.items()):
        scores = [float(o["score"]) for o in outcomes if "score" in o]
        if scores:
            avg = sum(scores) / len(scores)
            print(
                f"{persona + '/' + step:<42} {len(outcomes):>5}"
                f" {avg:>7.3f} {max(scores):>7.3f} {min(scores):>7.3f}"
            )

    # Recent trend (last 10)
    recent = sorted(records, key=lambda r: r.get("timestamp") or "", reverse=True)[:10]
    print(f"\nRecent outcomes (last {len(recent)}):")
    for r in recent:
        ts = (r.get("timestamp") or "?")[:19]
        pid = r.get("prompt_id") or "?"
        score = float(r.get("score") or 0.0)
        print(f"  {ts}  {pid:<40}  score={score:.3f}")

    return 0


def _print_usage() -> None:
    print("Usage: python3 brain_engine.py <command> [args]")
    print("")
    print("Commands:")
    print("  init              Index project source files")
    print("  ingest            Re-index all sources (same as init)")
    print("  search <query>    Search indexed knowledge")
    print("  status            Show index health and statistics")
    print("  graph <entity>    Show entity relationships in the graph")
    print("  explain <file>    Show what Brain knows about a file")
    print("  rebuild           Full purge + reindex")
    print("  analytics         Show outcome trends from outcomes.jsonl")


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
    elif cmd == "graph":
        if len(args) < 2:
            print("Error: graph requires an entity argument", file=sys.stderr)
            _print_usage()
            sys.exit(1)
        rc = _cmd_graph(b, " ".join(args[1:]))
    elif cmd == "explain":
        if len(args) < 2:
            print("Error: explain requires a file argument", file=sys.stderr)
            _print_usage()
            sys.exit(1)
        rc = _cmd_explain(b, args[1])
    elif cmd == "rebuild":
        rc = _cmd_rebuild(b)
    elif cmd == "analytics":
        rc = _cmd_analytics(b)
    else:
        print(f"Error: unknown command '{cmd}'", file=sys.stderr)
        _print_usage()
        sys.exit(1)

    sys.exit(rc)
