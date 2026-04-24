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
  html, body { height: 100%; }
  body { margin: 0; font-family: system-ui, sans-serif;
         background: #0f0f1a; color: #e5e7eb;
         display: flex; height: 100vh; overflow: hidden; }
  #graph-wrap { flex: 1; position: relative; }
  #graph { position: absolute; inset: 0; }
  #status { position: absolute; top: 8px; left: 8px; padding: 6px 10px;
            background: rgba(15,15,26,0.8); border: 1px solid #2a2a4e;
            border-radius: 6px; font-size: 12px; z-index: 10; max-width: 60ch; }
  #hint { position: absolute; bottom: 8px; left: 8px; padding: 6px 10px;
          background: rgba(15,15,26,0.8); border: 1px solid #2a2a4e;
          border-radius: 6px; font-size: 11px; z-index: 10; color: #9ca3af; }
  /* Right-side legend panel — matches graphify's graph.html styling
     so users can see cluster labels + toggle communities on/off. */
  #sidebar { width: 280px; background: #1a1a2e; border-left: 1px solid #2a2a4e;
             display: flex; flex-direction: column; overflow: hidden; }
  #sidebar h3 { font-size: 12px; color: #aaa; margin: 0 0 10px 0;
                text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  #legend-wrap { flex: 1; overflow-y: auto; padding: 14px; }
  .legend-item { display: flex; align-items: center; gap: 8px;
                 padding: 5px 4px; cursor: pointer; border-radius: 4px;
                 font-size: 12px; user-select: none; }
  .legend-item:hover { background: #2a2a4e; }
  .legend-item.dimmed { opacity: 0.35; }
  .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { flex: 1; overflow: hidden; text-overflow: ellipsis;
                  white-space: nowrap; color: #e0e0e0; }
  .legend-count { color: #666; font-size: 11px; }
  #sidebar-stats { padding: 10px 14px; border-top: 1px solid #2a2a4e;
                   font-size: 11px; color: #666; }
  * { scrollbar-color: #2a2a4e transparent; scrollbar-width: thin; }
</style>
</head>
<body>
<div id="graph-wrap">
  <div id="status">Loading graph...</div>
  <div id="graph"></div>
  <div id="hint">Scroll to zoom · drag to pan · click a node for details</div>
</div>
<aside id="sidebar">
  <div id="legend-wrap">
    <h3>Communities</h3>
    <div id="legend-list"></div>
  </div>
  <div id="sidebar-stats">Loading...</div>
</aside>
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
  // Translate #RRGGBB into rgba(R,G,B,a). Used so edges can inherit the
  // source node's community color at a lower alpha — that way intra-
  // cluster edges blend into the cluster and cross-cluster bridges read
  // as a visible contrast line, the same trick vis.js does by default
  // when edges.color.inherit='from'.
  function withAlpha(hex, a) {
    const h = (hex || "#6b7280").replace("#", "");
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r},${g},${b},${a})`;
  }
  // Random seed inside a unit square. Earlier revisions pre-seeded on
  // per-community rings, which combined with LinLog + strong gravity
  // shattered the graph into isolated hairballs (the opposite of
  // graphify's organic single-component look). Random + inferSettings
  // matches graphify's output much more closely — FA2 finds the
  // cluster structure on its own from the edge topology.
  function seedPosition() {
    return { x: Math.random(), y: Math.random() };
  }
  // communities.json returns DB-derived labels ({id, label, count}) so
  // the sidebar legend reads like graphify's graph.html did. Loaded in
  // parallel; if it fails we still render the graph but show ids only.
  Promise.all([
    fetch(`/graphify-visual/${PROJECT_ID}/graph.json`)
      .then(r => { if (!r.ok) throw new Error("graph.json " + r.status); return r.json(); }),
    fetch(`/graphify-visual/${PROJECT_ID}/communities.json`)
      .then(r => r.ok ? r.json() : {communities: []})
      .catch(() => ({communities: []})),
  ])
    .then(([data, commData]) => {
      const g = new Graph();
      const rawNodes = data.nodes || [];
      const edges = data.links || data.edges || [];
      // Drop graphify's community-summary rationale nodes — they're prose
      // blobs graphify attaches per community, not actual code, and they
      // inflate the graph by ~40% while adding no navigational value.
      // Edges that touched them get skipped by the hasNode guard below.
      const nodes = rawNodes.filter(n => n.file_type !== "rationale");
      const dropped = rawNodes.length - nodes.length;
      statusEl.textContent = `Loading ${nodes.length.toLocaleString()} nodes, `
        + `${edges.length.toLocaleString()} edges`
        + (dropped ? ` (hid ${dropped.toLocaleString()} rationale)` : "")
        + "...";
      for (const n of nodes) {
        if (g.hasNode(n.id)) continue;
        const pos = seedPosition();
        g.addNode(n.id, {
          label: n.label || n.id,
          size: Math.max(2, Math.log(1 + (n.degree || 1)) * 2),
          color: colorFor(n.community),
          community: n.community ?? null,
          x: pos.x, y: pos.y,
        });
      }
      let edgesDrawn = 0;
      for (const e of edges) {
        const s = e.source, t = e.target;
        if (!g.hasNode(s) || !g.hasNode(t) || s === t) continue;
        // Inherit the source node's community color (what graphify's
        // vis.js graph.html did via edges.color.inherit='from'). Alpha
        // 0.35 lets intra-cluster edges blend into their cluster while
        // cross-cluster bridges still read as colored threads.
        const srcColor = g.getNodeAttribute(s, "color");
        try {
          g.addEdge(s, t, {size: 0.25, color: withAlpha(srcColor, 0.35)});
          edgesDrawn++;
        } catch (_) {}
      }
      // ForceAtlas2 — tune to match graphify's vis.js Barnes-Hut
      // output (single organic hairball with visible community
      // structure). vis.js config we're mimicking:
      //   gravitationalConstant -60, springLength 120, springConstant
      //   0.08, damping 0.4.
      // FA2 equivalents: gravity 1.2 (pulls components together like
      // vis.js's -60 G-constant does), scalingRatio 2 (moderate
      // repulsion), adjustSizes FALSE (true creates starburst spokes
      // around large-degree hubs — the thing we're fighting), and
      // barnesHut for speed over ~2k nodes.
      statusEl.textContent = `Laying out ${nodes.length.toLocaleString()} nodes `
        + `(ForceAtlas2)...`;
      const settings = forceAtlas2.inferSettings(g);
      settings.barnesHutOptimize = g.order > 2000;
      settings.barnesHutTheta = 0.5;
      settings.gravity = 1.2;
      settings.scalingRatio = 2;
      settings.slowDown = 1;
      settings.adjustSizes = false;
      settings.outboundAttractionDistribution = false;
      const iters = g.order > 20000 ? 300 : g.order > 5000 ? 600 : 800;
      const t0 = performance.now();
      // Yield to the browser once so the "Laying out..." status can paint
      // before the synchronous FA2 pass blocks the main thread.
      setTimeout(() => {
        forceAtlas2.assign(g, { iterations: iters, settings });
        const dt = ((performance.now() - t0) / 1000).toFixed(1);
        // Click-to-focus state: when a node is focused, the node
        // reducer dims anything that isn't the node or a neighbor, and
        // the edge reducer dims any edge not incident to it. Using
        // reducers instead of mutating the graph keeps the state
        // toggleable with one click-stage.
        let focusedNode = null;
        let neighborSet = new Set();

        // Hover state: the hovered node grows 30% and its immediate
        // graph-space neighborhood is pushed radially outward to
        // "make space" visually. Push applied inside the node reducer
        // on each frame, so no mutation and no animation loop needed —
        // it just snaps on enter/leave which looks clean at this density.
        let hoveredNode = null;
        let hoveredX = 0, hoveredY = 0;
        const HOVER_PUSH_RADIUS = 8;    // graph units
        const HOVER_PUSH_MAX = 3.5;     // graph units
        const HOVER_SIZE_MULT = 1.3;

        const renderer = new Sigma(g, document.getElementById("graph"), {
          labelDensity: 0.15, labelGridCellSize: 80, minCameraRatio: 0.05,
          maxCameraRatio: 10, defaultNodeColor: "#6b7280",
          defaultEdgeColor: "rgba(107,114,128,0.3)",
          renderEdgeLabels: false,
          enableEdgeEvents: false,
          nodeReducer: (node, data) => {
            let out = data;
            // Focus dimming (click) layers first.
            if (focusedNode) {
              if (node === focusedNode || neighborSet.has(node)) {
                out = { ...out, zIndex: 1 };
              } else {
                out = { ...out, color: "#2a2a3e", label: "", zIndex: 0 };
              }
            }
            // Hover effects: grow hovered, push nearby away.
            if (hoveredNode) {
              if (node === hoveredNode) {
                out = {
                  ...out,
                  size: (out.size || data.size) * HOVER_SIZE_MULT,
                  forceLabel: true,
                  zIndex: 3,
                };
              } else {
                const dx = (data.x || 0) - hoveredX;
                const dy = (data.y || 0) - hoveredY;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (d > 0 && d < HOVER_PUSH_RADIUS) {
                  const t = 1 - (d / HOVER_PUSH_RADIUS);
                  const push = HOVER_PUSH_MAX * t * t;
                  out = {
                    ...out,
                    x: data.x + (dx / d) * push,
                    y: data.y + (dy / d) * push,
                  };
                }
              }
            }
            return out;
          },
          edgeReducer: (edge, data) => {
            if (!focusedNode) return data;
            const ext = g.extremities(edge);
            if (ext[0] === focusedNode || ext[1] === focusedNode) {
              return { ...data, size: 0.8, zIndex: 1 };
            }
            return { ...data, color: "rgba(40,40,60,0.2)", zIndex: 0 };
          },
        });

        // Hover enter/leave: cache the hovered node's graph-space
        // position once so the reducer doesn't re-query per-node.
        renderer.on("enterNode", ({ node }) => {
          hoveredNode = node;
          hoveredX = g.getNodeAttribute(node, "x");
          hoveredY = g.getNodeAttribute(node, "y");
          document.body.style.cursor = "pointer";
          renderer.refresh();
        });
        renderer.on("leaveNode", () => {
          hoveredNode = null;
          document.body.style.cursor = "";
          renderer.refresh();
        });
        statusEl.textContent = `${nodes.length.toLocaleString()} nodes · `
          + `${edgesDrawn.toLocaleString()} edges`
          + (dropped ? ` · ${dropped.toLocaleString()} rationale hidden` : "")
          + ` · FA2 ${iters}it in ${dt}s`;
        renderer.on("clickNode", ({ node }) => {
          focusedNode = node;
          neighborSet = new Set(g.neighbors(node));
          const attrs = g.getNodeAttributes(node);
          statusEl.textContent = `${attrs.label} `
            + `(community ${attrs.community ?? "—"}, `
            + `degree ${g.degree(node)}) — `
            + `click empty space to clear focus`;
          renderer.refresh();
        });
        // Click on the stage (empty space) clears focus highlighting.
        renderer.on("clickStage", () => {
          if (!focusedNode) return;
          focusedNode = null;
          neighborSet = new Set();
          statusEl.textContent = `${nodes.length.toLocaleString()} nodes · `
            + `${edgesDrawn.toLocaleString()} edges`
            + (dropped ? ` · ${dropped.toLocaleString()} rationale hidden` : "")
            + ` · FA2 ${iters}it in ${dt}s`;
          renderer.refresh();
        });

        // --- Legend / communities sidebar ---------------------------
        // Rank communities by actual node count in the rendered graph
        // (post-rationale-filter) instead of raw DB counts, so the
        // numbers match what's on screen. Fall back to id if no label.
        const counts = new Map();
        g.forEachNode((_n, attrs) => {
          const c = attrs.community;
          if (c === null || c === undefined) return;
          counts.set(c, (counts.get(c) || 0) + 1);
        });
        const labelMap = new Map();
        for (const c of (commData.communities || [])) {
          labelMap.set(c.id, c.label);
        }
        const ranked = [...counts.entries()]
          .map(([cid, n]) => ({
            cid, n,
            label: labelMap.get(cid) || `community ${cid}`,
            color: colorFor(cid),
          }))
          .sort((a, b) => b.n - a.n);

        const hidden = new Set();
        const listEl = document.getElementById("legend-list");
        listEl.innerHTML = "";
        for (const c of ranked) {
          const item = document.createElement("div");
          item.className = "legend-item";
          item.innerHTML =
            `<div class="legend-dot" style="background:${c.color}"></div>`
            + `<span class="legend-label" title="${c.label.replace(/"/g,'&quot;')}">`
            + `${c.label}</span>`
            + `<span class="legend-count">${c.n}</span>`;
          item.addEventListener("click", () => {
            if (hidden.has(c.cid)) {
              hidden.delete(c.cid);
              item.classList.remove("dimmed");
            } else {
              hidden.add(c.cid);
              item.classList.add("dimmed");
            }
            // Sigma respects the `hidden` node attribute; toggling it
            // and calling refresh() is the cheapest way to dim a whole
            // community without touching the layout.
            g.forEachNode((nid, attrs) => {
              if (attrs.community === c.cid) {
                g.setNodeAttribute(nid, "hidden", hidden.has(c.cid));
              }
            });
            renderer.refresh();
          });
          listEl.appendChild(item);
        }
        document.getElementById("sidebar-stats").textContent =
          `${ranked.length.toLocaleString()} communities · `
          + `${nodes.length.toLocaleString()} nodes · `
          + `${edgesDrawn.toLocaleString()} edges`;
      }, 50);
    })
    .catch(err => {
      statusEl.textContent = "Error loading graph: " + err.message;
    });
</script>
</body>
</html>"""


@app.get("/graphify-visual/{project_id}/communities.json")
def _graphify_communities(project_id: str):
    """Serve DB-derived community labels for the viewer sidebar.

    Joins the `communities` label table with per-community node counts
    from `entities`, filtering out rationale entries so the counts
    match what the viewer actually renders client-side.
    """
    from fastapi.responses import JSONResponse
    if not _SAFE_PROJECT_RE.match(project_id or ""):
        raise HTTPException(status_code=400, detail="invalid project id")
    ctx = get_project(project_id)
    db_path = ctx._data_dir / "graph.db"
    if not db_path.exists():
        return JSONResponse({"communities": []})
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        try:
            rows = conn.execute(
                "SELECT e.community AS id, COUNT(*) AS n, "
                "       c.label AS label "
                "FROM entities e "
                "LEFT JOIN communities c ON c.id = e.community "
                "WHERE e.community IS NOT NULL "
                "  AND COALESCE(e.file_type,'') != 'rationale' "
                "GROUP BY e.community "
                "ORDER BY n DESC"
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                "SELECT community AS id, COUNT(*) AS n, NULL AS label "
                "FROM entities WHERE community IS NOT NULL "
                "GROUP BY community ORDER BY n DESC"
            ).fetchall()
        out = [
            {
                "id": int(r["id"]),
                "label": (r["label"] if "label" in r.keys() else None)
                         or f"community {r['id']}",
                "count": int(r["n"]),
            }
            for r in rows
        ]
    finally:
        conn.close()
    return JSONResponse({"communities": out})


@app.get("/graphify-visual/{project_id}/{filename}")
def _graphify_visual(project_id: str, filename: str):
    """Serve graph.json for the WebGL viewer. Project slug strictly
    validated to prevent path traversal. Declared after the specific
    communities.json route so literal filenames take precedence over
    this path-parameter fallback."""
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
