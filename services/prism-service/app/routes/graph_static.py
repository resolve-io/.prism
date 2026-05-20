"""Graph static routes — Sigma.js viewer HTML and graphify-visual JSON.

Extracted from the deleted app/ui/graph_page.py during the v5.0.0 cutover.
The interactive viewer is server-rendered HTML that delegates rendering to
the user's browser GPU; community labels and graph.json are served as JSON
files. None of these routes depend on NiceGUI.
"""

from __future__ import annotations

import re
import sqlite3

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.project_context import get_project

router = APIRouter()


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
     so users can see cluster labels + toggle clusters on/off. */
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
    <h3>Clusters</h3>
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
  import FA2Layout from "https://esm.sh/graphology-layout-forceatlas2@0.10.1/worker";
  import Sigma from "https://esm.sh/sigma@3.0.0";
  // Yield to the browser between batches of synchronous work so paint /
  // input can run. requestAnimationFrame is the right primitive here —
  // it lines us up with the next frame, which is the moment Sigma will
  // try to redraw too.
  const yieldToBrowser = () => new Promise(r => requestAnimationFrame(r));
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
  // HSL round-trip utilities. Shading by degree modulates the L
  // channel while keeping H+S fixed, so every node in a community
  // shares the base hue and saturation — only perceived lightness
  // changes with connection count.
  function hexToHsl(hex) {
    const h = (hex || "#6b7280").replace("#", "");
    const r = parseInt(h.substring(0, 2), 16) / 255;
    const g = parseInt(h.substring(2, 4), 16) / 255;
    const b = parseInt(h.substring(4, 6), 16) / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    const l = (mx + mn) / 2;
    let hh, ss;
    if (mx === mn) { hh = 0; ss = 0; }
    else {
      const d = mx - mn;
      ss = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
      if (mx === r) hh = ((g - b) / d + (g < b ? 6 : 0));
      else if (mx === g) hh = ((b - r) / d + 2);
      else hh = ((r - g) / d + 4);
      hh *= 60;
    }
    return { h: hh, s: ss * 100, l: l * 100 };
  }
  function hslToRgb(h, s, l) {
    // h in [0,360], s/l in [0,100]
    s /= 100; l /= 100;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = l - c / 2;
    let r1, g1, b1;
    if (h < 60)       [r1, g1, b1] = [c, x, 0];
    else if (h < 120) [r1, g1, b1] = [x, c, 0];
    else if (h < 180) [r1, g1, b1] = [0, c, x];
    else if (h < 240) [r1, g1, b1] = [0, x, c];
    else if (h < 300) [r1, g1, b1] = [x, 0, c];
    else              [r1, g1, b1] = [c, 0, x];
    return `rgb(${Math.round((r1 + m) * 255)},${Math.round((g1 + m) * 255)},${Math.round((b1 + m) * 255)})`;
  }
  // Community hue with L modulated in [25, 75] by normalized log-degree.
  function shadeByDegree(baseHex, norm) {
    const { h, s } = hexToHsl(baseHex);
    const L = 25 + 50 * Math.max(0, Math.min(1, norm));
    return hslToRgb(h, s, L);
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
  // parallel; if it fails we still render the graph but mark clusters as
  // unlabeled instead of exposing graphify's raw numeric community ids.
  async function loadGraph() {
      statusEl.textContent = "Fetching graph data...";
      const [data, commData] = await Promise.all([
        fetch(`/graphify-visual/${PROJECT_ID}/graph.json`)
          .then(r => { if (!r.ok) throw new Error("graph.json " + r.status); return r.json(); }),
        fetch(`/graphify-visual/${PROJECT_ID}/communities.json`)
          .then(r => r.ok ? r.json() : {communities: []})
          .catch(() => ({communities: []})),
      ]);
      const g = new Graph();
      const rawNodes = data.nodes || [];
      const edges = data.links || data.edges || [];
      const labelMap = new Map();
      for (const c of (commData.communities || [])) {
        labelMap.set(c.id, c.label);
        labelMap.set(String(c.id), c.label);
      }
      const clusterLabel = community =>
        labelMap.get(community) || labelMap.get(String(community))
        || "unlabeled cluster";
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
      // Visible-subgraph degree: recount edges where both endpoints are
      // kept so the ~40% hidden rationale nodes don't inflate the base
      // numbers. Then normalize log-degree PER COMMUNITY: a 200-node
      // cluster's brightness range shouldn't get swamped by the
      // 2000-node cluster's range, and "hub-ness" is meaningful relative
      // to siblings in the same community.
      const visibleIds = new Set(nodes.map(n => n.id));
      const visDeg = new Map();
      for (const n of nodes) visDeg.set(n.id, 0);
      for (const e of edges) {
        const s = e.source, t = e.target;
        if (!visibleIds.has(s) || !visibleIds.has(t) || s === t) continue;
        visDeg.set(s, (visDeg.get(s) || 0) + 1);
        visDeg.set(t, (visDeg.get(t) || 0) + 1);
      }
      const commLo = new Map(), commHi = new Map();
      const commKey = n => String(n.community ?? "null");
      for (const n of nodes) {
        const k = commKey(n);
        const v = Math.log(1 + (visDeg.get(n.id) || 0));
        if (!commLo.has(k) || v < commLo.get(k)) commLo.set(k, v);
        if (!commHi.has(k) || v > commHi.get(k)) commHi.set(k, v);
      }
      // Stream node insertion in ~2k batches, yielding to the browser
      // between batches. graphology's addNode runs ~5-10K/sec; processing
      // 50K nodes in one synchronous loop locks the tab for several
      // seconds. Batched + RAF gives the user a live progress count and
      // keeps input responsive.
      const NODE_BATCH = 2000;
      for (let i = 0; i < nodes.length; ) {
        const end = Math.min(i + NODE_BATCH, nodes.length);
        for (; i < end; i++) {
          const n = nodes[i];
          if (g.hasNode(n.id)) continue;
          const pos = seedPosition();
          const k = commKey(n);
          const v = Math.log(1 + (visDeg.get(n.id) || 0));
          const range = (commHi.get(k) - commLo.get(k)) || 1;
          const norm = (v - commLo.get(k)) / range;
          g.addNode(n.id, {
            label: n.label || n.id,
            // Near-uniform size (2.5-3.3). Degree expressed through
            // brightness, not radius — large degree→size mappings turn
            // hubs into canvas-dominating blobs.
            size: 2.5 + 0.8 * norm,
            color: shadeByDegree(colorFor(n.community), norm),
            community: n.community ?? null,
            communityLabel: clusterLabel(n.community),
            x: pos.x, y: pos.y,
          });
        }
        statusEl.textContent =
          `Loading nodes ${i.toLocaleString()} / ${nodes.length.toLocaleString()}...`;
        await yieldToBrowser();
      }
      // Stream edge insertion — addEdge is cheaper than addNode so the
      // batch is larger, but the principle is the same: never block the
      // main thread for more than a frame.
      let edgesDrawn = 0;
      const EDGE_BATCH = 5000;
      for (let i = 0; i < edges.length; ) {
        const end = Math.min(i + EDGE_BATCH, edges.length);
        for (; i < end; i++) {
          const e = edges[i];
          const s = e.source, t = e.target;
          if (!g.hasNode(s) || !g.hasNode(t) || s === t) continue;
          // Edge color = source node's COMMUNITY hue at low alpha, not the
          // degree-shaded node color. A dim leaf connected to a bright hub
          // should still contribute a visible community-colored thread —
          // inheriting the shaded color made leaf-anchored edges fade to
          // invisible, which killed the webby between-community feel.
          const srcComm = g.getNodeAttribute(s, "community");
          try {
            g.addEdge(s, t, {
              size: 0.25,
              color: withAlpha(colorFor(srcComm), 0.3),
            });
            edgesDrawn++;
          } catch (_) {}
        }
        statusEl.textContent =
          `Loading edges ${i.toLocaleString()} / ${edges.length.toLocaleString()}...`;
        await yieldToBrowser();
      }
      // ----- ForceAtlas2 in a Web Worker (fully invisible) ----------
      // FA2 is mathematically chaotic during early iterations — watching
      // it live looks like a spazz attack and even post-warmup the per-
      // iteration jitter doesn't read as "smooth". The fix: compute the
      // layout fully off-screen (worker keeps the main thread responsive),
      // capture the converged positions, then play back a clean cluster-
      // by-cluster reveal animation that doesn't depend on FA2's frame
      // timing at all.
      const settings = forceAtlas2.inferSettings(g);
      settings.barnesHutOptimize = g.order > 2000;
      settings.barnesHutTheta = 0.5;
      settings.gravity = 1.2;
      settings.scalingRatio = 2;
      settings.slowDown = 1;
      settings.adjustSizes = false;
      settings.outboundAttractionDistribution = false;
      const computeMs = g.order > 20000 ? 5000 : g.order > 5000 ? 4000 : 3000;
      const layout = new FA2Layout(g, { settings });
      const t0 = performance.now();
      layout.start();

      // Click the (still-empty) canvas to skip straight to the result.
      let skipped = false;
      const graphEl = document.getElementById("graph");
      graphEl.style.cursor = "wait";
      const skipHandler = () => { skipped = true; };
      graphEl.addEventListener("click", skipHandler, { once: true });
      statusEl.textContent =
        `Computing layout (${(computeMs / 1000).toFixed(1)}s)...`;
      const cStart = performance.now();
      while (performance.now() - cStart < computeMs && !skipped) {
        await new Promise(r => setTimeout(r, 50));
      }
      graphEl.removeEventListener("click", skipHandler);
      graphEl.style.cursor = "";
      layout.stop();
      layout.kill();

      // Snapshot the final per-node sizes, then hide everything and zero
      // out sizes so Sigma's first paint shows nothing. The reveal
      // animation below will pop each cluster in. Edges auto-hide when
      // either endpoint is hidden (Sigma default), so they appear as
      // their endpoints become visible — no separate edge animation.
      const finalSize = new Map();
      g.updateEachNodeAttributes((id, attrs) => {
        finalSize.set(id, attrs.size);
        return { ...attrs, hidden: true, size: 0 };
      });

      // ----- Sigma renderer (mounted now, on settled positions) -----
      // Click-to-focus state: when a node is focused, the node reducer
      // dims anything that isn't the node or a neighbor, and the edge
      // reducer dims any edge not incident to it. Using reducers keeps
      // focus toggleable with one click-stage.
      let focusedNode = null;
      let neighborSet = new Set();
      // Hover state: the hovered node grows 30% and its immediate
      // graph-space neighborhood is pushed radially outward to "make
      // space" visually. Push applied inside the node reducer on each
      // frame — no mutation, no animation loop, just a snap on
      // enter/leave that looks clean at this density.
      let hoveredNode = null;
      let hoveredX = 0, hoveredY = 0;
      const HOVER_PUSH_RADIUS = 8;    // graph units
      const HOVER_PUSH_MAX = 3.5;     // graph units
      const HOVER_SIZE_MULT = 1.3;

      // layoutElapsed is filled in after the visible phase finishes; the
      // closure picks up whatever value it holds when baseStatus() is
      // called, so click handlers reading the status get the right text.
      let layoutElapsed = "...";
      const baseStatus = () =>
        `${nodes.length.toLocaleString()} nodes · `
        + `${edgesDrawn.toLocaleString()} edges`
        + (dropped ? ` · ${dropped.toLocaleString()} rationale hidden` : "")
        + ` · FA2 ${layoutElapsed}s`;

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
      renderer.on("clickNode", ({ node }) => {
        focusedNode = node;
        neighborSet = new Set(g.neighbors(node));
        const attrs = g.getNodeAttributes(node);
        statusEl.textContent = `${attrs.label} `
          + `(cluster: ${attrs.communityLabel || "unlabeled cluster"}, `
          + `degree ${g.degree(node)}) — `
          + `click empty space to clear focus`;
        renderer.refresh();
      });
      // Click on the stage (empty space) clears focus highlighting.
      renderer.on("clickStage", () => {
        if (!focusedNode) return;
        focusedNode = null;
        neighborSet = new Set();
        statusEl.textContent = baseStatus();
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
      const ranked = [...counts.entries()]
        .map(([cid, n]) => ({
          cid, n,
          label: clusterLabel(cid),
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
        `${ranked.length.toLocaleString()} clusters · `
        + `${nodes.length.toLocaleString()} nodes · `
        + `${edgesDrawn.toLocaleString()} edges`;

      // ----- Cluster-by-cluster reveal animation --------------------
      // Group nodes by community, biggest first. Each cluster starts
      // popping in `staggerMs` after the previous one starts; within a
      // cluster, every node fades from size=0 to its final size with
      // ease-out cubic. Pure WebGL render-loop animation — no physics,
      // no jitter. Skipping during compute jumps straight to final.
      const byCommunity = new Map();
      g.forEachNode((id, attrs) => {
        const k = String(attrs.community ?? "null");
        if (!byCommunity.has(k)) byCommunity.set(k, []);
        byCommunity.get(k).push(id);
      });
      const orderedComms = [...byCommunity.values()]
        .sort((a, b) => b.length - a.length);

      // Total reveal budget ~2s; pack stagger into it but cap so single-
      // cluster graphs still get a visible fade.
      const revealBudget = 2000;
      const fadeMs = 500;
      const staggerMs = orderedComms.length > 1
        ? Math.max(40, Math.min(180,
            (revealBudget - fadeMs) / (orderedComms.length - 1)))
        : 0;
      const startTime = new Map();
      orderedComms.forEach((ids, idx) => {
        const t = idx * staggerMs;
        for (const id of ids) startTime.set(id, t);
      });
      const totalAnimMs = staggerMs * Math.max(0, orderedComms.length - 1)
        + fadeMs;

      if (!skipped) {
        statusEl.textContent =
          `Revealing ${orderedComms.length} clusters...`;
        await new Promise(resolve => {
          const aStart = performance.now();
          const easeOut = t => 1 - Math.pow(1 - t, 3);
          const step = () => {
            const elapsed = performance.now() - aStart;
            g.updateEachNodeAttributes((id, attrs) => {
              const start = startTime.get(id) || 0;
              const t = Math.min(1, Math.max(0, (elapsed - start) / fadeMs));
              if (t <= 0) return attrs; // not yet — leave hidden
              return {
                ...attrs,
                hidden: false,
                size: finalSize.get(id) * easeOut(t),
              };
            });
            if (elapsed < totalAnimMs) requestAnimationFrame(step);
            else resolve();
          };
          requestAnimationFrame(step);
        });
      } else {
        // Skipped — snap straight to final.
        g.updateEachNodeAttributes((id, attrs) => ({
          ...attrs,
          hidden: false,
          size: finalSize.get(id),
        }));
      }
      layoutElapsed = ((performance.now() - t0) / 1000).toFixed(1);
      statusEl.textContent = baseStatus();
  }
  loadGraph().catch(err => {
    statusEl.textContent = "Error loading graph: " + err.message;
  });
</script>
</body>
</html>"""


@router.get("/graphify-visual/{project_id}/communities.json")
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


@router.get("/graphify-visual/{project_id}/{filename}")
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


@router.get("/graph/viewer/{project_id}")
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
