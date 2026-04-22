"""Graph service — wraps graphify CLI for code knowledge graph extraction.

graphify provides:
  * Tree-sitter AST pass (6+ languages, deterministic, no LLM needed)
  * Cross-file call graph edges with EXTRACTED/INFERRED/AMBIGUOUS confidence
  * Leiden community detection (Newman-style clustering)
  * Rationale tag extraction (# WHY:, # HACK:, # NOTE:)

PRISM stages MCP-ingested source files into a per-project directory, invokes
`graphify update <dir>` (the LLM-free pass), and parses the resulting
`graphify-out/graph.json` into the project's `graph.db`. The existing
Brain engine `_graph_search` then queries the richer tables.

Design choices:
  * Staging dir lives under the project's data dir on the mounted volume,
    so it survives container restart but is project-isolated.
  * Rebuild is explicit (via MCP tool `graph_rebuild`) rather than per-ingest:
    graphify is cheap on small repos but re-running per doc is wasteful.
  * Tree-sitter fallback in brain_engine remains for projects that haven't
    called graph_rebuild yet.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional


# Map of common source-code suffixes that graphify knows how to parse.
# Ingested docs with these suffixes will be staged for the graph pass.
GRAPHIFY_CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".cs",
    ".go", ".rs", ".java", ".rb", ".php", ".cpp", ".c", ".h", ".hpp",
    ".md",  # graphify also picks up heading structure from markdown
}


def _graph_schema_migrations(conn: sqlite3.Connection) -> None:
    """Add graphify-specific columns + communities table.
    Safe to call repeatedly — each ALTER is idempotent."""
    # entities extensions
    ent_cols = {row[1] for row in conn.execute("PRAGMA table_info(entities)").fetchall()}
    for col, sql in (
        ("graphify_id",     "ALTER TABLE entities ADD COLUMN graphify_id TEXT"),
        ("label",           "ALTER TABLE entities ADD COLUMN label TEXT"),
        ("file_type",       "ALTER TABLE entities ADD COLUMN file_type TEXT"),
        ("community",       "ALTER TABLE entities ADD COLUMN community INTEGER"),
        ("source_location", "ALTER TABLE entities ADD COLUMN source_location TEXT"),
    ):
        if col not in ent_cols:
            try:
                conn.execute(sql); conn.commit()
            except sqlite3.OperationalError:
                pass

    # relationships extensions
    rel_cols = {row[1] for row in conn.execute("PRAGMA table_info(relationships)").fetchall()}
    for col, sql in (
        ("confidence",        "ALTER TABLE relationships ADD COLUMN confidence TEXT"),
        ("confidence_score",  "ALTER TABLE relationships ADD COLUMN confidence_score REAL"),
        ("weight",            "ALTER TABLE relationships ADD COLUMN weight REAL"),
        ("source_location",   "ALTER TABLE relationships ADD COLUMN source_location TEXT"),
    ):
        if col not in rel_cols:
            try:
                conn.execute(sql); conn.commit()
            except sqlite3.OperationalError:
                pass

    # Communities — human-readable labels derived from dominant content
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS communities ("
            "  id INTEGER PRIMARY KEY,"
            "  label TEXT,"
            "  size INTEGER,"
            "  top_files TEXT,"       # JSON array
            "  top_entities TEXT,"    # JSON array
            "  summary TEXT"          # 1-2 sentence prose summary
            ")"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # Migrate existing DBs: add summary column if missing.
    try:
        cols = {row[1] for row in conn.execute(
            "PRAGMA table_info(communities)"
        ).fetchall()}
        if "summary" not in cols:
            conn.execute("ALTER TABLE communities ADD COLUMN summary TEXT")
            conn.commit()
    except sqlite3.OperationalError:
        pass

    # index on graphify_id for fast upsert
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ent_graphify_id "
                     "ON entities(graphify_id) WHERE graphify_id IS NOT NULL")
        conn.commit()
    except sqlite3.OperationalError:
        pass


# ---------------------------------------------------------------------------
# Community label derivation
# ---------------------------------------------------------------------------

import re as _re
from collections import Counter as _Counter

_WORD_RE = _re.compile(r"[A-Za-z][A-Za-z0-9]*")


def _basename_stem(path: str) -> str:
    """'services/prism-service/app/engines/brain_engine.py' -> 'brain_engine'."""
    if not path:
        return ""
    tail = path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return tail.rsplit(".", 1)[0]


def _humanize(stem: str) -> str:
    """brain_engine -> brain engine; BrainEngine -> brain engine.
    Trims trailing punctuation and caps to a readable length."""
    if not stem:
        return ""
    # split camelCase/PascalCase
    s = _re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", stem)
    s = s.replace("_", " ").replace("-", " ")
    words = [w.lower().rstrip(".,:;") for w in s.split()]
    # Drop leading/trailing noise words
    result = " ".join(w for w in words if w)
    # Keep first ~6 words so hub descriptors from docstrings stay compact
    first_six = result.split(" ", 6)
    if len(first_six) > 6:
        result = " ".join(first_six[:6])
    # Hard cap on total chars
    if len(result) > 42:
        result = result[:39].rstrip() + "…"
    return result


_GENERIC_ENTITY_NAMES = {
    "__init__", "init", "main", "run", "setup", "config", "module",
    "self", "cls", "args", "kwargs", "value", "result", "data",
}


def _pick_hub_entity(entities_ranked: list[tuple[dict, int]]) -> str:
    """Pick a meaningful entity name from the highest-degree nodes.

    Two passes:
      1. Strict: skip dunders, single-letter, generic placeholders.
      2. Relaxed: accept anything non-empty. Guarantees sibling communities
         from the same dominant file still get distinct labels.
    """
    def _clean(name: str) -> str:
        return (name or "").strip().lstrip(".").rstrip("()").replace("()", "")

    # Strict pass
    for node, deg in entities_ranked:
        name = _clean(node.get("label") or node.get("id") or "")
        if (deg > 0 and name and not name.startswith("__")
                and len(name) > 1
                and name.lower() not in _GENERIC_ENTITY_NAMES):
            return name
    # Relaxed pass — include degree 0 and dunders; avoid only empty strings
    for node, deg in entities_ranked:
        name = _clean(node.get("label") or node.get("id") or "")
        if name and len(name) > 1:
            return name
    return ""


def _derive_community_label(
    nodes: list[dict],
    in_degree: dict,
) -> tuple[str, list[str], list[str]]:
    """Return (label, top_files, top_entities) for a community.

    Heuristic:
      * Primary descriptor = dominant source-file basename.
      * Secondary descriptor = highest-degree NON-GENERIC entity in the
        community. Appended as "<file> · <hub>" to distinguish sibling
        communities that share a huge dominant file (e.g. brain_engine.py
        splits into 9 sub-clusters — each now gets named by its hub entity).
    """
    file_counts: _Counter = _Counter()
    for n in nodes:
        sf = n.get("source_file") or ""
        if sf:
            file_counts[_basename_stem(sf)] += 1

    total = sum(file_counts.values()) or 1
    top = file_counts.most_common(4)
    top_files = [t[0] for t in top]

    # Rank entities in this community by in-degree (connectedness)
    entity_scores = sorted(
        ((n, in_degree.get(n.get("id", ""), 0)) for n in nodes),
        key=lambda x: -x[1],
    )
    top_entities = [
        n.get("label") or n.get("id", "")
        for n, _ in entity_scores[:5]
        if (n.get("label") or n.get("id"))
    ]
    hub = _pick_hub_entity(entity_scores)

    if top:
        first, first_n = top[0]
        first_frac = first_n / total
        if first_frac >= 0.55:
            base = _humanize(first)
            # For mega-files (most of the community from one file), append
            # the hub entity so sibling communities from the same file stay
            # distinguishable.
            label = f"{base} · {_humanize(hub)}" if hub else base
        elif len(top) >= 2 and (top[0][1] + top[1][1]) / total >= 0.70:
            label = f"{_humanize(top[0][0])} + {_humanize(top[1][0])}"
            if hub:
                label = f"{label} · {_humanize(hub)}"
        else:
            # dispersed — use hub entity if we have one, else top file
            if hub:
                label = _humanize(hub)
            else:
                label = _humanize(top[0][0]) or "mixed"
    else:
        label = _humanize(hub) if hub else "misc"

    return label, top_files, top_entities


def _derive_community_summary(
    top_files: list[str],
    top_entities: list[str],
    brain_db_path: str | None,
    max_chars: int = 280,
) -> str:
    """Return a short prose summary for a community.

    Looks up the top entities in the Brain ``docs`` table and concatenates
    the first line of each chunk (which includes any prepended docstring
    from ``_chunk_python_treesitter``). Falls back to a structural summary
    when Brain content is unavailable.
    """
    structural = ""
    if top_files:
        head = ", ".join(top_files[:2])
        structural = f"Covers {head}."
    if not brain_db_path or not top_entities:
        if top_entities:
            structural += " Hubs: " + ", ".join(top_entities[:3]) + "."
        return structural[:max_chars].strip()

    import sqlite3 as _sq
    import re as _re
    snippets: list[str] = []
    try:
        conn = _sq.connect(brain_db_path)
        conn.row_factory = _sq.Row
        try:
            for ename in top_entities[:4]:
                if not ename:
                    continue
                # Graphify entity labels can carry call syntax or punctuation
                # (".execute()", "Brain._get", "_make_brain_in()"). Brain.db
                # stores bare identifiers, so normalize before lookup.
                clean = _re.sub(r"[()\s]", "", ename)
                clean = clean.lstrip(".").split(".")[-1]
                if not clean or clean.endswith(".py") or clean.endswith(".md"):
                    continue
                row = conn.execute(
                    "SELECT content FROM docs WHERE entity_name = ? "
                    "LIMIT 1",
                    (clean,),
                ).fetchone()
                if not row:
                    continue
                first = (row["content"] or "").strip().splitlines()
                first = next((ln.strip() for ln in first if ln.strip()), "")
                first = first.lstrip('"').lstrip("'").rstrip(".")[:80]
                if first:
                    snippets.append(f"{clean}: {first}")
                if sum(len(s) for s in snippets) > max_chars:
                    break
        finally:
            conn.close()
    except Exception:
        pass

    body = ". ".join(snippets)
    if structural and body:
        out = f"{structural} {body}."
    elif body:
        out = body + "."
    else:
        out = structural or " ".join(top_entities[:3])
    return out[:max_chars].strip()


class GraphService:
    """Per-project graphify runner + graph.db importer.

    Instantiate with the project's data dir (where brain.db / graph.db live).
    Call `stage_doc()` from brain_index_doc to write source files into the
    graphify staging area; call `rebuild()` to re-run graphify and re-import.
    """

    def __init__(self, project_data_dir: str, graph_db_path: str) -> None:
        self._project_dir = Path(project_data_dir)
        self._staging_dir = self._project_dir / "graphify-src"
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        self._graph_db = graph_db_path

    # ------------------------------------------------------------------
    # Ingestion: stage doc content to disk for graphify to read
    # ------------------------------------------------------------------

    def stage_doc(self, path: str, content: str) -> bool:
        """Write `content` to staging dir at `path`. Returns True if staged."""
        suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
        if suffix not in GRAPHIFY_CODE_SUFFIXES:
            return False
        # Normalize path (no absolute, no ..)
        rel = Path(path).as_posix().lstrip("/")
        if ".." in Path(rel).parts:
            return False
        dest = self._staging_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(content, encoding="utf-8")
            return True
        except OSError:
            return False

    def unstage_doc(self, path: str) -> bool:
        rel = Path(path).as_posix().lstrip("/")
        dest = self._staging_dir / rel
        if dest.exists():
            try:
                dest.unlink()
                return True
            except OSError:
                pass
        return False

    # ------------------------------------------------------------------
    # graphify invocation
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Backfill staging from the Brain docs table when it's empty. Protects
    # against the "old project upgraded before graphify existed" case where
    # docs were ingested long ago but nothing was staged for the code graph.
    # ------------------------------------------------------------------

    def backfill_from_brain(self, brain_db_path: str) -> int:
        """Stage every code-suffix doc from the Brain docs table.
        Returns the number of files staged. Safe to call repeatedly —
        will overwrite existing staged content with latest from docs."""
        try:
            conn = sqlite3.connect(brain_db_path)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return 0
        n = 0
        try:
            rows = conn.execute(
                "SELECT id, source_file, content FROM docs"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()
        for row in rows:
            # doc_id is typically "<path>::main"; source_file is the raw path
            path = row["source_file"] or row["id"].removesuffix("::main")
            if self.stage_doc(path, row["content"] or ""):
                n += 1
        return n

    def sync_status(self, brain_db_path: str,
                    file_hashes: dict | None = None) -> dict:
        """Report whether the graph is in sync with docs. Non-mutating.

        If `file_hashes` is provided ({path: sha256}), we also compare
        disk state against Brain's stored content_hash for each path and
        return a precise `drifted` list:
          [{path, reason: 'missing'|'content_changed'}]
        This is the signal the SessionStart hook uses to decide which
        files to re-push via prism_refresh.
        """
        import sqlite3 as _sq3
        try:
            from app.__version__ import PRISM_VERSION as _ver
        except Exception:
            _ver = "unknown"
        out: dict = {"prism_version": _ver,
                     "docs": 0, "code_docs": 0, "staged_files": 0,
                     "entities": 0, "entities_with_graphify_id": 0,
                     "relationships": 0, "communities": 0,
                     "stale": False, "reasons": [],
                     "drifted": [], "drift_checked": False}
        try:
            b = _sq3.connect(brain_db_path); b.row_factory = _sq3.Row
            out["docs"] = b.execute("SELECT COUNT(*) FROM docs").fetchone()[0]
            out["code_docs"] = sum(1 for r in b.execute(
                "SELECT source_file FROM docs"
            ) if (r["source_file"] or "").lower().rsplit(".", 1)[-1]
               in {s.lstrip(".") for s in GRAPHIFY_CODE_SUFFIXES})
            b.close()
        except _sq3.Error:
            pass
        try:
            out["staged_files"] = sum(
                1 for p in self._staging_dir.rglob("*")
                if p.is_file() and "graphify-out" not in p.parts
                and "cache" not in p.parts
            )
        except OSError:
            pass
        try:
            g = _sq3.connect(self._graph_db); g.row_factory = _sq3.Row
            out["entities"] = g.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            try:
                out["entities_with_graphify_id"] = g.execute(
                    "SELECT COUNT(*) FROM entities WHERE graphify_id IS NOT NULL"
                ).fetchone()[0]
                out["relationships"] = g.execute(
                    "SELECT COUNT(*) FROM relationships"
                ).fetchone()[0]
                out["communities"] = g.execute(
                    "SELECT COUNT(DISTINCT community) FROM entities "
                    "WHERE community IS NOT NULL"
                ).fetchone()[0]
            except _sq3.OperationalError:
                pass
            g.close()
        except _sq3.Error:
            pass

        # Staleness heuristics (count-based fallbacks)
        if out["code_docs"] > 0 and out["staged_files"] == 0:
            out["stale"] = True
            out["reasons"].append(
                f"{out['code_docs']} code docs in Brain but staging dir is "
                f"empty — call prism_sync to backfill + rebuild"
            )
        if out["entities"] > 0 and out["entities_with_graphify_id"] == 0:
            out["stale"] = True
            out["reasons"].append(
                "graph.db has entities but none carry graphify_id — legacy "
                "tree-sitter output; call graph_rebuild to refresh"
            )
        if out["code_docs"] > 0 and out["staged_files"] < out["code_docs"] // 2:
            out["stale"] = True
            out["reasons"].append(
                f"only {out['staged_files']}/{out['code_docs']} code docs "
                f"are staged — call prism_sync"
            )

        # Content-hash drift detection — precise per-file staleness. Given
        # {path: sha256} from the caller, diff against docs.content_hash and
        # report exactly which files need re-ingestion.
        if file_hashes:
            out["drift_checked"] = True
            stored: dict[str, str] = {}
            try:
                b = _sq3.connect(brain_db_path); b.row_factory = _sq3.Row
                for r in b.execute(
                    "SELECT source_file, content_hash FROM docs "
                    "WHERE content_hash IS NOT NULL"
                ):
                    sf = r["source_file"] or ""
                    if sf:
                        stored[sf] = r["content_hash"]
                b.close()
            except _sq3.Error:
                pass

            for path, sha in file_hashes.items():
                got = stored.get(path)
                if got is None:
                    out["drifted"].append({"path": path, "reason": "missing"})
                elif got != sha:
                    out["drifted"].append({"path": path, "reason": "content_changed"})

            if out["drifted"]:
                out["stale"] = True
                out["reasons"].append(
                    f"{len(out['drifted'])} file(s) drifted vs disk — call "
                    f"prism_refresh with their current content"
                )

        return out

    def rebuild(self, brain_db_path: str | None = None) -> dict:
        """Run `graphify update <staging>` and import resulting graph.json.

        If `brain_db_path` is provided and staging is empty, backfill it from
        the Brain docs table first. Prevents the "stale graph after upgrade"
        case where docs exist but nothing was ever staged for the graph.

        Returns a summary: {nodes, edges, communities, imported_entities,
        imported_relationships, backfilled}.
        """
        result: dict = {"nodes": 0, "edges": 0, "communities": 0,
                        "imported_entities": 0, "imported_relationships": 0,
                        "backfilled": 0}

        # Auto-backfill if staging is empty
        if brain_db_path and not any(self._staging_dir.rglob("*")):
            result["backfilled"] = self.backfill_from_brain(brain_db_path)

        if not any(self._staging_dir.rglob("*")):
            result["message"] = "no staged source files yet"
            return result

        # graphify CLI writes graph.json into <target>/graphify-out/ regardless
        # of cwd, so we just pass the staging dir as target.
        proc = subprocess.run(
            ["graphify", "update", str(self._staging_dir)],
            cwd=str(self._project_dir),
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            result["error"] = (proc.stderr or proc.stdout or "").strip()[:500]
            return result

        graph_json_path = self._staging_dir / "graphify-out" / "graph.json"
        if not graph_json_path.exists():
            result["error"] = "graphify ran but no graph.json produced"
            return result

        try:
            data = json.loads(graph_json_path.read_text(encoding="utf-8"))
        except Exception as e:
            result["error"] = f"graph.json parse failed: {e!r}"
            return result

        return self._import_graph_json(data, result, brain_db_path)

    # ------------------------------------------------------------------
    # graph.json -> graph.db import
    # ------------------------------------------------------------------

    def _import_graph_json(
        self,
        data: dict,
        result: dict,
        brain_db_path: str | None = None,
    ) -> dict:
        nodes = data.get("nodes", [])
        links = data.get("links", [])
        result["nodes"] = len(nodes)
        result["edges"] = len(links)
        result["communities"] = len({n.get("community") for n in nodes
                                      if n.get("community") is not None})

        # Total degree (in + out) for community label derivation — captures
        # both "called-by" hubs and "calls-a-lot" orchestrators.
        in_degree: dict = {}
        for link in links:
            src = link.get("source") or link.get("_src")
            tgt = link.get("target") or link.get("_tgt")
            if src:
                in_degree[src] = in_degree.get(src, 0) + 1
            if tgt:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        conn = sqlite3.connect(self._graph_db)
        conn.row_factory = sqlite3.Row
        try:
            _graph_schema_migrations(conn)
            # Wipe + re-import: the graph is a full snapshot, not an incremental diff
            conn.execute("DELETE FROM relationships")
            conn.execute("DELETE FROM entities")

            # Import nodes → entities. Use graphify's id as the natural key.
            id_map: dict[str, int] = {}
            for node in nodes:
                gid = node.get("id", "")
                if not gid:
                    continue
                label = node.get("label", gid)
                file_type = node.get("file_type", "")
                community = node.get("community")
                source_file = node.get("source_file", "")
                source_location = node.get("source_location", "")
                # Derive "kind" from file_type or label for legacy queries
                kind = file_type or "node"
                cur = conn.execute(
                    "INSERT INTO entities "
                    "(name, kind, file, line, graphify_id, label, file_type, "
                    " community, source_location) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(name, file) DO UPDATE SET "
                    "  kind=excluded.kind, "
                    "  graphify_id=excluded.graphify_id, "
                    "  label=excluded.label, "
                    "  file_type=excluded.file_type, "
                    "  community=excluded.community, "
                    "  source_location=excluded.source_location",
                    (label, kind, source_file, _extract_line(source_location),
                     gid, label, file_type, community, source_location),
                )
                # Retrieve id (RETURNING not universally available pre-3.35)
                row = conn.execute(
                    "SELECT id FROM entities WHERE graphify_id = ?", (gid,)
                ).fetchone()
                if row:
                    id_map[gid] = row["id"]
                    result["imported_entities"] += 1

            # Import links → relationships
            for link in links:
                src_gid = link.get("source") or link.get("_src")
                tgt_gid = link.get("target") or link.get("_tgt")
                src_id = id_map.get(src_gid)
                tgt_id = id_map.get(tgt_gid)
                if src_id is None or tgt_id is None:
                    continue
                relation = link.get("relation", "related")
                confidence = link.get("confidence", "EXTRACTED")
                confidence_score = float(link.get("confidence_score", 1.0))
                weight = float(link.get("weight", 1.0))
                source_location = link.get("source_location", "")
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO relationships "
                        "(source_id, target_id, relation, confidence, "
                        " confidence_score, weight, source_location) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (src_id, tgt_id, relation, confidence,
                         confidence_score, weight, source_location),
                    )
                    result["imported_relationships"] += 1
                except sqlite3.IntegrityError:
                    pass

            # -- Derive + persist community labels -----------------------
            from collections import defaultdict
            buckets: dict[int, list[dict]] = defaultdict(list)
            for n in nodes:
                cid = n.get("community")
                if cid is not None:
                    buckets[int(cid)].append(n)

            conn.execute("DELETE FROM communities")
            labels_out: dict[int, str] = {}
            for cid, cnodes in buckets.items():
                label, top_files, top_entities = _derive_community_label(
                    cnodes, in_degree
                )
                # de-duplicate labels across communities by suffixing (N)
                base = label
                n_taken = sum(1 for v in labels_out.values() if v == base
                              or v.startswith(base + " ("))
                final_label = base if n_taken == 0 else f"{base} ({n_taken + 1})"
                labels_out[cid] = final_label
                summary = _derive_community_summary(
                    top_files, top_entities, brain_db_path,
                )
                conn.execute(
                    "INSERT OR REPLACE INTO communities "
                    "(id, label, size, top_files, top_entities, summary) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (cid, final_label, len(cnodes),
                     json.dumps(top_files), json.dumps(top_entities),
                     summary),
                )

            conn.commit()
            result["community_labels"] = labels_out
        finally:
            conn.close()

        # Rewrite graphify's graph.html to replace "Community N" with our labels
        self._rewrite_visual_labels(labels_out)

        return result

    # Extra CSS injected into graphify's graph.html — tames the sidebar
    # scrollbars (they default to the OS chrome which looks terrible embedded
    # inside a dark-themed iframe) and tightens line-height.
    _VISUAL_CSS_INJECT = """
<style id="prism-visual-overrides">
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #4E79A7; }
  ::-webkit-scrollbar-corner { background: transparent; }
  * { scrollbar-color: #2a2a4e transparent; scrollbar-width: thin; }
  #communities-list, #neighbors-list, #search-results {
      scrollbar-width: thin !important;
  }
  .legend-item, #communities-list > div {
      line-height: 1.35 !important;
  }
</style>"""

    def _rewrite_visual_labels(self, labels: dict[int, str]) -> None:
        """Patch graphify's generated graph.html in-place:
          * replace "Community N" with humanized labels
          * inject scrollbar + line-height CSS so the embed looks polished

        Safe no-op if labels is empty or file is missing.
        """
        html_path = self._staging_dir / "graphify-out" / "graph.html"
        if not html_path.exists():
            return
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError:
            return

        changed = False

        # 1) Label rewrites — sort by longest cid first so "Community 10"
        #    doesn't get clobbered by the "Community 1" rule.
        for cid in sorted(labels.keys(), key=lambda x: -len(str(x))):
            lbl = labels[cid]
            if not lbl:
                continue
            patterns = [
                (f">Community {cid}<",
                 f">{lbl} <span style=\"opacity:.5;font-size:10px\">#{cid}</span><"),
                (f'"Community {cid}"', f'"{lbl} (#{cid})"'),
                (f"'Community {cid}'", f"'{lbl} (#{cid})'"),
                (f"Community {cid}</",
                 f"{lbl} <span style=\"opacity:.5;font-size:10px\">#{cid}</span></"),
            ]
            for needle, repl in patterns:
                if needle in html:
                    html = html.replace(needle, repl)
                    changed = True

        # 2) Inject our style block once, right before </head>.
        if 'id="prism-visual-overrides"' not in html:
            if "</head>" in html:
                html = html.replace(
                    "</head>", self._VISUAL_CSS_INJECT + "\n</head>", 1
                )
                changed = True

        if changed:
            try:
                html_path.write_text(html, encoding="utf-8")
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def clear_staging(self) -> None:
        if self._staging_dir.exists():
            try:
                shutil.rmtree(self._staging_dir)
            except OSError:
                pass
        self._staging_dir.mkdir(parents=True, exist_ok=True)


def _extract_line(source_location: str) -> Optional[int]:
    """Parse 'L42' or 'L42-L50' to int 42; return None on failure."""
    if not source_location:
        return None
    try:
        s = source_location.lstrip("L").split("-", 1)[0].lstrip("L")
        return int(s)
    except (ValueError, AttributeError):
        return None
