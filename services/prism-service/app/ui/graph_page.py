"""Graph page — visualise graphify-populated entities and relationships."""

from __future__ import annotations

import re
import sqlite3
from collections import Counter

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app, ui

from app.project_context import get_project
from app.ui.components.nav import create_nav, page_container


_SAFE_PROJECT_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
# Only graph.json is served now — the WebGL viewer is the only frontend.
# The legacy graphify graph.html / GRAPH_REPORT.md paths were dropped
# because they capped at ~11K nodes and the Sigma viewer covers every
# size graphify can produce.
_ALLOWED_VISUAL_FILES = {"graph.json"}


_SIGMA_VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>PRISM Graph Viewer</title>
<style>
  body { margin: 0; font-family: system-ui, sans-serif; background: #0f0f1a; color: #e5e7eb; }
  #graph { position: absolute; inset: 0; }
  #status { position: absolute; top: 8px; left: 8px; padding: 6px 10px;
            background: rgba(15,15,26,0.8); border: 1px solid #2a2a4e;
            border-radius: 6px; font-size: 12px; z-index: 10; max-width: 60ch; }
  #legend { position: absolute; bottom: 8px; left: 8px; padding: 6px 10px;
            background: rgba(15,15,26,0.8); border: 1px solid #2a2a4e;
            border-radius: 6px; font-size: 11px; z-index: 10; }
</style>
</head>
<body>
<div id="status">Loading graph...</div>
<div id="graph"></div>
<div id="legend">Scroll to zoom · drag to pan · click a node for details</div>
<script type="module">
  // ESM via esm.sh — avoids the UMD-global naming mess across
  // graphology's package family. Each import has an explicit name
  // (Graph, forceAtlas2, Sigma) instead of reaching into a
  // graphologyLibrary global that different packages register
  // inconsistently.
  import Graph from "https://esm.sh/graphology@0.25.4";
  import forceAtlas2 from "https://esm.sh/graphology-layout-forceatlas2@0.10.1";
  import Sigma from "https://esm.sh/sigma@3.0.0";
  const PROJECT_ID = "__PROJECT_ID__";
  const statusEl = document.getElementById("status");
  const COMMUNITY_COLORS = [
    "#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F","#EDC948",
    "#B07AA1","#FF9DA7","#9C755F","#BAB0AC","#86BCB6","#D37295",
  ];
  function colorFor(community) {
    if (community === undefined || community === null) return "#6b7280";
    const idx = Math.abs(Number(community) || 0) % COMMUNITY_COLORS.length;
    return COMMUNITY_COLORS[idx];
  }
  // Seed positions on a per-community ring so ForceAtlas2 starts with
  // cluster structure rather than pure noise — otherwise 35k random
  // nodes make FA2 converge to a fuzzy blob instead of a readable map.
  function seedPosition(community, idx) {
    const c = community === undefined || community === null ? 0 : Number(community) || 0;
    const clusterR = 50 + (Math.abs(c) % 12) * 8;
    const theta = ((Math.abs(c) * 2.39996) + idx * 0.0001) % (Math.PI * 2);
    const jitter = 3;
    return {
      x: clusterR * Math.cos(theta) + (Math.random() - 0.5) * jitter,
      y: clusterR * Math.sin(theta) + (Math.random() - 0.5) * jitter,
    };
  }
  fetch(`/graphify-visual/${PROJECT_ID}/graph.json`)
    .then(r => { if (!r.ok) throw new Error("graph.json " + r.status); return r.json(); })
    .then(data => {
      const g = new Graph();
      const nodes = data.nodes || [];
      const edges = data.links || data.edges || [];
      statusEl.textContent = `Loading ${nodes.length.toLocaleString()} nodes, `
        + `${edges.length.toLocaleString()} edges...`;
      let nIdx = 0;
      for (const n of nodes) {
        if (g.hasNode(n.id)) continue;
        const pos = seedPosition(n.community, nIdx++);
        g.addNode(n.id, {
          label: n.label || n.id,
          size: Math.max(2, Math.log(1 + (n.degree || 1)) * 2),
          color: colorFor(n.community),
          community: n.community ?? null,
          x: pos.x, y: pos.y,
        });
      }
      for (const e of edges) {
        const s = e.source, t = e.target;
        if (!g.hasNode(s) || !g.hasNode(t) || s === t) continue;
        // size 0.8 + brighter color so edges are visible against the dark
        // background at FA2-spaced clusters. Dropped hideEdgesOnMove:
        // letting edges paint during pan is the whole point of "connect
        // the elements"; losing them during interaction defeats the map.
        try { g.addEdge(s, t, {size: 0.8, color: "#8a8ac4"}); } catch (_) {}
      }
      // ForceAtlas2: iteration count scales down for huge graphs so the
      // layout returns in a few seconds. Barnes-Hut + LinLog modes help
      // community separation and keep it tractable at 35k+ nodes.
      statusEl.textContent = `Laying out ${nodes.length.toLocaleString()} nodes `
        + `(ForceAtlas2)...`;
      const settings = forceAtlas2.inferSettings(g);
      settings.barnesHutOptimize = g.order > 2000;
      settings.barnesHutTheta = 0.8;
      settings.linLogMode = true;
      settings.strongGravityMode = true;
      settings.gravity = 0.8;
      settings.scalingRatio = 10;
      settings.adjustSizes = true;
      const iters = g.order > 20000 ? 120 : g.order > 5000 ? 250 : 400;
      const t0 = performance.now();
      // Yield to the browser once so the "Laying out..." status can paint
      // before the synchronous FA2 pass blocks the main thread.
      setTimeout(() => {
        forceAtlas2.assign(g, { iterations: iters, settings });
        const dt = ((performance.now() - t0) / 1000).toFixed(1);
        const renderer = new Sigma(g, document.getElementById("graph"), {
          labelDensity: 0.15, labelGridCellSize: 80, minCameraRatio: 0.05,
          maxCameraRatio: 10, defaultNodeColor: "#6b7280",
          defaultEdgeColor: "#8a8ac4",
          renderEdgeLabels: false,
        });
        statusEl.textContent = `${nodes.length.toLocaleString()} nodes · `
          + `${edges.length.toLocaleString()} edges · FA2 ${iters}it in ${dt}s`;
        renderer.on("clickNode", ({ node }) => {
          const attrs = g.getNodeAttributes(node);
          statusEl.textContent = `${attrs.label} `
            + `(community ${attrs.community ?? "—"}, `
            + `degree ${g.degree(node)})`;
        });
      }, 50);
    })
    .catch(err => {
      statusEl.textContent = "Error loading graph: " + err.message;
    });
</script>
</body>
</html>"""


@app.get("/graphify-visual/{project_id}/{filename}")
def _graphify_visual(project_id: str, filename: str):
    """Serve graph.json for the WebGL viewer. Project slug strictly
    validated to prevent path traversal."""
    if not _SAFE_PROJECT_RE.match(project_id or ""):
        raise HTTPException(status_code=400, detail="invalid project id")
    if filename not in _ALLOWED_VISUAL_FILES:
        raise HTTPException(status_code=404, detail="not found")
    ctx = get_project(project_id)
    path = ctx._data_dir / "graphify-src" / "graphify-out" / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="graph.json not generated yet")
    return FileResponse(str(path), media_type="application/json")


@app.get("/graph/viewer/{project_id}")
def _graph_viewer(project_id: str):
    """Sigma.js WebGL viewer for a project's graph.json.

    Phase 2 of #16 — handles 100K+ nodes by delegating rendering to
    the user's browser GPU instead of asking graphify to emit a
    possibly-rejected HTML blob. Container ships no graphics libs;
    all rendering happens client-side.
    """
    from fastapi.responses import HTMLResponse
    if not _SAFE_PROJECT_RE.match(project_id or ""):
        raise HTTPException(status_code=400, detail="invalid project id")
    html = _SIGMA_VIEWER_HTML.replace("__PROJECT_ID__", project_id)
    return HTMLResponse(content=html)


def _project_id() -> str:
    return app.storage.user.get("project", "default")


def _graph_conn() -> sqlite3.Connection:
    ctx = get_project(_project_id())
    conn = sqlite3.connect(str(ctx._data_dir / "graph.db"))
    conn.row_factory = sqlite3.Row
    return conn


def _summary() -> dict:
    conn = _graph_conn()
    try:
        entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        rels = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
        communities = 0
        by_kind: Counter = Counter()
        by_community: list[tuple[int, int, str, str]] = []  # (id, size, label, summary)
        has_graphify = False
        try:
            communities = conn.execute(
                "SELECT COUNT(DISTINCT community) FROM entities "
                "WHERE community IS NOT NULL"
            ).fetchone()[0]
            for r in conn.execute(
                "SELECT kind, COUNT(*) AS n FROM entities GROUP BY kind"
            ):
                by_kind[r["kind"] or "unknown"] = r["n"]
            # Join community labels + summaries where available
            try:
                rows = conn.execute(
                    "SELECT e.community AS cid, COUNT(*) AS n, "
                    "c.label AS label, c.summary AS summary "
                    "FROM entities e "
                    "LEFT JOIN communities c ON c.id = e.community "
                    "WHERE e.community IS NOT NULL "
                    "GROUP BY e.community "
                    "ORDER BY n DESC LIMIT 16"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = conn.execute(
                    "SELECT community AS cid, COUNT(*) AS n, "
                    "NULL AS label, NULL AS summary "
                    "FROM entities WHERE community IS NOT NULL "
                    "GROUP BY community ORDER BY n DESC LIMIT 16"
                ).fetchall()
            for r in rows:
                label = r["label"] or f"community {r['cid']}"
                summary = ""
                try:
                    summary = r["summary"] or ""
                except (IndexError, KeyError):
                    pass
                by_community.append(
                    (int(r["cid"]), int(r["n"]), label, summary)
                )
            has_graphify = bool(conn.execute(
                "SELECT 1 FROM entities WHERE graphify_id IS NOT NULL LIMIT 1"
            ).fetchone())
        except sqlite3.OperationalError:
            pass
    finally:
        conn.close()
    return {
        "entities": entities, "relationships": rels,
        "communities": communities, "by_kind": dict(by_kind),
        "by_community": by_community, "has_graphify": has_graphify,
    }


def _entities_rows(community: int | None, kind: str | None, limit: int = 200) -> list[dict]:
    conn = _graph_conn()
    try:
        where = []
        args: list = []
        if community is not None:
            where.append("community = ?"); args.append(community)
        if kind:
            where.append("kind = ?"); args.append(kind)
        sql = "SELECT name, kind, community, file, source_location, file_type FROM entities"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY community, name LIMIT ?"
        args.append(limit)
        try:
            rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
        except sqlite3.OperationalError:
            rows = [dict(r) for r in conn.execute(
                "SELECT name, kind, file FROM entities LIMIT ?", (limit,)
            ).fetchall()]
    finally:
        conn.close()
    return rows


def _relationships_rows(min_confidence: float = 0.0, limit: int = 200) -> list[dict]:
    conn = _graph_conn()
    try:
        try:
            rows = [dict(r) for r in conn.execute(
                "SELECT r.relation, r.confidence, r.confidence_score, r.weight, "
                "       e1.name AS source, e2.name AS target "
                "FROM relationships r "
                "JOIN entities e1 ON r.source_id = e1.id "
                "JOIN entities e2 ON r.target_id = e2.id "
                "WHERE COALESCE(r.confidence_score, 1.0) >= ? "
                "ORDER BY r.confidence_score DESC, e1.name "
                "LIMIT ?", (min_confidence, limit)
            ).fetchall()]
        except sqlite3.OperationalError:
            rows = [dict(r) for r in conn.execute(
                "SELECT r.relation, e1.name AS source, e2.name AS target "
                "FROM relationships r "
                "JOIN entities e1 ON r.source_id = e1.id "
                "JOIN entities e2 ON r.target_id = e2.id LIMIT ?", (limit,)
            ).fetchall()]
    finally:
        conn.close()
    return rows


@ui.page("/graph")
def graph_page():
    create_nav()

    with page_container():
        ui.label("Graph — Code Knowledge Graph").classes(
            "text-2xl font-semibold text-gray-900"
        )
        ui.label(
            "Populated by graphify (tree-sitter AST pass + Leiden community "
            "detection). Trigger a rebuild with the button below after "
            "bulk-ingesting source files via brain_index_doc."
        ).classes("text-sm text-gray-600")

        summary = _summary()

        # WebGL viewer (Sigma.js) — single visual path. graph.json must
        # exist before the iframe has anything to render; otherwise show
        # an empty-state prompt pointing at the Rebuild button below.
        ctx = get_project(_project_id())
        json_path = ctx._data_dir / "graphify-src" / "graphify-out" / "graph.json"
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-3"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("Interactive visual").classes(
                    "text-sm font-medium text-gray-700"
                )
                if json_path.exists():
                    ui.link(
                        "Open full-screen viewer",
                        f"/graph/viewer/{_project_id()}",
                        new_tab=True,
                    ).classes("text-sm text-indigo-600 hover:underline")
            if json_path.exists():
                ui.element("iframe").props(
                    f'src="/graph/viewer/{_project_id()}"'
                ).style(
                    "width: 100%; height: 600px; border: 0; "
                    "border-radius: 6px; background: #0f0f1a; display: block;"
                )
            else:
                with ui.column().classes(
                    "w-full h-40 items-center justify-center "
                    "bg-gray-50 rounded-lg border border-dashed border-gray-300"
                ):
                    ui.icon("hub", size="xl").classes("text-gray-300")
                    ui.label(
                        "No graph.json yet — click Rebuild below."
                    ).classes("text-sm text-gray-400 mt-1")

        # --- Summary stats ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            with ui.row().classes("gap-8 flex-wrap items-start"):
                for label, val in [
                    ("Entities", summary["entities"]),
                    ("Relationships", summary["relationships"]),
                    ("Communities", summary["communities"]),
                ]:
                    with ui.column().classes("items-center gap-1"):
                        ui.label(str(val)).classes("text-3xl font-bold text-gray-900")
                        ui.label(label).classes(
                            "text-xs text-gray-500 uppercase tracking-wide"
                        )
                with ui.column().classes("items-center gap-1"):
                    if summary["has_graphify"]:
                        ui.html('<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                                'bg-green-100 text-green-800">graphify active</span>')
                    else:
                        ui.html('<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                                'bg-yellow-100 text-yellow-800">tree-sitter legacy</span>')
                    ui.label("Source").classes(
                        "text-xs text-gray-500 uppercase tracking-wide"
                    )

            ui.separator().classes("my-4")

            async def do_rebuild():
                rebuild_btn.disable()
                ui.notify("Running graphify update…", type="info")
                try:
                    ctx = get_project(_project_id())
                    r = ctx.graph_svc.rebuild(
                        brain_db_path=str(ctx._data_dir / "brain.db")
                    )
                    if r.get("error"):
                        ui.notify(f"Rebuild: {r['error'][:200]}", type="warning")
                    else:
                        ui.notify(
                            f"Rebuilt: {r.get('nodes',0)} nodes, "
                            f"{r.get('edges',0)} edges, "
                            f"{r.get('communities',0)} communities",
                            type="positive",
                        )
                    ui.navigate.reload()
                except Exception as exc:
                    ui.notify(f"Rebuild failed: {exc}", type="negative")
                finally:
                    rebuild_btn.enable()

            rebuild_btn = ui.button("Rebuild graph (graphify)", icon="hub").props(
                "color=primary no-caps"
            )
            rebuild_btn.on("click", do_rebuild)

        # --- Kind distribution ---
        if summary["by_kind"]:
            with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
                ui.label("Nodes by kind").classes(
                    "text-sm font-medium text-gray-700 mb-2"
                )
                with ui.row().classes("gap-2 flex-wrap"):
                    for k, n in sorted(summary["by_kind"].items(),
                                        key=lambda x: -x[1]):
                        ui.html(
                            f'<span class="text-xs font-medium px-2.5 py-1 rounded-full '
                            f'bg-indigo-50 text-indigo-700">{k}: {n}</span>'
                        )

        # --- Community distribution ---
        if summary["by_community"]:
            with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
                ui.label("Communities (labeled by dominant content)").classes(
                    "text-sm font-medium text-gray-700 mb-2"
                )
                with ui.row().classes("gap-2 flex-wrap"):
                    for cid, n, label, summ in summary["by_community"]:
                        # Hover shows the prose summary; escape quotes so it
                        # stays inside the HTML title attribute cleanly.
                        title_text = (
                            summ.replace('"', "&quot;") if summ else
                            f"community id: {cid}"
                        )
                        ui.html(
                            f'<span class="text-xs font-medium px-2.5 py-1 '
                            f'rounded-full bg-emerald-50 text-emerald-700" '
                            f'title="{title_text}">{label} — {n}</span>'
                        )

        # --- Entities table ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Entities").classes(
                "text-lg font-semibold text-gray-900 mb-2"
            )
            ent_rows = _entities_rows(community=None, kind=None, limit=300)
            # Decorate rows with community label
            labels_map: dict[int, str] = {}
            conn = _graph_conn()
            try:
                try:
                    for r in conn.execute("SELECT id, label FROM communities"):
                        labels_map[int(r["id"])] = r["label"] or ""
                except sqlite3.OperationalError:
                    pass
            finally:
                conn.close()
            for row in ent_rows:
                cid = row.get("community")
                if cid is not None and cid in labels_map:
                    row["community_label"] = f"{labels_map[cid]} (#{cid})"
                elif cid is not None:
                    row["community_label"] = f"community {cid}"
                else:
                    row["community_label"] = ""

            ent_cols = [
                {"name": "name", "label": "Name", "field": "name", "sortable": True},
                {"name": "kind", "label": "Kind", "field": "kind", "sortable": True,
                 "style": "width: 100px"},
                {"name": "community_label", "label": "Cluster",
                 "field": "community_label", "sortable": True,
                 "style": "width: 200px"},
                {"name": "file_type", "label": "Type", "field": "file_type",
                 "sortable": True, "style": "width: 90px"},
                {"name": "source_location", "label": "Loc", "field": "source_location",
                 "style": "width: 90px"},
                {"name": "file", "label": "File", "field": "file"},
            ]
            if ent_rows:
                t = ui.table(columns=ent_cols, rows=ent_rows, row_key="name",
                             pagination={"rowsPerPage": 15}).classes("w-full")
                t.props("flat dense separator=horizontal")
            else:
                ui.label("No entities yet — call graph_rebuild or ingest source "
                         "files first.").classes("text-sm text-gray-400")

        # --- Relationships table ---
        with ui.card().classes("w-full bg-white shadow-sm rounded-lg p-5"):
            ui.label("Relationships").classes(
                "text-lg font-semibold text-gray-900 mb-2"
            )
            rel_rows = _relationships_rows(min_confidence=0.0, limit=300)
            rel_cols = [
                {"name": "source", "label": "Source", "field": "source",
                 "sortable": True},
                {"name": "relation", "label": "Relation", "field": "relation",
                 "sortable": True, "style": "width: 120px"},
                {"name": "target", "label": "Target", "field": "target",
                 "sortable": True},
                {"name": "confidence", "label": "Confidence", "field": "confidence",
                 "sortable": True, "style": "width: 110px"},
                {"name": "confidence_score", "label": "Score",
                 "field": "confidence_score", "sortable": True,
                 "style": "width: 80px"},
                {"name": "weight", "label": "Weight", "field": "weight",
                 "sortable": True, "style": "width: 80px"},
            ]
            if rel_rows:
                t = ui.table(columns=rel_cols, rows=rel_rows,
                             pagination={"rowsPerPage": 15}).classes("w-full")
                t.props("flat dense separator=horizontal")
            else:
                ui.label("No relationships yet.").classes("text-sm text-gray-400")
