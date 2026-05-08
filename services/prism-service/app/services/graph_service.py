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

import hashlib
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Optional


# Map of common source-code suffixes that graphify knows how to parse.
# Ingested docs with these suffixes will be staged for the graph pass.
GRAPHIFY_CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".cs",
    ".csproj", ".sln", ".props", ".targets", ".razor", ".cshtml", ".xaml",
    ".go", ".rs", ".java", ".rb", ".php", ".cpp", ".c", ".h", ".hpp",
    ".md",  # graphify also picks up heading structure from markdown
}

_UNRESOLVED_CALL_MIN_FAN_IN = 50
_UNRESOLVED_CALL_MEDIAN_MULTIPLIER = 5
_UNRESOLVED_CALL_RELATIONS = {"calls"}
_PRISM_DETECT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs"}
_PRISM_FALLBACK_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".cs"}
_PRISM_CALL_SKIP = {
    "if", "for", "foreach", "while", "switch", "catch", "using", "lock",
    "return", "new", "typeof", "nameof", "sizeof", "default", "await",
    "function", "class", "interface", "constructor",
}
_CS_FRAMEWORK_CALLS = {
    "Build", "Configure", "ConfigureServices", "AddSingleton", "AddScoped",
    "AddTransient", "AddDbContext", "AddControllers", "AddEndpointsApiExplorer",
    "UseRouting", "UseAuthentication", "UseAuthorization", "UseSwagger",
    "UseHttpsRedirection", "MapGet", "MapPost", "MapPut", "MapDelete",
    "Select", "Where", "OrderBy", "ThenBy", "ToList", "ToArray",
    "ToString", "GetHashCode", "Equals", "GetAwaiter",
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
        # AC4: graphify emits a normalized label per node
        # ("brain.search" → "brain_search") for fuzzy entity lookup
        # when the user-provided name doesn't match the canonical
        # name exactly. Indexed below for cheap fallback resolution.
        ("norm_label",      "ALTER TABLE entities ADD COLUMN norm_label TEXT"),
    ):
        if col not in ent_cols:
            try:
                conn.execute(sql); conn.commit()
            except sqlite3.OperationalError:
                pass
    # Index norm_label for the call_chain fallback lookup. Skip if
    # column never landed (older sqlite returning OperationalError).
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ent_norm_label "
            "ON entities(norm_label) WHERE norm_label IS NOT NULL"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # relationships extensions
    rel_cols = {row[1] for row in conn.execute("PRAGMA table_info(relationships)").fetchall()}
    for col, sql in (
        ("confidence",        "ALTER TABLE relationships ADD COLUMN confidence TEXT"),
        ("confidence_score",  "ALTER TABLE relationships ADD COLUMN confidence_score REAL"),
        ("weight",            "ALTER TABLE relationships ADD COLUMN weight REAL"),
        ("source_location",   "ALTER TABLE relationships ADD COLUMN source_location TEXT"),
        # AC5: graphify emits source_file per edge — the FILE where
        # the call site lives (distinct from the source ENTITY's
        # defining file when the entity is defined elsewhere). Store
        # as call_site_file to disambiguate; surface in call_chain
        # results so users can jump straight to the call site.
        ("call_site_file",    "ALTER TABLE relationships ADD COLUMN call_site_file TEXT"),
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
    s = s.replace("_", " ").replace("-", " ").replace(".", " ")
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
    # Utility methods that dominate hub-selection in test-heavy
    # communities. Produce labels like "search"/"list"/"check" that
    # describe the method's verb, not what the community is about.
    "search", "list", "get", "set", "add", "remove", "delete", "create",
    "update", "check", "validate", "execute", "process", "handle",
    "load", "save", "read", "write", "open", "close", "build", "make",
    "find", "filter", "map", "reduce", "call", "send", "receive",
    "start", "stop", "reset", "clear", "parse", "format", "render",
    "test", "setup_method", "teardown_method", "fixture",
}


def _path_prefix_label(nodes: list[dict], threshold: float = 0.6) -> str:
    """Return a humanized directory prefix that covers ``threshold`` of
    the community's nodes, or empty string if no prefix is strong enough.

    Walks from the deepest shared directory outward so we pick the most
    specific prefix that still clears the threshold. For 130 nodes with
    100 of them under ``plugins/prism-devtools/tests/`` → returns
    ``"plugin tests"``; with only 40 under that prefix → returns empty
    and the caller falls through to the filename/hub heuristic.
    """
    paths: list[list[str]] = []
    for n in nodes:
        sf = (n.get("source_file") or "").replace("\\", "/").strip("/")
        if not sf:
            continue
        parts = sf.rsplit("/", 1)[0].split("/") if "/" in sf else []
        parts = [p for p in parts if p]
        if parts:
            paths.append(parts)
    if not paths:
        return ""
    n_paths = len(paths)
    min_cov = max(2, int(n_paths * threshold))
    dotnet_regions: _Counter = _Counter()
    for n in nodes:
        region = _dotnet_region_segments(n.get("source_file") or "")
        if region:
            dotnet_regions[tuple(region[:2])] += 1
    if dotnet_regions:
        region, cov = dotnet_regions.most_common(1)[0]
        if cov >= min_cov:
            return _humanize(" ".join(region))
    # Try depths from deepest to shallowest.
    max_depth = max(len(p) for p in paths)
    for depth in range(max_depth, 0, -1):
        counts: _Counter = _Counter()
        for p in paths:
            if len(p) >= depth:
                counts[tuple(p[:depth])] += 1
        prefix, cov = counts.most_common(1)[0]
        if cov >= min_cov:
            # Prefer the last 1–2 segments of the prefix — "plugins/
            # prism-devtools/tests" → "prism-devtools tests" reads better
            # than the full path. Drop common top-level containers.
            tail = [seg for seg in prefix[-2:]
                    if seg.lower() not in _PATH_PREFIX_DROP]
            if not tail:
                tail = list(prefix[-1:])
            return _humanize(" ".join(tail))
    return ""


# Top-level directory segments that add no information — drop them
# when shortening a path prefix to a label.
_PATH_PREFIX_DROP = {
    "src", "app", "lib", "pkg", "source", "sources",
    "plugins", "services", "packages",
    # Common C# / Unity wrapper folders. Keeping these as hierarchy
    # regions makes customer graphs read as "Assets > Scripts" instead
    # of the actual gameplay/API/domain area underneath.
    "assets", "scripts", "runtime",
}


_DOTNET_SOURCE_SUFFIXES = {
    ".cs", ".csproj", ".sln", ".props", ".targets",
    ".razor", ".cshtml", ".xaml",
}


_DOTNET_WRAPPER_DIRS = {
    "src", "source", "sources", "app", "apps", "lib", "libs",
    "packages", "projects", "assets", "scripts", "runtime",
}


_DOTNET_CATEGORY_DIRS = {
    "controllers", "endpoints", "handlers", "services", "repositories",
    "models", "entities", "dtos", "contracts", "interfaces",
    "infrastructure", "persistence", "migrations", "configurations",
    "components", "pages", "views", "viewmodels", "middleware",
    "validators", "mappings", "profiles", "jobs", "workers",
}


_DOTNET_FEATURE_WRAPPERS = {
    "features", "feature", "modules", "module", "areas", "area",
    "verticals", "usecases", "usecase",
}


_CS_PROJECT_LAYER_HINTS = {
    "api": "api",
    "web": "ui",
    "mvc": "ui",
    "presentation": "ui",
    "client": "ui",
    "maui": "ui",
    "wasm": "ui",
    "server": "api",
    "function": "api",
    "functions": "api",
    "application": "service",
    "services": "service",
    "worker": "service",
    "workers": "service",
    "background": "service",
    "infrastructure": "data",
    "persistence": "data",
    "data": "data",
    "domain": "domain",
    "core": "domain",
    "shared": "domain",
    "contracts": "domain",
    "abstractions": "domain",
    "tests": "test",
    "test": "test",
}


def _split_project_segment(segment: str) -> list[str]:
    """Split C# project folders like ``Acme.Store.Api`` into tokens."""
    spaced = _re.sub(
        r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])",
        " ",
        segment.replace(".", " "),
    )
    return [p.lower() for p in _WORD_RE.findall(spaced) if p]


def _dotnet_layer_for_segment(segment: str) -> str | None:
    for token in _split_project_segment(segment):
        layer = _CS_PROJECT_LAYER_HINTS.get(token)
        if layer:
            return layer
    return None


def _dotnet_region_segments(source_file: str) -> list[str]:
    """Prefer .NET project/layer regions over generic monorepo folders.

    Massive .NET monorepos often look like:
    ``src/Commerce/Shop.Api/Controllers/OrdersController.cs`` or
    ``src/Shop.Application/Features/Orders/CreateOrderHandler.cs``.
    The useful region is the project/layer segment (``Shop.Api``), then
    the local feature/category (``Controllers`` or ``Orders``), not
    wrapper folders such as ``src`` / ``Services`` / ``Features``.
    """
    sf = (source_file or "").replace("\\", "/").strip("/")
    if not sf:
        return []
    suffix = "." + sf.rsplit(".", 1)[-1].lower() if "." in sf else ""
    if suffix not in _DOTNET_SOURCE_SUFFIXES:
        return []

    raw_parts = [p for p in sf.split("/") if p]
    if not raw_parts:
        return []
    filename = raw_parts[-1] if "." in raw_parts[-1] else ""
    dir_parts = raw_parts[:-1] if filename else raw_parts
    file_stem = filename.rsplit(".", 1)[0] if filename else ""

    candidates = [
        (idx, part)
        for idx, part in enumerate(dir_parts)
        if _dotnet_layer_for_segment(part)
    ]
    preferred = [
        (idx, part) for idx, part in candidates
        if part.lower() not in _DOTNET_CATEGORY_DIRS
    ]
    if preferred:
        project_idx, project = preferred[-1]
    elif candidates:
        project_idx, project = candidates[-1]
    elif suffix in {".csproj", ".sln"} and file_stem:
        project_idx, project = len(dir_parts), file_stem
    else:
        non_wrapper = [
            (idx, part) for idx, part in enumerate(dir_parts)
            if part.lower() not in _DOTNET_WRAPPER_DIRS
        ]
        if not non_wrapper:
            return []
        project_idx, project = non_wrapper[0]

    regions = [project]
    for part in dir_parts[project_idx + 1:]:
        lower = part.lower()
        if lower in _DOTNET_WRAPPER_DIRS:
            continue
        if lower in _DOTNET_FEATURE_WRAPPERS:
            continue
        if part == project:
            continue
        regions.append(part)
        break
    return regions


def compute_node_hierarchy(
    source_file: str | None,
    fallback_community: int | None = None,
) -> dict:
    """Return {l0, l1, l2} parent keys for a leaf's hierarchical rollup.

    L0/L1 are semantic file or .NET project regions, not raw graphify
    communities. Large monorepos can produce thousands of tiny Leiden
    communities, which makes the overview unusable if each community is
    a top-level node. When community metadata is available, keep it at
    the deepest rollup level so drilldown can still separate dense
    topology without crushing the first screen.
    """
    sf = (source_file or "").replace("\\", "/").strip("/")
    parts = sf.split("/") if sf else []
    if parts and "." in parts[-1]:
        parts = parts[:-1]  # drop filename
    segs = _dotnet_region_segments(sf)
    if not segs:
        segs = [p for p in parts if p and p.lower() not in _PATH_PREFIX_DROP]
    if fallback_community is not None:
        if not segs:
            l1 = f"external/comm:{fallback_community}"
            return {"l0": "external", "l1": l1, "l2": l1}
        l0 = segs[0]
        l1 = "/".join(segs[:2]) if len(segs) >= 2 else l0
        l2_base = "/".join(segs[:3]) if len(segs) >= 3 else l1
        return {
            "l0": l0,
            "l1": l1,
            "l2": f"{l2_base}/comm:{fallback_community}",
        }
    if not segs:
        return {"l0": "external", "l1": "external", "l2": "external"}
    l0 = segs[0]
    l1 = "/".join(segs[:2]) if len(segs) >= 2 else l0
    l2 = "/".join(segs[:3]) if len(segs) >= 3 else l1
    return {"l0": l0, "l1": l1, "l2": l2}


def infer_architectural_layer(
    source_file: str | None,
    file_type: str | None = None,
    label: str | None = None,
) -> str:
    """Infer a coarse architectural layer for graph visualization color.

    This deliberately uses boring path/name heuristics instead of a model:
    it is deterministic, cheap, and good enough to make color encode
    meaning while graphify's communities encode topology.
    """
    haystack = " ".join(
        part for part in (source_file or "", file_type or "", label or "")
        if part
    ).replace("\\", "/").lower()
    tokens = set(_WORD_RE.findall(haystack))
    path = (source_file or "").replace("\\", "/")
    path_lower = path.lower()
    suffix = "." + path_lower.rsplit(".", 1)[-1] if "." in path_lower else ""
    path_parts = [p for p in path.replace("\\", "/").split("/") if p]
    project_token_list = [
        tok
        for part in path_parts
        for tok in _split_project_segment(part)
    ]
    project_tokens = set(project_token_list)

    def has_any(words: set[str]) -> bool:
        return bool(tokens.intersection(words) or project_tokens.intersection(words))

    if suffix in {".csproj", ".sln", ".props", ".targets"}:
        return "config"
    if any(name in path_lower for name in (
        "appsettings.", "launchsettings.", "directory.build.",
        "global.json", "nuget.config",
    )):
        return "config"
    if path_lower.rsplit("/", 1)[-1] in {"program.cs", "startup.cs"}:
        return "config"

    for layer in ("test", "api", "ui", "service", "data", "domain"):
        if any(_CS_PROJECT_LAYER_HINTS.get(token) == layer
               for token in project_token_list):
            return layer

    if has_any({"test", "tests", "spec", "specs", "fixture", "fixtures"}):
        return "test"
    if has_any({"doc", "docs", "documentation", "readme", "markdown"}):
        return "docs"
    if has_any({
        "config", "settings", "manifest", "dockerfile", "compose",
        "program", "startup", "host", "hosting", "properties",
    }):
        return "config"
    if has_any({"script", "scripts", "tool", "tools", "cli", "command", "commands"}):
        return "tooling"
    if has_any({
        "ui", "web", "frontend", "front", "page", "pages", "component",
        "components", "view", "views", "dashboard", "screen", "screens",
        "razor", "blazor", "viewmodel", "viewmodels", "xaml", "presenter",
        "presenters",
    }):
        return "ui"
    if has_any({
        "api", "route", "routes", "endpoint", "endpoints", "handler",
        "handlers", "controller", "controllers", "server", "mcp",
        "hub", "hubs", "grpc",
    }):
        return "api"
    if has_any({
        "service", "services", "engine", "engines", "worker", "workers",
        "mediator", "mediatr", "command", "commands", "query", "queries",
        "usecase", "usecases", "job", "jobs", "backgroundservice",
    }):
        return "service"
    if has_any({
        "db", "database", "data", "model", "models", "repo", "repos",
        "repository", "repositories", "schema", "migration", "storage",
        "dbcontext", "context", "contexts", "entityframework",
        "configuration", "configurations",
    }):
        return "data"
    if has_any({
        "domain", "core", "entity", "entities", "aggregate", "aggregates",
        "valueobject", "valueobjects", "enum", "enums", "contract",
        "contracts", "dto", "dtos",
    }):
        return "domain"
    return "other"


def display_label_for_graph_node(label: str | None, source_file: str | None = None) -> str:
    """Return a viewer-friendly node label without changing graph ids.

    Graphify emits C# member labels as ``.Method()``. That is faithful to
    the AST, but it looks broken in a customer-facing graph. Strip only this
    C#-specific leading dot; leave hidden/anonymous labels untouched.
    """
    text = str(label or "").strip()
    if not text:
        return text
    sf = (source_file or "").replace("\\", "/").lower()
    if sf.endswith(".cs") and text.startswith(".") and len(text) > 1:
        return text[1:]
    return text


def _prism_rel_source_file(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _prism_detect_code_files(root: Path, detected: list[Path]) -> list[Path]:
    """Return graphify-detected files plus PRISM-known source suffixes."""
    by_key: dict[str, Path] = {}
    for path in detected:
        if path.suffix.lower() in _PRISM_DETECT_SUFFIXES:
            by_key[str(path.resolve())] = path
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if "graphify-out" in path.parts:
            continue
        if path.suffix.lower() in _PRISM_DETECT_SUFFIXES:
            by_key[str(path.resolve())] = path
    return sorted(by_key.values(), key=lambda p: p.as_posix().lower())


def _prism_graph_id(source_file: str, label: str, kind: str, line: int) -> str:
    stem = _derive_norm_label(Path(source_file).stem) or "file"
    name = _derive_norm_label(label) or kind or "node"
    digest = hashlib.sha1(
        f"{source_file}|{label}|{kind}|{line}".encode("utf-8", errors="replace")
    ).hexdigest()[:10]
    return f"prism_{stem}_{name}_{digest}"


def _prism_node(source_file: str, label: str, kind: str, line: int) -> dict:
    return {
        "id": _prism_graph_id(source_file, label, kind, line),
        "label": label,
        "file_type": kind,
        "source_file": source_file,
        "source_location": f"L{max(1, line)}",
        "norm_label": _derive_norm_label(label),
    }


def _line_for_offset(content: str, offset: int) -> int:
    return content.count("\n", 0, max(0, offset)) + 1


def _find_matching_brace(content: str, open_idx: int) -> int:
    depth = 0
    for idx in range(open_idx, len(content)):
        ch = content[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth <= 0:
                return idx
    return len(content)


def _iter_call_names(body: str) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for match in _re.finditer(r"(?:\.|->)?\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", body):
        name = match.group(1)
        if name in _PRISM_CALL_SKIP or name in _CS_FRAMEWORK_CALLS:
            continue
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _extract_prism_fallback_graph(path: Path, root: Path) -> dict:
    """Small deterministic extractor for C#/TS/JS when graphify skips them."""
    suffix = path.suffix.lower()
    if suffix not in _PRISM_FALLBACK_SUFFIXES:
        return {"nodes": [], "edges": [], "raw_calls": []}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {"error": str(exc), "nodes": [], "edges": [], "raw_calls": []}

    source_file = _prism_rel_source_file(path, root)
    file_node = _prism_node(source_file, Path(source_file).name, "file", 1)
    nodes: list[dict] = [file_node]
    edges: list[dict] = []
    raw_calls: list[dict] = []
    node_by_key: dict[tuple[str, int], dict] = {(file_node["label"], 1): file_node}

    def add_node(label: str, kind: str, line: int) -> dict:
        key = (label, line)
        if key in node_by_key:
            return node_by_key[key]
        node = _prism_node(source_file, label, kind, line)
        node_by_key[key] = node
        nodes.append(node)
        return node

    def add_contains(parent: dict, child: dict) -> None:
        if parent["id"] == child["id"]:
            return
        edges.append({
            "source": parent["id"],
            "target": child["id"],
            "relation": "contains",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": source_file,
            "source_location": child.get("source_location", "L1"),
            "weight": 0.4,
        })

    if suffix == ".cs":
        type_matches = list(_re.finditer(
            r"\b(class|interface|struct|record)\s+([A-Za-z_][A-Za-z0-9_]*)",
            content,
        ))
        method_re = _re.compile(
            r"(?:^|[\r\n])\s*(?:"
            r"(?:public|private|protected|internal|static|async|virtual|override|sealed|partial|extern)\s+"
            r")+[\w<>\[\],.?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*(?:where[^{]+)?\{",
            _re.MULTILINE,
        )
    else:
        type_matches = list(_re.finditer(
            r"\b(class|interface)\s+([A-Za-z_][A-Za-z0-9_]*)",
            content,
        ))
        method_re = _re.compile(
            r"(?:^|[\r\n])\s*(?:export\s+)?(?:async\s+)?"
            r"(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*(?::[^{]+)?\{",
            _re.MULTILINE,
        )

    type_nodes: list[tuple[int, int, dict]] = []
    for idx, match in enumerate(type_matches):
        kind = match.group(1)
        name = match.group(2)
        line = _line_for_offset(content, match.start(2))
        node = add_node(name, kind, line)
        add_contains(file_node, node)
        end = type_matches[idx + 1].start() if idx + 1 < len(type_matches) else len(content)
        type_nodes.append((match.start(), end, node))

    def owner_for(offset: int) -> dict:
        for start, end, node in type_nodes:
            if start <= offset < end:
                return node
        return file_node

    for match in method_re.finditer(content):
        name = match.group(1)
        if name in _PRISM_CALL_SKIP:
            continue
        line = _line_for_offset(content, match.start(1))
        label = f".{name}()" if suffix == ".cs" else f"{name}()"
        node = add_node(label, "method", line)
        add_contains(owner_for(match.start()), node)
        open_idx = content.find("{", match.end() - 1)
        if open_idx < 0:
            continue
        body = content[open_idx + 1:_find_matching_brace(content, open_idx)]
        for callee in _iter_call_names(body):
            if callee == name:
                continue
            raw_calls.append({
                "caller_nid": node["id"],
                "callee": callee,
                "source_file": source_file,
                "source_location": f"L{line}",
            })

    return {"nodes": nodes, "edges": edges, "raw_calls": raw_calls}


def _needs_prism_fallback(path: Path, extracted: dict | None) -> bool:
    if path.suffix.lower() not in _PRISM_FALLBACK_SUFFIXES:
        return False
    if not extracted or "error" in extracted:
        return True
    return not any(
        node.get("file_type") not in {"rationale", "document", "markdown"}
        for node in extracted.get("nodes", [])
    )


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

    Cascade, most-specific first:
      1. Single dominant file (≥55%) → ``<file> · <hub>``.
      2. Directory-prefix covering ≥60% → ``<prefix> · <hub>``. Catches
         test-heavy communities where no one file dominates but they all
         live under ``.../tests/`` — previously these fell through to
         the hub picker and got named after a utility method.
      3. Two files covering ≥70% together → ``<f1> + <f2> · <hub>``.
      4. Hub entity.

    The hub entity is appended in cases 1–3 so sibling communities
    from the same dominant file/directory remain distinguishable.
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
    hub_h = _humanize(hub) if hub else ""

    first_frac = (top[0][1] / total) if top else 0.0
    two_frac = ((top[0][1] + top[1][1]) / total) if len(top) >= 2 else 0.0

    if top and first_frac >= 0.55:
        base = _humanize(top[0][0])
        label = f"{base} · {hub_h}" if hub_h else base
    else:
        prefix_label = _path_prefix_label(nodes, threshold=0.6)
        if prefix_label:
            label = f"{prefix_label} · {hub_h}" if hub_h else prefix_label
        elif two_frac >= 0.70:
            label = f"{_humanize(top[0][0])} + {_humanize(top[1][0])}"
            if hub_h:
                label = f"{label} · {hub_h}"
        elif hub_h:
            label = hub_h
        elif top:
            label = _humanize(top[0][0]) or "mixed"
        else:
            label = "misc"

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
        """Stage every code-suffix file from the Brain docs table.

        Multi-granular chunking emits N rows per source_file
        (``::win_N``, ``::__file__``, ``::__module__``, ``::EntityName``).
        Only the ``::__file__`` or ``::main`` rows hold full-file content;
        chunk rows hold fragments. Fix for resolve-io/.prism#34: the
        previous implementation iterated all rows and called ``stage_doc``
        on each, which overwrote the staged file on disk per-chunk —
        leaving graphify with only the last chunk's fragment per file
        and producing ~83.5% isolated nodes in the code graph.

        Returns the number of files staged. Safe to call repeatedly.
        """
        try:
            conn = sqlite3.connect(brain_db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
        except sqlite3.Error:
            return 0
        try:
            rows = conn.execute(
                "SELECT id, source_file, content FROM docs "
                "WHERE source_file IS NOT NULL "
                "ORDER BY source_file, "
                "  CASE "
                "    WHEN id LIKE '%::__file__' THEN 0 "
                "    WHEN id LIKE '%::main' THEN 1 "
                "    ELSE 2 "
                "  END"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()
        n = 0
        seen: set[str] = set()
        for row in rows:
            path = row["source_file"]
            if path in seen:
                continue
            doc_id = row["id"] or ""
            # Only file-level rows hold full source; skip chunk fragments.
            if not (doc_id.endswith("::__file__")
                    or doc_id.endswith("::main")):
                continue
            seen.add(path)
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
            # Issue #41: multi-granular chunking emits N rows per
            # source_file (::win_N, ::__file__, ::__module__, ::EntName).
            # Comparing chunk-rows vs disk-files (staged_files counts
            # files) made `stale: true` fire on every project where
            # chunks-per-file > 1 — typically every project. Count
            # DISTINCT source_files so the unit matches staged_files.
            allowed = {s.lstrip(".") for s in GRAPHIFY_CODE_SUFFIXES}
            out["code_docs"] = sum(1 for r in b.execute(
                "SELECT DISTINCT source_file FROM docs "
                "WHERE source_file IS NOT NULL"
            ) if (r["source_file"] or "").lower().rsplit(".", 1)[-1]
               in allowed)
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

        rebuild_out = self._run_graphify_update_with_safe_calls()
        if not rebuild_out.get("ok"):
            result["error"] = str(rebuild_out.get("error") or "graphify rebuild failed")[:500]
            return result
        result["ambiguous_call_phantoms"] = rebuild_out.get(
            "ambiguous_call_phantoms", 0,
        )
        result["fallback_extracted_files"] = rebuild_out.get(
            "fallback_extracted_files", 0,
        )

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

    def _run_graphify_update_with_safe_calls(self) -> dict:
        """Rebuild graphify output with PRISM's safer unresolved-call resolver.

        graphifyy 0.4.x resolves every cross-file raw call through a
        ``label -> single node id`` map. In large C# / TS monorepos that turns
        calls such as ``x.ToString()`` or ``expect.Be()`` into arbitrary
        first-party super-hubs. Keep graphify's parser/export pipeline, but
        replace that one resolver before clustering and writing graph.json.
        """
        watch_path = self._staging_dir.resolve()
        try:
            import graphify.extract as graphify_extract
            from graphify.analyze import (
                god_nodes,
                surprising_connections,
                suggest_questions,
            )
            from graphify.build import build_from_json
            from graphify.cache import load_cached, save_cached
            from graphify.cluster import cluster, score_all
            from graphify.detect import detect
            from graphify.export import to_html, to_json
            from graphify.report import generate
        except Exception as exc:
            return {"ok": False, "error": f"graphify import failed: {exc}"}

        try:
            detected = detect(watch_path)
            detected_code_files = [Path(f) for f in detected["files"]["code"]]
            code_files = _prism_detect_code_files(watch_path, detected_code_files)
            if not code_files:
                return {"ok": False, "error": "no code files found"}

            per_file: list[dict] = []
            per_file_paths: list[Path] = []
            fallback_files = 0
            for path in code_files:
                extracted: dict | None = None
                if path.name.endswith(".blade.php"):
                    extractor = getattr(graphify_extract, "extract_blade", None)
                else:
                    extractor = getattr(graphify_extract, "_DISPATCH", {}).get(
                        path.suffix
                    )
                if extractor is not None:
                    cached = load_cached(path, watch_path)
                    if cached is not None:
                        extracted = cached
                    else:
                        extracted = extractor(path)
                        if "error" not in extracted:
                            save_cached(path, extracted, watch_path)
                    per_file.append(extracted)
                    per_file_paths.append(path)

                if _needs_prism_fallback(path, extracted):
                    fallback = _extract_prism_fallback_graph(path, watch_path)
                    if fallback.get("nodes") or fallback.get("edges"):
                        per_file.append(fallback)
                        per_file_paths.append(path)
                        fallback_files += 1

            result = _merge_graphify_extractions_with_safe_calls(
                per_file, per_file_paths,
            )
            result = self._preserve_graphify_semantic_context(result)

            out = watch_path / "graphify-out"
            out.mkdir(exist_ok=True)
            graph = build_from_json(result)
            communities = cluster(graph)
            cohesion = score_all(graph, communities)
            labels = {cid: f"Community {cid}" for cid in communities}
            detection = {
                "files": {
                    "code": [str(f) for f in code_files],
                    "document": [],
                    "paper": [],
                    "image": [],
                },
                "total_files": len(code_files),
                "total_words": detected.get("total_words", 0),
            }
            questions = suggest_questions(graph, communities, labels)
            report = generate(
                graph,
                communities,
                cohesion,
                labels,
                god_nodes(graph),
                surprising_connections(graph, communities),
                detection,
                {"input": 0, "output": 0},
                str(watch_path),
                suggested_questions=questions,
            )
            (out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
            to_json(graph, communities, str(out / "graph.json"))
            to_html(
                graph,
                communities,
                str(out / "graph.html"),
                community_labels=labels or None,
            )
            stale_flag = out / "needs_update"
            if stale_flag.exists():
                stale_flag.unlink()
            return {
                "ok": True,
                "ambiguous_call_phantoms": result.get(
                    "ambiguous_call_phantoms", 0,
                ),
                "fallback_extracted_files": fallback_files,
            }
        except Exception as exc:
            return {"ok": False, "error": exc}

    def _preserve_graphify_semantic_context(self, result: dict) -> dict:
        out = self._staging_dir / "graphify-out"
        existing_graph = out / "graph.json"
        if not existing_graph.exists():
            return result
        try:
            existing = json.loads(existing_graph.read_text(encoding="utf-8"))
        except Exception:
            return result
        code_ids = {
            n["id"] for n in existing.get("nodes", [])
            if n.get("file_type") == "code"
        }
        sem_nodes = [
            n for n in existing.get("nodes", [])
            if n.get("file_type") not in ("code", "unresolved_call")
        ]
        sem_edges = []
        for edge in existing.get("links", existing.get("edges", [])):
            src = edge.get("source") or edge.get("_src")
            tgt = edge.get("target") or edge.get("_tgt")
            if src in code_ids and tgt in code_ids:
                continue
            sem_edges.append(edge)
        return {
            "nodes": result.get("nodes", []) + sem_nodes,
            "edges": result.get("edges", []) + sem_edges,
            "hyperedges": existing.get("hyperedges", []),
            "input_tokens": 0,
            "output_tokens": 0,
            "ambiguous_call_phantoms": result.get("ambiguous_call_phantoms", 0),
        }

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

        node_by_gid, pruned_call_targets, prune_summary = (
            _unresolved_call_pruning_plan(nodes, links)
        )
        filtered_links: list[dict] = []
        pruned_edges = 0
        for link in links:
            if _should_prune_unresolved_call_edge(
                link, node_by_gid, pruned_call_targets,
            ):
                pruned_edges += 1
                continue
            filtered_links.append(link)
        result["pruned_unresolved_call_edges"] = pruned_edges
        if prune_summary:
            result["pruned_unresolved_call_labels"] = prune_summary

        # Total degree (in + out) for community label derivation — captures
        # both "called-by" hubs and "calls-a-lot" orchestrators.
        in_degree: dict = {}
        for link in filtered_links:
            src = _graph_link_endpoint(link, "source", "_src")
            tgt = _graph_link_endpoint(link, "target", "_tgt")
            if src:
                in_degree[src] = in_degree.get(src, 0) + 1
            if tgt:
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        conn = sqlite3.connect(self._graph_db, timeout=5.0)
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
                # AC4: graphify emits norm_label for fuzzy lookup.
                # Fall back to a derived form so legacy graph.json
                # without that field still gets a useful default.
                norm_label = (
                    node.get("norm_label")
                    or _derive_norm_label(label)
                )
                # Derive "kind" from file_type or label for legacy queries
                kind = file_type or "node"
                cur = conn.execute(
                    "INSERT INTO entities "
                    "(name, kind, file, line, graphify_id, label, file_type, "
                    " community, source_location, norm_label) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(name, file) DO UPDATE SET "
                    "  kind=excluded.kind, "
                    "  graphify_id=excluded.graphify_id, "
                    "  label=excluded.label, "
                    "  file_type=excluded.file_type, "
                    "  community=excluded.community, "
                    "  source_location=excluded.source_location, "
                    "  norm_label=excluded.norm_label",
                    (label, kind, source_file, _extract_line(source_location),
                     gid, label, file_type, community, source_location,
                     norm_label),
                )
                # Retrieve id (RETURNING not universally available pre-3.35)
                row = conn.execute(
                    "SELECT id FROM entities WHERE graphify_id = ?", (gid,)
                ).fetchone()
                if row:
                    id_map[gid] = row["id"]
                    result["imported_entities"] += 1

            # Import links → relationships
            for link in filtered_links:
                src_gid = _graph_link_endpoint(link, "source", "_src")
                tgt_gid = _graph_link_endpoint(link, "target", "_tgt")
                src_id = id_map.get(src_gid)
                tgt_id = id_map.get(tgt_gid)
                if src_id is None or tgt_id is None:
                    continue
                relation = link.get("relation", "related")
                confidence = link.get("confidence", "EXTRACTED")
                confidence_score = float(link.get("confidence_score", 1.0))
                weight = float(link.get("weight", 1.0))
                source_location = link.get("source_location", "")
                # AC5: per-edge source_file is the FILE where the call
                # site lives (e.g. for an A→B call where A is defined
                # in src/a.py but the call site is in src/handler.py
                # because A was inlined or aliased). Distinct from the
                # source entity's defining file.
                call_site_file = link.get("source_file", "")
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO relationships "
                        "(source_id, target_id, relation, confidence, "
                        " confidence_score, weight, source_location, "
                        " call_site_file) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (src_id, tgt_id, relation, confidence,
                         confidence_score, weight, source_location,
                         call_site_file),
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

        # Merge enrichment edges from brain docs (INFERRED edges from
        # prism-enrich.py — MediatR/DI/MassTransit/sproc/TS-DI/HTTP)
        if brain_db_path:
            enrichment_added = self._apply_enrichment_edges(
                brain_db_path, conn_path=str(self._graph_db),
            )
            result["enrichment_edges"] = enrichment_added

        return result

    def _apply_enrichment_edges(self, brain_db_path: str, conn_path: str) -> int:
        """Read enrichment docs from brain.db and insert INFERRED relationships
        into graph.db. Idempotent — uses INSERT OR IGNORE.

        Entities in enrichment docs use bare class names (e.g. GetWorkflowsQuery).
        Graph entities use filenames (e.g. GetWorkflowsQuery.cs). Tries exact
        match first, then strips the extension as fallback.

        Depends on brain commit 6097eee (docs.content stores raw source) so
        the markdown survives storage. Older brain.db rows written before
        that commit have tokenized content and won't parse — re-run
        prism-enrich.py to overwrite them.
        """
        import sqlite3 as _sq
        import re as _re2

        edge_re = _re2.compile(r'\*\*(.+?)\*\*\s*->\s*\*\*(.+?)\*\*')
        kind_re = _re2.compile(r'^Pattern:\s*(\S+)', _re2.MULTILINE)
        # Strip brain context prefix (added by contextual chunking) before parsing
        content_start_re = _re2.compile(r'(#\s*Inferred relationships)', _re2.MULTILINE)

        # Build name → entity_id index from graph.db (both exact and stem-based)
        try:
            gconn = _sq.connect(conn_path)
            gconn.row_factory = _sq.Row
            name_to_id: dict[str, int] = {}
            for r in gconn.execute("SELECT id, name FROM entities"):
                raw = r["name"]
                name_to_id[raw] = r["id"]
                # Also index by stem (strip extension) so class names resolve
                # against filename entities: "GetWorkflowsQuery.cs" → "GetWorkflowsQuery"
                stem = raw.rsplit(".", 1)[0] if "." in raw else raw
                if stem not in name_to_id:
                    name_to_id[stem] = r["id"]
        except _sq.Error:
            return 0

        # Read enrichment docs from brain.db
        try:
            bconn = _sq.connect(brain_db_path)
            bconn.row_factory = _sq.Row
            rows = bconn.execute(
                "SELECT source_file, content FROM docs "
                "WHERE source_file LIKE 'enrichment/%'"
            ).fetchall()
            bconn.close()
        except _sq.Error:
            gconn.close()
            return 0

        inserted = 0
        try:
            for row in rows:
                content = row["content"] or ""
                # Strip brain context prefix — content we care about starts at the heading
                m0 = content_start_re.search(content)
                if m0:
                    content = content[m0.start():]
                kind_match = kind_re.search(content)
                relation = kind_match.group(1) if kind_match else "inferred"
                for m in edge_re.finditer(content):
                    src_name, tgt_name = m.group(1).strip(), m.group(2).strip()
                    src_id = name_to_id.get(src_name)
                    tgt_id = name_to_id.get(tgt_name)
                    if src_id is None or tgt_id is None:
                        continue
                    try:
                        gconn.execute(
                            "INSERT OR IGNORE INTO relationships "
                            "(source_id, target_id, relation, confidence, "
                            " confidence_score, weight) "
                            "VALUES (?, ?, ?, 'INFERRED', 0.8, 1.0)",
                            (src_id, tgt_id, relation),
                        )
                        inserted += 1
                    except _sq.IntegrityError:
                        pass
            gconn.commit()
        finally:
            gconn.close()
        return inserted

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


def _derive_norm_label(label: str) -> str:
    """Local fallback when graphify doesn't emit norm_label.

    Strips call/dot syntax and lowercases so 'Brain.search()' and
    'brain.search' both resolve to 'brain_search'. Mirrors graphify's
    own normalization so the index column remains useful even on
    pre-norm_label graph.json output.
    """
    if not label:
        return ""
    import re as _re
    s = label.strip().rstrip("()")
    s = _re.sub(r"[.\s]+", "_", s)
    s = _re.sub(r"[^A-Za-z0-9_]", "", s)
    return s.lower()


def _graphify_label_key(label: object) -> str:
    return str(label or "").strip("()").lstrip(".").lower()


def _unresolved_call_id(raw_call: dict, callee: str) -> str:
    line = str(raw_call.get("source_location") or "")
    source_file = str(raw_call.get("source_file") or "")
    digest = hashlib.sha1(
        f"{raw_call.get('caller_nid')}|{callee}|{source_file}|{line}".encode(
            "utf-8",
            errors="replace",
        )
    ).hexdigest()[:12]
    return f"unresolved_call_{_derive_norm_label(callee) or 'call'}_{digest}"


def _display_unresolved_callee(callee: str) -> str:
    callee = str(callee or "").strip()
    if not callee:
        return "unresolved call"
    return callee if callee.endswith(")") else f"{callee}()"


def _append_safe_cross_file_call_edges(
    nodes: list[dict],
    edges: list[dict],
    per_file: list[dict],
) -> int:
    from collections import defaultdict

    node_by_id = {node.get("id"): node for node in nodes if node.get("id")}
    label_to_nodes: dict[str, list[dict]] = defaultdict(list)
    for node in nodes:
        key = _graphify_label_key(node.get("label"))
        if key:
            label_to_nodes[key].append(node)

    existing_pairs = {
        (edge.get("source"), edge.get("target"))
        for edge in edges
        if edge.get("source") and edge.get("target")
    }
    unresolved_count = 0
    unresolved_ids: set[str] = set()

    for result in per_file:
        for raw_call in result.get("raw_calls", []):
            callee = str(raw_call.get("callee") or "")
            caller = raw_call.get("caller_nid")
            if not callee or not caller:
                continue
            candidates = [
                node for node in label_to_nodes.get(callee.lower(), [])
                if node.get("id") != caller
            ]
            if not candidates:
                continue

            call_site_file = _path_key(raw_call.get("source_file"))
            same_file = [
                node for node in candidates
                if call_site_file
                and _source_file_key(node) == call_site_file
            ]
            target = same_file[0] if len(same_file) == 1 else None
            if target is None and len(candidates) == 1:
                target = candidates[0]

            if target is not None:
                target_id = target.get("id")
                pair = (caller, target_id)
                if target_id and pair not in existing_pairs:
                    existing_pairs.add(pair)
                    edges.append({
                        "source": caller,
                        "target": target_id,
                        "relation": "calls",
                        "confidence": "INFERRED",
                        "confidence_score": 0.8,
                        "source_file": raw_call.get("source_file", ""),
                        "source_location": raw_call.get("source_location"),
                        "weight": 1.0,
                    })
                continue

            unresolved_id = _unresolved_call_id(raw_call, callee)
            if unresolved_id not in unresolved_ids and unresolved_id not in node_by_id:
                unresolved_ids.add(unresolved_id)
                node_by_id[unresolved_id] = {
                    "id": unresolved_id,
                    "label": _display_unresolved_callee(callee),
                    "file_type": "unresolved_call",
                    "source_file": raw_call.get("source_file", ""),
                    "source_location": raw_call.get("source_location") or "",
                    "norm_label": _derive_norm_label(callee),
                }
                nodes.append(node_by_id[unresolved_id])
                unresolved_count += 1

            pair = (caller, unresolved_id)
            if pair not in existing_pairs:
                existing_pairs.add(pair)
                edges.append({
                    "source": caller,
                    "target": unresolved_id,
                    "relation": "calls",
                    "confidence": "AMBIGUOUS",
                    "confidence_score": 0.35,
                    "source_file": raw_call.get("source_file", ""),
                    "source_location": raw_call.get("source_location"),
                    "weight": 0.2,
                })

    return unresolved_count


def _merge_graphify_extractions_with_safe_calls(
    per_file: list[dict],
    paths: list[Path],
) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    for result in per_file:
        nodes.extend(result.get("nodes", []))
        edges.extend(result.get("edges", []))

    py_paths = [path for path in paths if path.suffix == ".py"]
    if py_paths:
        try:
            from graphify.extract import _resolve_cross_file_imports

            py_results = [
                result for result, path in zip(per_file, paths)
                if path.suffix == ".py"
            ]
            edges.extend(_resolve_cross_file_imports(py_results, py_paths))
        except Exception:
            pass

    ambiguous_count = _append_safe_cross_file_call_edges(
        nodes, edges, per_file,
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "hyperedges": [],
        "input_tokens": 0,
        "output_tokens": 0,
        "ambiguous_call_phantoms": ambiguous_count,
    }


def _graph_link_endpoint(link: dict, primary: str, fallback: str) -> object:
    value = link.get(primary)
    if value is not None:
        return value
    return link.get(fallback)


def _graph_link_relation(link: dict) -> str:
    return str(link.get("relation") or "related").lower()


def _source_file_key(node: dict | None) -> str:
    if not node:
        return ""
    return str(node.get("source_file") or "").replace("\\", "/").lower()


def _path_key(path: object) -> str:
    return str(path or "").replace("\\", "/").lower()


def _lower_median(values: list[int]) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    return sorted_values[(len(sorted_values) - 1) // 2]


def _unresolved_call_pruning_plan(
    nodes: list[dict],
    links: list[dict],
) -> tuple[dict[object, dict], set[object], list[dict]]:
    """Detect graphify's collapsed C# unresolved-call hubs.

    Some unresolved receiver calls are emitted as dot-prefixed method labels
    (for example `.ToString()`), then routed to one arbitrary first-party
    method node with that label. The node is real, so deleting it would remove
    valid code. Prune only the suspicious cross-file incoming call edges.
    """
    from collections import Counter, defaultdict

    node_by_id: dict[object, dict] = {}
    dot_label_nodes: dict[str, list[object]] = defaultdict(list)
    for node in nodes:
        gid = node.get("id")
        if gid is None:
            continue
        node_by_id[gid] = node
        label = str(node.get("label") or "")
        if label.startswith("."):
            dot_label_nodes[label].append(gid)

    incoming_by_label: dict[str, Counter] = defaultdict(Counter)
    for link in links:
        if _graph_link_relation(link) not in _UNRESOLVED_CALL_RELATIONS:
            continue
        tgt = _graph_link_endpoint(link, "target", "_tgt")
        target_node = node_by_id.get(tgt)
        label = str((target_node or {}).get("label") or "")
        if label.startswith("."):
            incoming_by_label[label][tgt] += 1

    pruned_targets: set[object] = set()
    summary: list[dict] = []
    for label, target_counts in incoming_by_label.items():
        group_node_ids = dot_label_nodes.get(label, [])
        if len(group_node_ids) < 2:
            continue
        counts = [int(target_counts.get(gid, 0)) for gid in group_node_ids]
        total = sum(counts)
        if total <= _UNRESOLVED_CALL_MIN_FAN_IN:
            continue
        median = _lower_median(counts)
        threshold = max(
            _UNRESOLVED_CALL_MIN_FAN_IN,
            _UNRESOLVED_CALL_MEDIAN_MULTIPLIER * max(1, median),
        )
        offenders = [
            gid for gid, count in target_counts.items()
            if count > threshold
        ]
        if not offenders:
            continue
        pruned_targets.update(offenders)
        summary.append({
            "label": label,
            "total_incoming": total,
            "median_incoming": median,
            "targets": [
                {
                    "id": str(gid),
                    "incoming": int(target_counts.get(gid, 0)),
                    "source_file": str((node_by_id.get(gid) or {}).get("source_file") or ""),
                }
                for gid in offenders[:5]
            ],
        })

    return node_by_id, pruned_targets, summary


def _should_prune_unresolved_call_edge(
    link: dict,
    node_by_id: dict[object, dict],
    pruned_targets: set[object],
) -> bool:
    if _graph_link_relation(link) not in _UNRESOLVED_CALL_RELATIONS:
        return False
    tgt = _graph_link_endpoint(link, "target", "_tgt")
    if tgt not in pruned_targets:
        return False
    src = _graph_link_endpoint(link, "source", "_src")
    source_file = _path_key(link.get("source_file")) or _source_file_key(
        node_by_id.get(src)
    )
    target_file = _source_file_key(node_by_id.get(tgt))
    if source_file and target_file and source_file == target_file:
        return False
    return True
