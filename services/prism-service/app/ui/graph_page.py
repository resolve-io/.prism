"""Graph page — visualise graphify-populated entities and relationships."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app, ui

from app.project_context import get_project
from app.services.graph_service import (
    compute_node_hierarchy,
    display_label_for_graph_node,
    infer_architectural_layer,
)
from app.ui.components.nav import create_nav, page_container


_SAFE_PROJECT_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
# Only graph.json is served now — the WebGL viewer is the only frontend.
# The legacy graphify graph.html / GRAPH_REPORT.md paths were dropped
# because they capped at ~11K nodes and the Sigma viewer covers every
# size graphify can produce.
_ALLOWED_VISUAL_FILES = {"graph.json"}
_CS_SUFFIXES = (".cs", ".csx", ".razor.cs")
_TS_JS_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")
_VISUAL_MEMBER_LIMIT = 80


_SIGMA_VIEWER_HTML = r"""<!DOCTYPE html>
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
  /* Right-side region panel — GitNexus-style: semantic regions first,
     then click/hover to descend into their contents. */
  #sidebar { width: 280px; background: #1a1a2e; border-left: 1px solid #2a2a4e;
             display: flex; flex-direction: column; overflow: hidden; }
  #sidebar h3 { font-size: 12px; color: #aaa; margin: 0 0 10px 0;
                text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
  #legend-wrap { flex: 1; overflow-y: auto; padding: 14px; }
  #search-wrap { margin-bottom: 14px; }
  #graph-search { width: 100%; box-sizing: border-box; border: 1px solid #34345a;
                  background: #111123; color: #eef2ff; border-radius: 6px;
                  padding: 8px 9px; font: 12px system-ui, sans-serif; outline: none; }
  #graph-search:focus { border-color: #60a5fa; box-shadow: 0 0 0 2px rgba(96,165,250,0.18); }
  #search-results { margin-top: 6px; display: none; border: 1px solid #2a2a4e;
                    border-radius: 6px; overflow: hidden; background: #141427; }
  .search-result { padding: 7px 8px; cursor: pointer; border-bottom: 1px solid #24243f; }
  .search-result:last-child { border-bottom: none; }
  .search-result:hover { background: #252547; }
  .search-title { color: #f8fafc; font-size: 12px; overflow: hidden;
                  text-overflow: ellipsis; white-space: nowrap; }
  .search-meta { margin-top: 2px; color: #7f8aa3; font-size: 10px; }
  #layer-filters, #relation-filters { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  .filter-chip { display: inline-flex; align-items: center; gap: 5px;
                 padding: 3px 7px; border-radius: 999px; border: 1px solid #34345a;
                 background: #17172b; color: #dbe4f0; font-size: 11px;
                 cursor: pointer; user-select: none; }
  .filter-chip:hover { background: #242443; }
  .filter-chip.off { opacity: 0.35; text-decoration: line-through; }
  .layer-chip-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .relation-chip-dot { color: #8fa1c2; font-size: 10px; }
  #nav-controls { display: flex; gap: 6px; margin-top: 10px; }
  .nav-btn { flex: 1; border: 1px solid #34345a; background: #17172b;
             color: #dbe4f0; border-radius: 6px; padding: 6px 8px;
             font-size: 11px; cursor: pointer; }
  .nav-btn:hover { background: #242443; }
  .nav-btn.active { border-color: #60a5fa; background: #1d3152; color: #f8fafc; }
  .nav-btn:disabled { opacity: 0.4; cursor: default; }
  #breadcrumb { display: flex; flex-wrap: wrap; align-items: center;
                gap: 5px; margin-top: 8px; min-height: 18px; }
  .crumb { border: 0; border-radius: 999px; padding: 3px 7px;
           background: #24243d; color: #dbe4f0; font-size: 10px;
           cursor: pointer; max-width: 100%; overflow: hidden;
           text-overflow: ellipsis; white-space: nowrap; }
  .crumb:hover { background: #303056; }
  .crumb-sep { color: #596174; font-size: 10px; }
  .legend-item { display: flex; align-items: center; gap: 8px;
                 padding: 5px 4px; cursor: pointer; border-radius: 4px;
                 font-size: 12px; user-select: none; }
  .legend-item:hover { background: #2a2a4e; }
  .legend-item.dimmed { opacity: 0.35; }
  .legend-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
  .legend-label { flex: 1; overflow: hidden; text-overflow: ellipsis;
                  white-space: nowrap; color: #e0e0e0; }
  .legend-count { color: #666; font-size: 11px; }
  #inspector { border-top: 1px solid #2a2a4e; padding: 14px;
               background: rgba(10,10,20,0.24); }
  #inspector-body { font-size: 12px; color: #cbd5e1; line-height: 1.45; }
  .inspector-title { color: #f8fafc; font-weight: 700; font-size: 13px;
                     margin-bottom: 8px; overflow-wrap: anywhere; }
  .inspector-row { display: flex; justify-content: space-between; gap: 10px;
                   padding: 3px 0; border-bottom: 1px solid rgba(42,42,78,0.45); }
  .inspector-key { color: #7f8aa3; }
  .inspector-value { color: #e5e7eb; text-align: right; overflow-wrap: anywhere; }
  .inspector-summary { margin-top: 9px; color: #aab4c8; }
  .inspector-neighbors { margin-top: 9px; display: flex; flex-wrap: wrap; gap: 5px; }
  .inspector-symbols { margin-top: 10px; border-top: 1px solid #252545; padding-top: 8px; }
  .inspector-symbol { color: #cbd5e1; font-size: 11px; line-height: 1.35;
                      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .inspector-symbol-more { color: #7f8aa3; font-size: 10px; margin-top: 4px; }
  .neighbor-pill { max-width: 100%; padding: 2px 6px; border-radius: 999px;
                   background: #24243d; color: #dbe4f0; font-size: 11px;
                   overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                   border: 0; cursor: pointer; }
  .neighbor-pill:hover { background: #303056; }
  .neighbor-rel { color: #8fa1c2; }
  .inspector-empty { color: #64748b; }
  #sidebar-stats { padding: 10px 14px; border-top: 1px solid #2a2a4e;
                   font-size: 11px; color: #666; }
  * { scrollbar-color: #2a2a4e transparent; scrollbar-width: thin; }
</style>
</head>
<body>
<div id="graph-wrap">
  <div id="status">Loading graph...</div>
  <div id="graph"></div>
  <div id="hint">Scroll to zoom L0→L3 · drag to pan · click a super-node to drill in</div>
</div>
<aside id="sidebar">
  <div id="legend-wrap">
    <div id="search-wrap">
      <input id="graph-search" type="search" placeholder="Search regions, types, and files" autocomplete="off" />
      <div id="search-results"></div>
      <div id="layer-filters"></div>
      <div id="relation-filters"></div>
      <div id="nav-controls">
        <button id="nav-back" class="nav-btn" type="button">Back</button>
        <button id="nav-overview" class="nav-btn" type="button">Overview</button>
        <button id="nav-whole" class="nav-btn" type="button">Whole</button>
      </div>
      <div id="breadcrumb"></div>
    </div>
    <h3>Regions</h3>
    <div id="legend-list"></div>
  </div>
  <div id="inspector">
    <h3>Selection</h3>
    <div id="inspector-body" class="inspector-empty">No selection</div>
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
  const LAYER_COLORS = {
    ui: "#2DD4BF",
    api: "#60A5FA",
    service: "#A78BFA",
    data: "#34D399",
    domain: "#FBBF24",
    test: "#F87171",
    docs: "#94A3B8",
    config: "#F59E0B",
    tooling: "#C084FC",
    other: "#64748B",
  };
  function colorForLayer(layer) {
    return LAYER_COLORS[layer || "other"] || LAYER_COLORS.other;
  }
  // Translate #RRGGBB into rgba(R,G,B,a). Used so edges can inherit the
  // source node's architectural-layer color at a lower alpha — that way
  // intra-region edges blend into the region and cross-region bridges
  // read as visible contrast lines.
  function withAlpha(hex, a) {
    const h = (hex || "#6b7280").replace("#", "");
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r},${g},${b},${a})`;
  }
  // Multiply an existing color (hex OR rgba(...)) by `a`. Used by the
  // LOD reducers to blend whichever color the node/edge already has —
  // hex super-node fills, rgba leaf-edge tints — through a level
  // boundary without losing its underlying hue.
  function multiplyAlpha(color, a) {
    if (a >= 0.999) return color;
    if (!color) return `rgba(107,114,128,${a})`;
    if (color[0] === "#") return withAlpha(color, a);
    const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
    if (!m) return color;
    const a0 = m[4] !== undefined ? parseFloat(m[4]) : 1;
    return `rgba(${m[1]},${m[2]},${m[3]},${a0 * a})`;
  }
  const LEVEL_FADE_MS = 240;
  const L0_DENSE_COUNT = 120;
  const L0_HUGE_COUNT = 240;
  const RELAX_NODE_LIMIT = 80;
  const L0_SUPER_EDGE_LIMIT = 900;
  // HSL round-trip utilities. Shading by degree modulates the L
  // channel while keeping H+S fixed, so every node in a layer shares
  // the base hue and saturation — only perceived lightness changes
  // with connection count.
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
  // Layer hue with L modulated in [25, 75] by normalized log-degree.
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
  // hierarchy.json returns leaves tagged with l0/l1/l2 parent keys + the
  // DB-derived community labels for the legend. One fetch primes both
  // the LOD super-node assembly (after FA2) and the legend.
  async function loadGraph() {
      statusEl.textContent = "Fetching graph data...";
      const data = await fetch(`/graphify-visual/${PROJECT_ID}/hierarchy.json`)
        .then(r => {
          if (!r.ok) throw new Error("hierarchy " + r.status);
          return r.json();
        });
      const g = new Graph();
      const rawNodes = data.nodes || [];
      const edges = data.edges || data.links || [];
      const commLabelsMap = new Map();
      for (const [k, v] of Object.entries(data.community_labels || {})) {
        commLabelsMap.set(Number(k), v);
        commLabelsMap.set(String(k), v);
      }
      const commMetaMap = new Map();
      for (const [k, v] of Object.entries(data.community_meta || {})) {
        commMetaMap.set(Number(k), v || {});
        commMetaMap.set(String(k), v || {});
      }
      const clusterLabel = community =>
        commLabelsMap.get(community) || commLabelsMap.get(String(community))
        || "unlabeled cluster";
      const clusterSummary = community =>
        (commMetaMap.get(community) || commMetaMap.get(String(community)) || {}).summary || "";
      // Track which abstraction level the camera ratio currently maps to.
      // Declared up here so the Sigma reducer closure (built farther down)
      // captures the live binding.
      //
      // Threshold tuning notes:
      //   The bbox Sigma normalizes against includes the spread super-
      //   nodes (3× leaf extent at L0), so ratio=1.0 = "fit super-node
      //   spread to viewport." Lower thresholds keep the active level
      //   filling the canvas instead of shrinking into a tiny island.
      let currentLevel = 0;
      let prevLevel = 0;
      let levelTransitionStart = 0;
      // Per-level alpha for the LOD reducer. Exactly one level is
      // visible at any settled moment — the previous wide-ratio
      // crossfade caused a confusing mix where, e.g., L2 super-nodes
      // ghosted on top of the L3 leaf mesh. When currentLevel
      // changes (via click-drill or 80%-bbox auto-drill) a short
      // smoothstep fade interpolates from the old layer to the new.
      function smoothAlphas() {
        const now = performance.now();
        if (
          smoothAlphas.cache
          && smoothAlphas.cacheLevel === currentLevel
          && smoothAlphas.cachePrevLevel === prevLevel
          && smoothAlphas.cacheStart === levelTransitionStart
          && now - smoothAlphas.cacheNow < 8
        ) {
          return smoothAlphas.cache;
        }
        const out = [0, 0, 0, 0];
        const elapsed = now - levelTransitionStart;
        if (elapsed >= LEVEL_FADE_MS) {
          out[currentLevel] = 1;
          smoothAlphas.cache = out;
          smoothAlphas.cacheNow = now;
          smoothAlphas.cacheLevel = currentLevel;
          smoothAlphas.cachePrevLevel = prevLevel;
          smoothAlphas.cacheStart = levelTransitionStart;
          return out;
        }
        const t = elapsed / LEVEL_FADE_MS;
        const eased = t * t * (3 - 2 * t);
        out[currentLevel] = eased;
        out[prevLevel] = 1 - eased;
        smoothAlphas.cache = out;
        smoothAlphas.cacheNow = now;
        smoothAlphas.cacheLevel = currentLevel;
        smoothAlphas.cachePrevLevel = prevLevel;
        smoothAlphas.cacheStart = levelTransitionStart;
        return out;
      }
      // Click-to-drill focus stack. Each entry is {level, key} — the
      // ancestor a click pushed down to. Reducers + legend render only
      // descendants of the deepest entry. Wheeling out past a focus
      // level pops it; clicking empty space clears the stack.
      let focusPath = [];
      const focusKey = () => focusPath.length > 0
        ? focusPath[focusPath.length - 1] : null;
      // Latest camera ratio cached for the LOD reducer. Sigma calls
      // the reducer during its own constructor (before `camera` is
      // assigned), so we can't read getState() in the closure — read
      // this mirror instead and refresh it from the camera "updated"
      // handler, which fires on every animation frame.
      let currentRatio = 1.8;
      // Drop graphify's community-summary rationale nodes — they're prose
      // blobs graphify attaches per community, not actual code, and they
      // inflate the graph by ~40% while adding no navigational value.
      // Edges that touched them get skipped by the hasNode guard below.
      const nodes = rawNodes.filter(n => n.file_type !== "rationale");
      const dropped = rawNodes.length - nodes.length;
      const totalMembers = nodes.reduce(
        (sum, n) => sum + (n.member_count || n.symbol_count || 1),
        0
      );

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
            layer: n.layer || "other",
            color: shadeByDegree(colorForLayer(n.layer), norm),
            community: n.community ?? null,
            communityLabel: clusterLabel(n.community),
            communitySummary: clusterSummary(n.community),
            sourceFile: n.source_file || "",
            sourceLocation: n.source_location || "",
            fileType: n.file_type || "",
            visualKind: n.visual_kind || n.file_type || "symbol",
            memberCount: n.member_count || n.symbol_count || 1,
            symbols: Array.isArray(n.symbols) ? n.symbols : [],
            // L3 = leaf. Parent keys at L0/L1/L2 are emitted by the
            // server from the file path; the LOD pass below uses them
            // to assemble super-nodes after FA2 settles.
            level: 3,
            l0: n.l0 || null,
            l1: n.l1 || null,
            l2: n.l2 || null,
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
      const leafAdj = new Map();
      function addLeafAdj(from, to, relation, direction) {
        if (!leafAdj.has(from)) leafAdj.set(from, []);
        leafAdj.get(from).push({ id: to, relation, direction });
      }
      let edgesDrawn = 0;
      const EDGE_BATCH = 5000;
      for (let i = 0; i < edges.length; ) {
        const end = Math.min(i + EDGE_BATCH, edges.length);
        for (; i < end; i++) {
          const e = edges[i];
          const s = e.source, t = e.target;
          if (!g.hasNode(s) || !g.hasNode(t) || s === t) continue;
          const relation = e.relation || e.kind || e.type || "related";
          addLeafAdj(s, t, relation, "out");
          addLeafAdj(t, s, relation, "in");
          // Edge color = source node's architectural-layer hue at low alpha,
          // not the degree-shaded node color. A dim leaf connected to a
          // bright hub should still contribute a visible layer-colored thread.
          const srcLayer = g.getNodeAttribute(s, "layer");
          try {
            g.addEdge(s, t, {
              size: 0.25,
              color: withAlpha(colorForLayer(srcLayer), 0.3),
              level: 3,
              relation,
              confidence: e.confidence || "",
              confidenceScore: e.confidence_score || null,
              sourceLocation: e.source_location || "",
              callSiteFile: e.source_file || "",
              aggregateCount: e.aggregate_count || 1,
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

      // ----- Super-node assembly (LOD hierarchy) ----------------------
      // For each abstraction level, group the L3 leaves by their l0/l1/l2
      // parent and add a super-node at the centroid of its members.
      // Super-edges aggregate leaf edges between matching parent groups.
      // The level attribute on every node + edge is what the LOD reducer
      // below keys on to show only one zoom level at a time.
      function buildSupers(levelKey, lvl) {
        const groups = new Map();
        g.forEachNode((id, attrs) => {
          if (attrs.level !== 3) return;
          const k = attrs[levelKey];
          if (!k) return;
          if (!groups.has(k)) groups.set(k, {
            ids: [], sx: 0, sy: 0, comm: new Map(), layer: new Map(),
            symbolCount: 0,
            // Capture the leaves' ancestor keys so descendants retain
            // their exact community/path lineage. Splitting keys later
            // would lose that lineage for comm:<id>/path combinations.
            ancL0: attrs.l0, ancL1: attrs.l1, ancL2: attrs.l2,
          });
          const grp = groups.get(k);
          grp.ids.push(id);
          grp.sx += attrs.x; grp.sy += attrs.y;
          grp.symbolCount += attrs.memberCount || 1;
          const c = attrs.community ?? "_";
          grp.comm.set(c, (grp.comm.get(c) || 0) + 1);
          const layer = attrs.layer || "other";
          grp.layer.set(layer, (grp.layer.get(layer) || 0) + 1);
        });
        // Find the max member count *within this level* so size
        // scaling is normalised per level — proportional to the
        // largest group at L0/L1/L2 separately. The previous
        // 8 + 4·log(n) saturated, giving express-web-api (5852) a
        // 42.7-unit radius vs. rita-client (75) at 25.3 — visual
        // areas of 5728 vs 2009 px², a 2.85× ratio that the customer
        // perceives as "giants swallow smalls". Closes #79.
        let maxMembers = 1;
        for (const grp of groups.values()) {
          if (grp.ids.length > maxMembers) maxMembers = grp.ids.length;
        }
        const logMax = Math.log(1 + maxMembers) || 1;
        const ranked = [...groups.entries()]
          .sort((a, b) => b[1].ids.length - a[1].ids.length);
        const rankByKey = new Map();
        ranked.forEach(([k], idx) => rankByKey.set(k, idx));
        const isDenseL0 = lvl === 0 && groups.size >= L0_DENSE_COUNT;
        const isHugeL0 = lvl === 0 && groups.size >= L0_HUGE_COUNT;
        // Top-K-by-size super-nodes get forceLabel; the rest let
        // Sigma's labelDensity hide them when collisions occur.
        // On massive L0 graphs, make that set smaller and keep
        // unlabeled communities as compact colored landmarks. This
        // preserves the full shape without turning the overview into
        // a label layout problem.
        const LABEL_TOP_K = lvl === 0
          ? (isHugeL0 ? 6 : isDenseL0 ? 8 : 12)
          : 18;
        const labelTopK = new Set();
        for (const [k] of ranked.slice(0, LABEL_TOP_K)) labelTopK.add(k);
        for (const [key, grp] of groups) {
          const n = grp.ids.length;
          let bestC = null, bestN = -1;
          for (const [c, cnt] of grp.comm)
            if (cnt > bestN) { bestN = cnt; bestC = c === "_" ? null : c; }
          let bestLayer = "other", bestLayerN = -1;
          for (const [layer, cnt] of grp.layer)
            if (cnt > bestLayerN) { bestLayerN = cnt; bestLayer = layer; }
          // Strip path parents to the rightmost segment for a readable
          // label. comm:<id> fallback (flat repos) resolves to the
          // DB-derived community label, then truncated at the first
          // " · " separator so legend / canvas don't show the
          // graphify "<file> · <hub>" suffix as a mashed-up string.
          const rawLabel = key.startsWith("comm:") && !key.includes("/")
              ? (clusterLabel(Number(key.slice(5))) || ("cluster " + key.slice(5)))
              : (key.split("/").pop() || key);
          const labelText = (() => {
            const dot = rawLabel.indexOf(" · ");
            return dot > 0 ? rawLabel.substring(0, dot) : rawLabel;
          })();
          // Larger labels at higher abstraction levels so the L0 view
          // reads instantly. Sigma honors per-node labelSize.
          const labelSizeForLevel = lvl === 0
            ? (isHugeL0 ? 16 : isDenseL0 ? 18 : 22)
            : lvl === 1 ? 18 : 15;
          // Ancestor keys come from the leaves themselves, not from
          // splitting `key`; community-prefixed path keys need to keep
          // their exact ancestry for focus filtering.
          const ancL0 = grp.ancL0 || (key.split("/")[0] || key);
          const ancL1 = grp.ancL1
            || (key.split("/").slice(0, 2).join("/") || ancL0);
          const ancL2 = grp.ancL2
            || (key.split("/").slice(0, 3).join("/") || ancL1);
          // Spawn position: a small random jitter very close to the
          // graph centroid (or leaf-graph center for L0). The centroid
          // itself is the *target* — physics adds an attraction force
          // that pulls the super-node toward target while repulsion
          // pushes it away from overlapping siblings. Net effect: the
          // user sees clusters bloom outward from the centre and
          // settle into their natural homes.
          const targetX = grp.sx / n;
          const targetY = grp.sy / n;
          const jx = (Math.random() - 0.5) * (isDenseL0 ? 3 : 8);
          const jy = (Math.random() - 0.5) * (isDenseL0 ? 3 : 8);
          // Proportional log-scale radius, normalised so the level's
          // largest super-node hits SIZE_MAX and a singleton sits at
          // SIZE_MIN. Tighter than the old 8 + 4·log formula: 22 vs
          // 13 instead of 42.7 vs 10.7, so giants don't visually
          // swallow the tail and label collisions resolve cheaply.
          const SIZE_MIN = isHugeL0 ? 6 : isDenseL0 ? 8 : 11;
          const SIZE_RANGE = isHugeL0 ? 7 : isDenseL0 ? 8 : 11;
          const sizeForN = SIZE_MIN
            + SIZE_RANGE * (Math.log(1 + n) / logMax);
          g.addNode(`__super__${lvl}__${key}`, {
            label: labelText,
            level: lvl,
            x: targetX * (isDenseL0 ? 0.35 : 0.18) + jx,
            y: targetY * (isDenseL0 ? 0.35 : 0.18) + jy,
            targetX, targetY,
            size: sizeForN,
            color: colorForLayer(bestLayer),
            layer: bestLayer,
            community: bestC,
            communityLabel: labelText,
            communitySummary: clusterSummary(bestC),
            memberCount: n,
            symbolCount: grp.symbolCount,
            labelSize: labelSizeForLevel,
            rank: rankByKey.get(key) || 0,
            denseOverview: isDenseL0,
            // Per-node forceLabel — top-K always show; rest defer to
            // labelDensity. Reducer-side hover override still wins, so
            // any cluster can be identified by mousing over it.
            forceLabel: labelTopK.has(key),
            l0: ancL0,
            l1: lvl >= 1 ? ancL1 : null,
            l2: lvl >= 2 ? ancL2 : null,
          });
        }
        return groups.size;
      }
      function buildSuperEdges(levelKey, lvl) {
        const agg = new Map();
        g.forEachEdge((eid, attrs, src, tgt) => {
          if (attrs.level !== 3) return;
          const sKey = g.getNodeAttribute(src, levelKey);
          const tKey = g.getNodeAttribute(tgt, levelKey);
          if (!sKey || !tKey || sKey === tKey) return;
          const a = sKey < tKey ? sKey : tKey;
          const b = sKey < tKey ? tKey : sKey;
          const key = `${a}${b}`;
          const cur = agg.get(key);
          if (cur) cur.count++;
          else agg.set(key, { a, b, count: 1 });
        });
        let added = 0;
        let values = [...agg.values()];
        if (lvl === 0 && values.length > L0_SUPER_EDGE_LIMIT) {
          values = values
            .sort((a, b) => b.count - a.count)
            .slice(0, L0_SUPER_EDGE_LIMIT);
        }
        for (const v of values) {
          const sId = `__super__${lvl}__${v.a}`;
          const tId = `__super__${lvl}__${v.b}`;
          if (!g.hasNode(sId) || !g.hasNode(tId)) continue;
          try {
            g.addEdgeWithKey(`__se__${lvl}__${v.a}__${v.b}`, sId, tId, {
              level: lvl,
              size: 0.6 + 0.5 * Math.log(1 + v.count),
              // Quiet default — edges fade into the background so
              // super-nodes own the eye. The edge reducer brightens
              // them when their endpoints are involved in a hover,
              // which is when the connections are actually relevant.
              color: "rgba(60,68,90,0.35)",
              aggregateCount: v.count,
            });
            added++;
          } catch (_) {}
        }
        return added;
      }
      const lodCount = {
        0: buildSupers("l0", 0),
        1: buildSupers("l1", 1),
        2: buildSupers("l2", 2),
      };
      buildSuperEdges("l0", 0);
      buildSuperEdges("l1", 1);
      buildSuperEdges("l2", 2);

      // Leaf-graph bbox — needed both by the SPREAD pass below and
      // by labelRadius() for the physics tick that runs alongside.
      // Computed once after super-node assembly and treated as
      // immutable for the lifetime of the viewer.
      let lminX = Infinity, lmaxX = -Infinity;
      let lminY = Infinity, lmaxY = -Infinity;
      g.forEachNode((id, attrs) => {
        if (attrs.level !== 3) return;
        if (attrs.x < lminX) lminX = attrs.x;
        if (attrs.x > lmaxX) lmaxX = attrs.x;
        if (attrs.y < lminY) lminY = attrs.y;
        if (attrs.y > lmaxY) lmaxY = attrs.y;
      });
      const leafCx = (lminX + lmaxX) / 2;
      const leafCy = (lminY + lmaxY) / 2;

      // ----- Label-overlap relaxation physics --------------------
      // Approximate each super-node as a circle whose radius covers
      // its node + the right-side label. When two circles overlap
      // we push them apart by an amount proportional to the overlap;
      // running this in a RAF tick gives the user a smooth settling
      // animation as the canvas transitions from "spawn" to "no
      // labels overlapping".
      const GRAPH_PER_PX = (() => {
        const ext = Math.max(lmaxX - lminX, lmaxY - lminY);
        return ext > 0 ? ext / 700 : 0.5;
      })();
      // labelRadius ≈ half the diagonal of the node-plus-label AABB.
      // The label paints to the right, so the AABB is asymmetric
      // (node radius on the left, label width + node radius on the
      // right); the diagonal gives us a single conservative number
      // that, when used as a soft-repulsion circle radius, keeps
      // labels well clear of one another regardless of orientation.
      function labelRadius(attrs) {
        const text = attrs.label || "";
        const labelPx = attrs.labelSize || 14;
        const widthPx = text.length * labelPx * 0.6 + 28;
        const heightPx = labelPx * 1.4 + 6;
        const sz = attrs.size || 5;
        const wG = sz + (widthPx + 8) * GRAPH_PER_PX;
        const hG = Math.max(sz, heightPx * 0.5 * GRAPH_PER_PX);
        // Half-diagonal of the (full-width × full-height) box,
        // scaled down a touch so we don't spread further than the
        // visual footprint actually requires.
        return Math.sqrt(wG * wG + hG * hG) * 0.55;
      }
      // Damping coefficient on the integrated step. Without this the
      // system is undamped — attraction overshoots equilibrium,
      // repulsion overshoots back, and the layout oscillates instead
      // of settling. 0.55 is heavy enough that motion converges
      // within ~2s for 20-30 super-nodes; light enough that the
      // spawn animation still reads as motion, not a snap.
      const PHYSICS_DAMPING = 0.55;
      function labelRelaxStep() {
        let totalMove = 0;
        for (const lvl of [0, 1, 2]) {
          const candidates = [];
          g.forEachNode((id, attrs) => {
            if (attrs.level === lvl) candidates.push({
              id,
              forceLabel: !!attrs.forceLabel,
              memberCount: attrs.memberCount || 0,
            });
          });
          if (candidates.length > RELAX_NODE_LIMIT) {
            candidates.sort((a, b) =>
              Number(b.forceLabel) - Number(a.forceLabel)
              || b.memberCount - a.memberCount
            );
          }
          const ids = candidates
            .slice(0, RELAX_NODE_LIMIT)
            .map(item => item.id);
          if (ids.length < 2) continue;
          const px = new Float64Array(ids.length);
          const py = new Float64Array(ids.length);
          const tx = new Float64Array(ids.length);
          const ty = new Float64Array(ids.length);
          const radii = new Float64Array(ids.length);
          for (let i = 0; i < ids.length; i++) {
            const a = g.getNodeAttributes(ids[i]);
            px[i] = a.x; py[i] = a.y;
            tx[i] = a.targetX !== undefined ? a.targetX : a.x;
            ty[i] = a.targetY !== undefined ? a.targetY : a.y;
            radii[i] = labelRadius(a);
          }
          // Accumulate force components first so attraction and
          // repulsion compose on the same step — applying them
          // sequentially to position let attraction pull nodes
          // back into overlap, which repulsion would then push out
          // again, producing the never-settling ping-pong.
          const dx = new Float64Array(ids.length);
          const dy = new Float64Array(ids.length);
          for (let i = 0; i < ids.length; i++) {
            dx[i] += (tx[i] - px[i]) * 0.040;
            dy[i] += (ty[i] - py[i]) * 0.040;
          }
          for (let i = 0; i < ids.length; i++) {
            for (let j = i + 1; j < ids.length; j++) {
              const ddx = px[i] - px[j];
              const ddy = py[i] - py[j];
              const d = Math.sqrt(ddx * ddx + ddy * ddy) || 0.0001;
              const minD = radii[i] + radii[j];
              if (d >= minD) continue;
              const overlap = minD - d;
              const push = overlap * 0.22;
              const ux = ddx / d, uy = ddy / d;
              dx[i] += ux * push; dy[i] += uy * push;
              dx[j] -= ux * push; dy[j] -= uy * push;
            }
          }
          for (let i = 0; i < ids.length; i++) {
            const stepX = dx[i] * PHYSICS_DAMPING;
            const stepY = dy[i] * PHYSICS_DAMPING;
            // Convergence cutoff: per-frame moves below 0.05 graph
            // units are imperceptible. Skip the write so totalMove
            // can fall under the idle threshold and the RAF loop
            // exits, killing the constant-motion bug.
            if (Math.abs(stepX) < 0.05 && Math.abs(stepY) < 0.05) continue;
            g.setNodeAttribute(ids[i], "x", px[i] + stepX);
            g.setNodeAttribute(ids[i], "y", py[i] + stepY);
            totalMove += Math.abs(stepX) + Math.abs(stepY);
          }
        }
        return totalMove;
      }
      let physicsRaf = null;
      let physicsIdleFrames = 0;
      function startPhysics() {
        if (physicsRaf !== null) return;
        physicsIdleFrames = 0;
        const tick = () => {
          const moved = labelRelaxStep();
          // Refresh while either physics is moving OR a level-
          // transition fade is in flight — without the second
          // clause, the alpha fade between levels stalls because
          // there's no other RAF source on the page during a
          // settled layout.
          const fadeActive = (performance.now() - levelTransitionStart)
                             < LEVEL_FADE_MS;
          if (moved > 0.001 || fadeActive) {
            physicsIdleFrames = 0;
            renderer.refresh();
          } else {
            physicsIdleFrames++;
          }
          // Stop after ~1s of stillness so we're not burning RAF
          // cycles when nothing is moving. Long enough that brief
          // overlap-resolutions don't kick the loop off prematurely.
          if (physicsIdleFrames > 60) {
            physicsRaf = null;
            // First time physics settles per page load, animate the
            // camera onto the L0 set's actual bbox. Beforehand
            // super-nodes are still spawning + spreading, and a fit
            // would lock onto the spawn cluster.
            if (!initialFitDone) {
              initialFitDone = true;
              fitCameraToLevel(currentLevel);
            }
            return;
          }
          physicsRaf = requestAnimationFrame(tick);
        };
        physicsRaf = requestAnimationFrame(tick);
      }

      // No pre-spread — super-nodes spawn at their member centroids
      // (clumped) and physics relaxation alone slides them outward.
      // The user watches the clusters move from where they spawn,
      // which is the requested behaviour.
      const SPREAD = { 0: 1.0, 1: 1.0, 2: 1.0 };
      g.forEachNode((id, attrs) => {
        const lvl = attrs.level;
        if (lvl === undefined || lvl === 3) return;
        const sx = SPREAD[lvl] || 1.0;
        if (sx === 1.0) return;
        const dx = (attrs.x - leafCx) * sx;
        const dy = (attrs.y - leafCy) * sx;
        g.setNodeAttribute(id, "x", leafCx + dx);
        g.setNodeAttribute(id, "y", leafCy + dy);
      });

      // Snapshot final sizes for reveal. Only the level the user lands on
      // (L0) needs size-zeroing — non-current levels are hidden by the
      // reducer regardless of their size attribute.
      const finalSize = new Map();
      g.forEachNode((id, attrs) => { finalSize.set(id, attrs.size); });
      g.forEachNode((id, attrs) => {
        if (attrs.level === 0) g.setNodeAttribute(id, "size", 0);
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
      let suppressNextStageClick = false;
      let wholeGraphMode = false;
      const hiddenLayers = new Set();
      const hiddenRelations = new Set();
      const HOVER_PUSH_RADIUS = 8;    // graph units
      const HOVER_PUSH_MAX = 3.5;     // graph units
      const HOVER_SIZE_MULT = 1.3;

      // layoutElapsed is filled in after the visible phase finishes; the
      // closure picks up whatever value it holds when baseStatus() is
      // called, so click handlers reading the status get the right text.
      let layoutElapsed = "...";
      const LEVEL_NAMES = ["communities", "regions", "modules", "leaves"];
      // Counts items the LOD reducer would paint right now — i.e., at
      // currentLevel and inside the active focus subtree if any. So
      // status reads what the user actually sees, not raw level totals.
      function visibleCount() {
        const fk = focusKey();
        const targetLevel = wholeGraphMode ? 3 : currentLevel;
        let c = 0;
        g.forEachNode((_id, attrs) => {
          if (attrs.level !== targetLevel) return;
          if (!wholeGraphMode && fk && attrs["l" + fk.level] !== fk.key) return;
          if (hiddenLayers.has(attrs.layer || "other")) return;
          c++;
        });
        return c;
      }
      const baseStatus = () => {
        const showing = visibleCount();
        if (wholeGraphMode) {
          return `Whole graph · ${showing.toLocaleString()} leaves · `
            + `FA2 ${layoutElapsed}s · scroll in for communities`;
        }
        const where = `${showing.toLocaleString()} ${LEVEL_NAMES[currentLevel]}`;
        // Breadcrumb of focused ancestors — rightmost is the deepest.
        const trail = focusPath.length > 0
          ? " · " + focusPath
              .map(f => (f.key.split("/").pop() || f.key))
              .join(" › ")
          : "";
        const hint = focusPath.length > 0
          ? " · click empty to back out"
          : " · scroll to zoom";
        const scaleHint = currentLevel === 0 && lodCount[0] >= L0_DENSE_COUNT
          ? " · high-scale overview"
          : "";
        return `L${currentLevel}${trail} · ${where} · FA2 ${layoutElapsed}s${scaleHint}${hint}`;
      };
      let inspectorPinned = false;
      function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, ch => ({
          "&": "&amp;", "<": "&lt;", ">": "&gt;",
          '"': "&quot;", "'": "&#39;",
        }[ch]));
      }
      function compactLabel(value) {
        const s = String(value || "");
        return s.includes(" · ") ? s.split(" · ")[0] : s;
      }
      function relationLabel(item) {
        if (!item || !item.relation) return "";
        const arrow = item.direction === "in" ? "←" : "→";
        return `${arrow} ${item.relation}`;
      }
      function updateInspector(node = null) {
        const el = document.getElementById("inspector-body");
        if (!node || !g.hasNode(node)) {
          el.className = "inspector-empty";
          el.textContent = "No selection";
          return;
        }
        const attrs = g.getNodeAttributes(node);
        const isLeaf = attrs.level === 3;
        const visualKind = attrs.visualKind || attrs.fileType || "symbol";
        const type = isLeaf ? visualKind : LEVEL_NAMES[attrs.level] || "region";
        const degree = g.degree(node);
        const rows = [
          ["type", type],
          ["layer", attrs.layer || "other"],
          ["region", attrs.communityLabel || "unlabeled"],
        ];
        if (isLeaf) {
          if (attrs.memberCount && attrs.memberCount > 1) rows.push(["members", attrs.memberCount]);
          rows.push(["degree", degree]);
          if (attrs.fileType) rows.push(["kind", attrs.fileType]);
          if (attrs.sourceFile) rows.push(["file", attrs.sourceFile]);
          if (attrs.sourceLocation) rows.push(["loc", attrs.sourceLocation]);
        } else {
          rows.push(["leaves", attrs.memberCount || 0]);
          if (attrs.symbolCount) rows.push(["members", attrs.symbolCount]);
        }
        const neighbors = (isLeaf && leafAdj.has(node)
            ? leafAdj.get(node)
            : g.neighbors(node).map(nid => ({ id: nid, relation: "", direction: "" }))
          )
          .slice(0, 8)
          .map(item => ({
            id: item.id,
            relation: relationLabel(item),
            label: compactLabel(g.getNodeAttribute(item.id, "label") || item.id),
          }));
        const symbols = Array.isArray(attrs.symbols) ? attrs.symbols : [];
        const visibleSymbols = symbols.slice(0, 12);
        const symbolList = isLeaf && visibleSymbols.length && attrs.memberCount > 1
          ? `<div class="inspector-symbols">`
            + visibleSymbols.map(s =>
                `<div class="inspector-symbol">${escapeHtml(s.label || s.id || "")}</div>`
              ).join("")
            + (attrs.memberCount > visibleSymbols.length
                ? `<div class="inspector-symbol-more">+${escapeHtml(attrs.memberCount - visibleSymbols.length)} more</div>`
                : "")
            + `</div>`
          : "";
        const summary = isLeaf ? "" : attrs.communitySummary || "";
        el.className = "";
        el.innerHTML =
          `<div class="inspector-title">${escapeHtml(attrs.label || node)}</div>`
          + rows.map(([k, v]) =>
              `<div class="inspector-row">`
              + `<span class="inspector-key">${escapeHtml(k)}</span>`
              + `<span class="inspector-value">${escapeHtml(v)}</span>`
              + `</div>`
            ).join("")
          + (summary
              ? `<div class="inspector-summary">${escapeHtml(summary)}</div>`
              : "")
          + symbolList
          + (neighbors.length
              ? `<div class="inspector-neighbors">`
                + neighbors.map(n =>
                    `<button class="neighbor-pill" type="button" data-node="${escapeHtml(n.id)}">`
                    + (n.relation
                        ? `<span class="neighbor-rel">${escapeHtml(n.relation)}</span> `
                        : "")
                    + `${escapeHtml(n.label)}</button>`
                  ).join("")
                + `</div>`
              : "");
        el.querySelectorAll(".neighbor-pill[data-node]").forEach(btn => {
          btn.addEventListener("click", ev => {
            ev.stopPropagation();
            jumpToNode(btn.dataset.node);
          });
        });
      }
      function focusDisplayName(focusItem) {
        const key = focusItem?.key || "";
        if (focusItem?.level === 0 && key.startsWith("comm:")) {
          const cid = Number(key.slice(5));
          return compactLabel(clusterLabel(cid));
        }
        return compactLabel(key.split("/").pop() || key || "region");
      }
      function renderBreadcrumb() {
        const el = document.getElementById("breadcrumb");
        const backBtn = document.getElementById("nav-back");
        const overviewBtn = document.getElementById("nav-overview");
        const wholeBtn = document.getElementById("nav-whole");
        if (!el || !backBtn) return;
        backBtn.disabled =
          !wholeGraphMode && currentLevel === 0 && focusPath.length === 0 && !focusedNode;
        if (overviewBtn) overviewBtn.classList.toggle(
          "active", !wholeGraphMode && currentLevel === 0 && focusPath.length === 0
        );
        if (wholeBtn) wholeBtn.classList.toggle("active", wholeGraphMode);
        const pieces = [
          `<button class="crumb" type="button" data-root="1">Overview</button>`,
        ];
        if (wholeGraphMode) {
          pieces.push(`<span class="crumb-sep">/</span>`);
          pieces.push(`<button class="crumb" type="button" data-whole="1">Whole graph</button>`);
        }
        focusPath.forEach((item, idx) => {
          pieces.push(`<span class="crumb-sep">/</span>`);
          pieces.push(
            `<button class="crumb" type="button" data-idx="${idx}">`
            + `${escapeHtml(focusDisplayName(item))}`
            + `</button>`
          );
        });
        if (focusedNode && g.hasNode(focusedNode)) {
          pieces.push(`<span class="crumb-sep">/</span>`);
          pieces.push(
            `<button class="crumb" type="button" data-focus="1">`
            + `${escapeHtml(compactLabel(g.getNodeAttribute(focusedNode, "label") || focusedNode))}`
            + `</button>`
          );
        }
        el.innerHTML = pieces.join("");
        const root = el.querySelector("[data-root]");
        if (root) root.addEventListener("click", clearToOverview);
        const whole = el.querySelector("[data-whole]");
        if (whole) whole.addEventListener("click", enterWholeGraph);
        el.querySelectorAll("[data-idx]").forEach(btn => {
          btn.addEventListener("click", () => {
            const idx = Number(btn.dataset.idx);
            const item = focusPath[idx];
            if (!item) return;
            focusPath = focusPath.slice(0, idx + 1);
            focusedNode = null;
            neighborSet = new Set();
            inspectorPinned = false;
            updateInspector(null);
            setLevel(Math.min(3, item.level + 1), {
              anchorRatio: currentRatio || lodAnchorRatio,
              lockMs: 420,
            });
          });
        });
      }

      // Stroke-outlined label: dark stroke first, light fill on top.
      // Reads against any background — node fills, edges, hover
      // highlights, even Sigma's default lighter hover canvas — and
      // doesn't depend on a backdrop rectangle that can land on the
      // wrong z-order. Hover variant boosts size 15% so the active
      // label visibly dominates without needing a separate backdrop.
      const drawNodeLabelOutlined = (context, data, settings, sizeMul) => {
        if (!data.label || data.hidden) return;
        const mul = sizeMul || 1;
        const baseSize = (data.labelSize || settings.labelSize || 13) * mul;
        const weight = data.labelWeight || settings.labelWeight || "600";
        const font = settings.labelFont
          || "system-ui, -apple-system, sans-serif";
        context.font = `${weight} ${baseSize}px ${font}`;
        context.textBaseline = "middle";
        context.textAlign = "left";
        const x = data.x + data.size + 4;
        const y = data.y;
        // Heavy dark stroke around the text — reads against any
        // background colour, including Sigma's default white hover
        // overlay (which previously rendered white-on-white).
        context.lineWidth = mul > 1 ? 4 : 3;
        context.lineJoin = "round";
        context.miterLimit = 2;
        context.strokeStyle = "rgba(8,10,18,0.92)";
        context.strokeText(data.label, x, y);
        context.fillStyle =
          (settings.labelColor && settings.labelColor.color) || "#f1f3f8";
        context.fillText(data.label, x, y);
      };
      // Sigma paints labels on the labels canvas AND hover labels on
      // the hoverNodes canvas — both stay visible, so without this
      // skip the smaller regular label bleeds through under the
      // bigger hover label and reads as jumbled doubled text.
      const drawNodeLabel = (ctx, d, s) => {
        if (d.__hovered) return;
        drawNodeLabelOutlined(ctx, d, s, 1);
      };
      const drawNodeHover = (ctx, d, s) => drawNodeLabelOutlined(ctx, d, s, 1.15);

      const renderer = new Sigma(g, document.getElementById("graph"), {
        // Keep overview labels selective. Dense L0 graphs explicitly
        // label only the dominant communities; Sigma can opportunistically
        // place the rest when there is room.
        labelDensity: 0.08, labelGridCellSize: 160, minCameraRatio: 0.04,
        maxCameraRatio: 30, defaultNodeColor: "#6b7280",
        defaultEdgeColor: "rgba(107,114,128,0.3)",
        renderEdgeLabels: false,
        enableEdgeEvents: false,
        // Wheel zoom — Sigma's default 1.7× per click felt jumpy with
        // the LOD bands clustered close (1.5 / 0.7 / 0.3). 1.22× takes
        // ~3 clicks to cross a band so the smooth crossfade has time
        // to read; zoomDuration extends the animation so each click
        // glides instead of snapping.
        zoomingRatio: 1.22,
        zoomDuration: 320,
        // Brighter labels with weight so super-nodes read against the
        // #0f0f1a body. Per-node labelSize on super-nodes overrides
        // this default for L0/L1; L3 leaves use it as the floor.
        labelColor: { color: "#f1f3f8" },
        labelWeight: "600",
        labelSize: 13,
        labelFont: "system-ui, -apple-system, sans-serif",
        // Sigma 3.0.0 setting names — labelRenderer/hoverRenderer
        // were Sigma 2 and silently ignored here, which let the
        // default white-on-white hover overlay clobber labels.
        defaultDrawNodeLabel: drawNodeLabel,
        defaultDrawNodeHover: drawNodeHover,
        nodeReducer: (node, data) => {
          // Smooth LOD blend — alpha is interpolated through level
          // boundaries (smoothstep) so wheeling produces a continuous
          // crossfade between adjacent layers rather than a snap.
          const a = smoothAlphas()[data.level];
          if (a <= 0.01) return { ...data, hidden: true };
          // Drill-down focus: only render descendants of the deepest
          // focus item. Each super-node + leaf carries ancestor keys at
          // every level above its own, so this is a single attribute
          // compare regardless of depth.
          const fk = focusKey();
          if (!wholeGraphMode && fk && data["l" + fk.level] !== fk.key) {
            return { ...data, hidden: true };
          }
          if (hiddenLayers.has(data.layer || "other")) {
            return { ...data, hidden: true };
          }
          let out = a < 0.999
            ? { ...data, color: multiplyAlpha(data.color, a) }
            : data;
          // Focus dimming (click) layers first.
          if (focusedNode) {
            if (node === focusedNode || neighborSet.has(node)) {
              out = { ...out, zIndex: 1 };
            } else {
              out = { ...out, color: "#2a2a3e", label: "", zIndex: 0 };
            }
          }
          // Hover effects: grow hovered, push nearby away. Hovered
          // super-nodes get a subtle pulse + 15% bigger label so the
          // canvas feels live and the label always reads on top.
          if (hoveredNode) {
            if (node === hoveredNode) {
              const pulse = 1 + 0.06 * Math.sin(performance.now() / 220);
              out = {
                ...out,
                size: (out.size || data.size) * HOVER_SIZE_MULT * pulse,
                labelSize:
                  (out.labelSize || data.labelSize || 13) * 1.15,
                forceLabel: true,
                zIndex: 3,
                // Marker the label drawer reads to skip painting the
                // regular (un-grown) label for this node — only the
                // hover renderer paints it during hover.
                __hovered: true,
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
          // forceLabel is set per-node on the top-K super-nodes in
          // buildSupers; the rest defer to labelDensity so wide-extent
          // graphs don't paint 21 labels on top of each other. Hover
          // branch above already force-shows whichever node is hovered.
          if (!wholeGraphMode && data.level === 0
              && lodCount[0] >= L0_DENSE_COUNT
              && !data.forceLabel
              && node !== hoveredNode && node !== focusedNode) {
            out = { ...out, label: "", forceLabel: false };
          }
          if (wholeGraphMode && node !== hoveredNode && node !== focusedNode) {
            return {
              ...out,
              label: "",
              forceLabel: false,
              size: Math.min(out.size || data.size || 2.4, 2.4),
            };
          }
          return out;
        },
        edgeReducer: (edge, data) => {
          // Same smoothstep crossfade as nodes so super-edges fade
          // alongside super-nodes through the threshold.
          const a = smoothAlphas()[data.level];
          if (a <= 0.01) return { ...data, hidden: true };
          // Same drill-down filter as nodeReducer: hide edges that
          // would connect across the focus boundary.
          const fk = focusKey();
          if (!wholeGraphMode && fk) {
            const ext = g.extremities(edge);
            const fld = "l" + fk.level;
            const sa = g.getNodeAttribute(ext[0], fld);
            const ta = g.getNodeAttribute(ext[1], fld);
            if (sa !== fk.key || ta !== fk.key) {
              return { ...data, hidden: true };
            }
          }
          const ext = g.extremities(edge);
          const sLayer = g.getNodeAttribute(ext[0], "layer") || "other";
          const tLayer = g.getNodeAttribute(ext[1], "layer") || "other";
          if (hiddenLayers.has(sLayer) || hiddenLayers.has(tLayer)) {
            return { ...data, hidden: true };
          }
          if (hiddenRelations.has(data.relation || "related")) {
            return { ...data, hidden: true };
          }
          let out = a < 0.999
            ? { ...data, color: multiplyAlpha(data.color, a) }
            : data;
          // Hover: any super-edge incident to the hovered cluster
          // gets boosted brightness + thickness so the user can
          // trace its connections at a glance. Edges to other
          // clusters stay at their dim default.
          if (hoveredNode) {
            if (ext[0] === hoveredNode || ext[1] === hoveredNode) {
              return {
                ...out,
                color: "rgba(220,228,250,0.92)",
                size: (out.size || data.size) * 1.8,
                zIndex: 2,
              };
            }
          }
          if (wholeGraphMode) {
            return {
              ...out,
              color: multiplyAlpha(out.color, 0.45),
              size: Math.min(out.size || data.size || 0.18, 0.18),
              zIndex: 0,
            };
          }
          if (!focusedNode) return out;
          if (ext[0] === focusedNode || ext[1] === focusedNode) {
            return { ...out, size: 0.8, zIndex: 1 };
          }
          return { ...out, color: "rgba(40,40,60,0.2)", zIndex: 0 };
        },
      });

      // ----- LOD: camera-ratio ladder -------------------------------
      // Sigma's camera ratio decreases as the user zooms in. Instead
      // of recomputing viewport bboxes on every camera tick, each level
      // records the ratio where the user entered it. Wheel-in past the
      // lower threshold descends one level; wheel-out past the upper
      // threshold ascends. This gives a predictable, GitNexus-like
      // ladder: smooth crossfades, no surprise size-based jumps.
      const camera = renderer.getCamera();
      // Initial camera: Sigma's default ratio=1.0 fits the whole
      // graph extent. Super-nodes spawn near origin with jitter and
      // physics spreads them toward leaf-centroid targets — fitting
      // BEFORE physics ran would zoom into the spawn cluster and
      // hide the spread animation. fitCameraToLevel(0) fires once
      // physics first settles (see startPhysics tick).
      camera.setState({ x: 0.5, y: 0.5, ratio: 1.0 });
      currentRatio = 1.0;
      currentLevel = 0;
      let lodAnchorRatio = 1.0;
      let lodLockedUntil = 0;
      const LOD_ZOOM_IN_RATIO = 0.52;
      const LOD_ZOOM_OUT_RATIO = 1.85;
      // Fit camera so the active level's super-node bbox occupies
      // ~75% of the viewport. Closes #79 — the previous fixed
      // ratio=1.8 left a tiny L0 blob floating in 92% empty canvas
      // when the full graph extent (driven by L3 leaves) is huge.
      function fitCameraToLevel(targetLvl, opts = {}) {
        let mnx = Infinity, mxx = -Infinity, mny = Infinity, mxy = -Infinity;
        let count = 0;
        g.forEachNode((id, attrs) => {
          if (attrs.level !== targetLvl) return;
          const norm = renderer.normalizationFunction(
            { x: attrs.x, y: attrs.y },
          );
          if (norm.x < mnx) mnx = norm.x;
          if (norm.x > mxx) mxx = norm.x;
          if (norm.y < mny) mny = norm.y;
          if (norm.y > mxy) mxy = norm.y;
          count++;
        });
        if (count < 1) return;
        const cx = (mnx + mxx) / 2;
        const cy = (mny + mxy) / 2;
        const span = Math.max(mxx - mnx, mxy - mny, 0.05);
        const ratio = Math.min(30, Math.max(0.1, span / 0.75));
        lodAnchorRatio = ratio;
        lodLockedUntil = performance.now() + (opts.lockMs || 520);
        camera.animate(
          { x: cx, y: cy, ratio },
          { duration: opts.duration || 500 },
        );
        return ratio;
      }
      let initialFitDone = false;
      // Debug hooks — expose graph + renderer so devtools can inspect
      // node attributes, drive the camera, or smoke-test LOD swaps
      // without monkey-patching. Cheap and useful.
      window.__prismGraph = g;
      window.__prismSigma = renderer;
      function reconcileLevelWithZoom() {
        if (performance.now() < lodLockedUntil) return;
        const ratio = currentRatio || lodAnchorRatio;
        if (wholeGraphMode) {
          if (ratio < lodAnchorRatio * LOD_ZOOM_IN_RATIO) {
            wholeGraphMode = false;
            setLevel(0, { anchorRatio: ratio, lockMs: 420 });
          }
          return;
        }
        let next = currentLevel;
        if (ratio < lodAnchorRatio * LOD_ZOOM_IN_RATIO && currentLevel < 3) {
          next = currentLevel + 1;
        } else if (
          ratio > lodAnchorRatio * LOD_ZOOM_OUT_RATIO
          && currentLevel > 0
        ) {
          next = currentLevel - 1;
        } else if (
          ratio > lodAnchorRatio * LOD_ZOOM_OUT_RATIO
          && currentLevel === 0
          && focusPath.length === 0
        ) {
          enterWholeGraph({ anchorRatio: ratio, lockMs: 420, fit: false });
          return;
        }
        if (next === currentLevel) return;
        while (focusPath.length > 0
               && focusPath[focusPath.length - 1].level >= next) {
          focusPath.pop();
        }
        setLevel(next, { anchorRatio: ratio });
      }

      // setLevel — single entry point for level changes. Captures
      // the previous level for the fade, runs the side effects
      // (status text, legend rebuild, physics nudge), and refreshes.
      function setLevel(next, opts = {}) {
        next = Math.max(0, Math.min(3, next));
        if (!opts.keepWhole) wholeGraphMode = false;
        if (next === currentLevel) return;
        prevLevel = currentLevel;
        currentLevel = next;
        lodAnchorRatio = opts.anchorRatio || currentRatio || lodAnchorRatio;
        if (opts.lockMs) lodLockedUntil = performance.now() + opts.lockMs;
        levelTransitionStart = performance.now();
        if (focusedNode) {
          focusedNode = null;
          neighborSet = new Set();
        }
        statusEl.textContent = baseStatus();
        rebuildLegend();
        renderBreadcrumb();
        renderer.refresh();
        startPhysics();
      }

      function clearToOverview() {
        wholeGraphMode = false;
        focusedNode = null;
        neighborSet = new Set();
        inspectorPinned = false;
        updateInspector(null);
        focusPath = [];
        if (currentLevel !== 0) {
          setLevel(0, { anchorRatio: currentRatio, lockMs: 650 });
        } else {
          statusEl.textContent = baseStatus();
          rebuildLegend();
          renderBreadcrumb();
          renderer.refresh();
          startPhysics();
        }
        fitCameraToLevel(0, { duration: 650, lockMs: 720 });
      }

      function backOneLevel() {
        if (wholeGraphMode) {
          clearToOverview();
          return;
        }
        if (focusedNode) {
          focusedNode = null;
          neighborSet = new Set();
          inspectorPinned = false;
          updateInspector(null);
        }
        if (currentLevel <= 0 && focusPath.length === 0) {
          clearToOverview();
          return;
        }
        const next = Math.max(0, currentLevel - 1);
        while (focusPath.length > 0
               && focusPath[focusPath.length - 1].level >= next) {
          focusPath.pop();
        }
        if (next === 0) {
          clearToOverview();
        } else {
          setLevel(next, { anchorRatio: currentRatio, lockMs: 420 });
        }
      }

      function setupNavigationControls() {
        const backBtn = document.getElementById("nav-back");
        const overviewBtn = document.getElementById("nav-overview");
        const wholeBtn = document.getElementById("nav-whole");
        if (backBtn) backBtn.addEventListener("click", backOneLevel);
        if (overviewBtn) overviewBtn.addEventListener("click", clearToOverview);
        if (wholeBtn) wholeBtn.addEventListener("click", () => enterWholeGraph());
        renderBreadcrumb();
      }
      window.__prismJumpToNode = jumpToNode;

      function enterWholeGraph(opts = {}) {
        wholeGraphMode = true;
        focusPath = [];
        focusedNode = null;
        neighborSet = new Set();
        inspectorPinned = false;
        updateInspector(null);
        if (currentLevel !== 3) {
          setLevel(3, {
            anchorRatio: opts.anchorRatio || currentRatio || lodAnchorRatio,
            lockMs: opts.lockMs || 650,
            keepWhole: true,
          });
        } else {
          lodAnchorRatio = opts.anchorRatio || currentRatio || lodAnchorRatio;
          lodLockedUntil = performance.now() + (opts.lockMs || 650);
          statusEl.textContent = baseStatus();
          rebuildLegend();
          renderBreadcrumb();
          renderer.refresh();
        }
        if (opts.fit !== false) {
          fitCameraToLevel(3, { duration: 700, lockMs: 760 });
        }
      }

      camera.on("updated", () => {
        currentRatio = camera.getState().ratio;
        reconcileLevelWithZoom();
        renderer.refresh();
      });

      // RAF loop that re-renders while a node is hovered so the
      // pulse + label-grow are animated, then idles itself out.
      // Cheap: one render/frame, only while the user's pointer is
      // over a node.
      let pulseRaf = null;
      function startPulseLoop() {
        if (pulseRaf !== null) return;
        const tick = () => {
          if (!hoveredNode) { pulseRaf = null; return; }
          renderer.refresh();
          pulseRaf = requestAnimationFrame(tick);
        };
        pulseRaf = requestAnimationFrame(tick);
      }

      // Hover enter/leave: cache the hovered node's graph-space
      // position once so the reducer doesn't re-query per-node.
      renderer.on("enterNode", ({ node }) => {
        hoveredNode = node;
        hoveredX = g.getNodeAttribute(node, "x");
        hoveredY = g.getNodeAttribute(node, "y");
        document.body.style.cursor = "pointer";
        if (!inspectorPinned) updateInspector(node);
        startPulseLoop();
      });
      renderer.on("leaveNode", () => {
        hoveredNode = null;
        document.body.style.cursor = "";
        if (!inspectorPinned) updateInspector(null);
        renderer.refresh();
      });
      renderer.on("clickNode", ({ node }) => {
        suppressNextStageClick = true;
        setTimeout(() => { suppressNextStageClick = false; }, 0);
        const attrs = g.getNodeAttributes(node);
        inspectorPinned = true;
        updateInspector(node);
        // Click a super-node → push it onto the focus stack so the
        // next level only paints its descendants, jump to that level
        // (no ratio threshold races) and pan the camera onto it.
        if (attrs.level !== undefined && attrs.level < 3) {
          const tgtLvl = attrs.level + 1;
          const ownKey = attrs["l" + attrs.level];
          if (ownKey) {
            focusPath.push({ level: attrs.level, key: ownKey });
          }
          const tgtRatio = Math.max(
            0.04,
            Math.min(30, (currentRatio || lodAnchorRatio) * 0.58),
          );
          setLevel(tgtLvl, { anchorRatio: tgtRatio, lockMs: 700 });
          // Pan + zoom onto the clicked super-node. Sigma's camera
          // state x/y is in normalized [0,1] framed-graph space, not
          // graph coords — pass through normalizationFunction or the
          // camera animates off-canvas and the viewer goes blank.
          const target = renderer.normalizationFunction({
            x: attrs.x, y: attrs.y,
          });
          const summary = attrs.communitySummary
            ? ` · ${attrs.communitySummary}`
            : "";
          statusEl.textContent = `${attrs.label} · `
            + `${(attrs.memberCount || 0).toLocaleString()} leaves`
            + (attrs.symbolCount ? ` · ${attrs.symbolCount.toLocaleString()} members` : "")
            + ` · layer ${attrs.layer || "other"}${summary}`;
          camera.animate(
            { x: target.x, y: target.y, ratio: tgtRatio },
            { duration: 600 }
          );
          return;
        }
        // L3 leaf — preserve the existing focus / dim-non-neighbors flow.
        focusedNode = node;
        neighborSet = new Set(g.neighbors(node));
        statusEl.textContent = `${attrs.label} `
          + `(${attrs.visualKind || attrs.fileType || "leaf"}, `
          + `${(attrs.memberCount || 1).toLocaleString()} members, `
          + `region: ${attrs.communityLabel || "unlabeled region"}, `
          + `layer ${attrs.layer || "other"}, `
          + `degree ${g.degree(node)}) — `
          + `click empty space to clear focus`;
        renderBreadcrumb();
        renderer.refresh();
      });
      // Click on empty space backs all the way out — clears the
      // focus stack, drops the leaf-focus dim-highlight, resets
      // currentLevel to L0, and recenters the overview.
      renderer.on("clickStage", () => {
        if (suppressNextStageClick) {
          suppressNextStageClick = false;
          return;
        }
        const hadFocus = !!focusedNode || focusPath.length > 0;
        const wasDeep = currentLevel > 0;
        if (!hadFocus && !wasDeep) return;
        clearToOverview();
      });

      function focusPathForNode(attrs) {
        const out = [];
        const level = attrs.level === undefined ? 3 : attrs.level;
        for (let lvl = 0; lvl < level; lvl++) {
          const key = attrs["l" + lvl];
          if (key) out.push({ level: lvl, key });
        }
        return out;
      }
      function ratioForJumpLevel(level) {
        const base = Math.max(currentRatio || lodAnchorRatio || 1, 0.45);
        if (level <= 0) return Math.min(30, base);
        return Math.max(0.04, Math.min(30, base * Math.pow(0.58, level)));
      }
      function jumpToNode(node) {
        if (!g.hasNode(node)) return;
        const attrs = g.getNodeAttributes(node);
        const level = attrs.level === undefined ? 3 : attrs.level;
        focusPath = focusPathForNode(attrs);
        focusedNode = level === 3 ? node : null;
        neighborSet = level === 3 ? new Set(g.neighbors(node)) : new Set();
        inspectorPinned = true;
        updateInspector(node);
        const target = renderer.normalizationFunction({
          x: attrs.x, y: attrs.y,
        });
        const ratio = ratioForJumpLevel(level);
        setLevel(level, { anchorRatio: ratio, lockMs: 720 });
        camera.animate(
          { x: target.x, y: target.y, ratio },
          { duration: 680 },
        );
        statusEl.textContent = `${attrs.label || node} · `
          + `${LEVEL_NAMES[level] || "leaf"} · layer ${attrs.layer || "other"}`;
        renderBreadcrumb();
        renderer.refresh();
      }
      function setupSearch() {
        const input = document.getElementById("graph-search");
        const resultsEl = document.getElementById("search-results");
        if (!input || !resultsEl) return;
        const index = [];
        g.forEachNode((id, attrs) => {
          const symbolText = Array.isArray(attrs.symbols)
            ? attrs.symbols.map(s => [s.label || "", s.source_file || ""].join(" ")).join(" ")
            : "";
          index.push({
            id,
            label: attrs.label || id,
            level: attrs.level === undefined ? 3 : attrs.level,
            layer: attrs.layer || "other",
            region: attrs.communityLabel || "",
            count: attrs.memberCount || g.degree(id) || 0,
            text: [
              attrs.label || id,
              attrs.layer || "",
              attrs.communityLabel || "",
              attrs.communitySummary || "",
              attrs.sourceFile || "",
              attrs.sourceLocation || "",
              attrs.fileType || "",
              attrs.visualKind || "",
              symbolText,
            ].join(" ").toLowerCase(),
          });
        });
        const renderResults = () => {
          const q = input.value.trim().toLowerCase();
          if (q.length < 2) {
            resultsEl.style.display = "none";
            resultsEl.innerHTML = "";
            return;
          }
          const hits = index
            .filter(item => item.text.includes(q))
            .sort((a, b) => {
              const al = a.label.toLowerCase();
              const bl = b.label.toLowerCase();
              const ap = al.startsWith(q) ? 0 : al.includes(q) ? 1 : 2;
              const bp = bl.startsWith(q) ? 0 : bl.includes(q) ? 1 : 2;
              return ap - bp || a.level - b.level || b.count - a.count;
            })
            .slice(0, 9);
          if (!hits.length) {
            resultsEl.style.display = "block";
            resultsEl.innerHTML =
              `<div class="search-result"><div class="search-meta">No matches</div></div>`;
            return;
          }
          resultsEl.style.display = "block";
          resultsEl.innerHTML = hits.map((item, idx) =>
            `<div class="search-result" data-idx="${idx}">`
            + `<div class="search-title">${escapeHtml(item.label)}</div>`
            + `<div class="search-meta">L${item.level} ${escapeHtml(LEVEL_NAMES[item.level] || "leaf")}`
            + ` · ${escapeHtml(item.layer)} · ${escapeHtml(compactLabel(item.region))}</div>`
            + `</div>`
          ).join("");
          resultsEl.querySelectorAll(".search-result[data-idx]").forEach(el => {
            el.addEventListener("click", () => {
              const hit = hits[Number(el.dataset.idx)];
              if (!hit) return;
              input.value = hit.label;
              resultsEl.style.display = "none";
              jumpToNode(hit.id);
            });
          });
        };
        input.addEventListener("input", renderResults);
        input.addEventListener("keydown", ev => {
          if (ev.key !== "Enter") return;
          const first = resultsEl.querySelector(".search-result[data-idx]");
          if (first) first.click();
        });
      }
      function setupLayerFilters() {
        const el = document.getElementById("layer-filters");
        if (!el) return;
        const counts = new Map();
        g.forEachNode((_id, attrs) => {
          if (attrs.level !== 3) return;
          const layer = attrs.layer || "other";
          counts.set(layer, (counts.get(layer) || 0) + 1);
        });
        const order = Object.keys(LAYER_COLORS)
          .filter(layer => counts.has(layer))
          .concat(
            [...counts.keys()]
              .filter(layer => !Object.prototype.hasOwnProperty.call(LAYER_COLORS, layer))
              .sort()
          );
        el.innerHTML = order.map(layer =>
          `<button class="filter-chip layer-chip" type="button" data-layer="${escapeHtml(layer)}" `
          + `title="${escapeHtml(counts.get(layer) || 0)} leaves">`
          + `<span class="layer-chip-dot" style="background:${colorForLayer(layer)}"></span>`
          + `${escapeHtml(layer)}`
          + `</button>`
        ).join("");
        el.querySelectorAll(".layer-chip").forEach(btn => {
          btn.addEventListener("click", () => {
            const layer = btn.dataset.layer || "other";
            if (hiddenLayers.has(layer)) {
              hiddenLayers.delete(layer);
              btn.classList.remove("off");
            } else {
              hiddenLayers.add(layer);
              btn.classList.add("off");
            }
            if (focusedNode && hiddenLayers.has(g.getNodeAttribute(focusedNode, "layer") || "other")) {
              focusedNode = null;
              neighborSet = new Set();
            }
            const filters = hiddenLayers.size + hiddenRelations.size;
            statusEl.textContent = baseStatus()
              + (filters ? ` · ${filters} filters` : "");
            rebuildLegend();
            renderer.refresh();
          });
        });
      }

      function setupRelationFilters() {
        const el = document.getElementById("relation-filters");
        if (!el) return;
        const counts = new Map();
        g.forEachEdge((_eid, attrs) => {
          if (attrs.level !== 3) return;
          const relation = attrs.relation || "related";
          counts.set(relation, (counts.get(relation) || 0) + 1);
        });
        const relations = [...counts.entries()]
          .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
          .slice(0, 8);
        el.innerHTML = relations.map(([relation, count]) =>
          `<button class="filter-chip relation-chip" type="button" data-relation="${escapeHtml(relation)}" `
          + `title="${escapeHtml(count)} edges">`
          + `<span class="relation-chip-dot">edge</span> `
          + `${escapeHtml(relation)}`
          + `</button>`
        ).join("");
        el.querySelectorAll(".relation-chip").forEach(btn => {
          btn.addEventListener("click", () => {
            const relation = btn.dataset.relation || "related";
            if (hiddenRelations.has(relation)) {
              hiddenRelations.delete(relation);
              btn.classList.remove("off");
            } else {
              hiddenRelations.add(relation);
              btn.classList.add("off");
            }
            const filters = hiddenLayers.size + hiddenRelations.size;
            statusEl.textContent = baseStatus()
              + (filters ? ` · ${filters} filters` : "");
            renderer.refresh();
          });
        });
      }

      // --- Legend / categories sidebar ----------------------------
      // Level-aware: at L0/L1/L2 it lists super-nodes ranked by member
      // count; at L3 it lists Leiden communities. Click an item to dim
      // its members from the canvas. Truncates the first dotted segment
      // of community labels per #68 proposal #6 — "express web api · be"
      // reads as "express web api" with the full string in tooltip.
      function truncateLabel(lbl) {
        if (!lbl) return "(unlabeled)";
        const dot = lbl.indexOf(" · ");
        return dot > 0 ? lbl.substring(0, dot) : lbl;
      }
      function rebuildLegend() {
        const listEl = document.getElementById("legend-list");
        listEl.innerHTML = "";
        const fk = focusKey();
        const inFocus = (attrs) =>
          (!fk || attrs["l" + fk.level] === fk.key)
          && !hiddenLayers.has(attrs.layer || "other");
        let items = [];
        if (currentLevel < 3) {
          g.forEachNode((id, attrs) => {
            if (attrs.level !== currentLevel) return;
            if (!inFocus(attrs)) return;
            items.push({
              kind: "super", id,
              label: attrs.label,
              color: attrs.color,
              count: attrs.memberCount || 1,
            });
          });
        } else {
          const counts = new Map();
          const layers = new Map();
          g.forEachNode((_n, attrs) => {
            if (attrs.level !== 3) return;
            if (!inFocus(attrs)) return;
            const c = attrs.community;
            if (c === null || c === undefined) return;
            counts.set(c, (counts.get(c) || 0) + 1);
            if (!layers.has(c)) layers.set(c, new Map());
            const layerCounts = layers.get(c);
            const layer = attrs.layer || "other";
            layerCounts.set(layer, (layerCounts.get(layer) || 0) + 1);
          });
          items = [...counts.entries()].map(([cid, n]) => ({
            kind: "community", cid,
            label: clusterLabel(cid),
            color: colorForLayer(
              [...(layers.get(cid) || new Map()).entries()]
                .sort((a, b) => b[1] - a[1])[0]?.[0] || "other"
            ),
            count: n,
          }));
        }
        items.sort((a, b) => b.count - a.count);

        for (const item of items) {
          const div = document.createElement("div");
          div.className = "legend-item";
          const display = truncateLabel(item.label);
          const fullLabel = (item.label || "").replace(/"/g, "&quot;");
          div.innerHTML =
            `<div class="legend-dot" style="background:${item.color}"></div>`
            + `<span class="legend-label" title="${fullLabel}">${display}</span>`
            + `<span class="legend-count">${item.count}</span>`;
          div.addEventListener("click", () => {
            div.classList.toggle("dimmed");
            const dimmed = div.classList.contains("dimmed");
            if (item.kind === "super") {
              g.setNodeAttribute(item.id, "hidden", dimmed);
            } else {
              g.forEachNode((nid, attrs) => {
                if (attrs.level === 3 && attrs.community === item.cid) {
                  g.setNodeAttribute(nid, "hidden", dimmed);
                }
              });
            }
            renderer.refresh();
          });
          listEl.appendChild(div);
        }

        document.getElementById("sidebar-stats").textContent =
          `L${currentLevel} (${LEVEL_NAMES[currentLevel]}) · `
          + `${items.length.toLocaleString()} categories · `
          + `${nodes.length.toLocaleString()} leaves · `
          + `${totalMembers.toLocaleString()} members`;
      }
      rebuildLegend();
      setupSearch();
      setupLayerFilters();
      setupRelationFilters();
      setupNavigationControls();

      // ----- L0 reveal animation ------------------------------------
      // The user lands at L0 (~10 super-nodes), so the reveal animates
      // those biggest-first instead of the L3 leaf graph. The skip
      // threshold (proposal #3) suppresses the animation when there are
      // too few super-nodes for the staged reveal to telegraph anything
      // structural — single-domain repos just snap in.
      const l0Items = [];
      g.forEachNode((id, attrs) => {
        if (attrs.level === 0) {
          l0Items.push({ id, count: attrs.memberCount || 1 });
        }
      });
      l0Items.sort((a, b) => b.count - a.count);

      const fadeMs = 450;
      const SKIP_REVEAL_BELOW = 5;
      const shouldAnimate = !skipped
        && l0Items.length >= SKIP_REVEAL_BELOW
        && l0Items.length < L0_DENSE_COUNT;

      if (shouldAnimate) {
        const revealBudget = 1600;
        const staggerMs = l0Items.length > 1
          ? Math.max(18, Math.min(120,
              (revealBudget - fadeMs) / (l0Items.length - 1)))
          : 0;
        const startTime = new Map();
        l0Items.forEach(({ id }, idx) => startTime.set(id, idx * staggerMs));
        const totalAnimMs =
          staggerMs * Math.max(0, l0Items.length - 1) + fadeMs;

        statusEl.textContent = `Revealing ${l0Items.length} domains...`;
        await new Promise(resolve => {
          const aStart = performance.now();
          const easeOut = t => 1 - Math.pow(1 - t, 3);
          const step = () => {
            const elapsed = performance.now() - aStart;
            for (const { id } of l0Items) {
              const start = startTime.get(id) || 0;
              const t = Math.min(1,
                Math.max(0, (elapsed - start) / fadeMs));
              if (t <= 0) continue;
              g.setNodeAttribute(id, "size",
                finalSize.get(id) * easeOut(t));
            }
            if (elapsed < totalAnimMs) requestAnimationFrame(step);
            else resolve();
          };
          requestAnimationFrame(step);
        });
      } else {
        // Snap to final — either the user clicked to skip during
        // FA2 compute, or there are too few L0 nodes to be worth
        // animating.
        for (const { id } of l0Items) {
          g.setNodeAttribute(id, "size", finalSize.get(id));
        }
      }
      layoutElapsed = ((performance.now() - t0) / 1000).toFixed(1);
      statusEl.textContent = baseStatus();
      // Kick the label-relax physics so super-nodes settle into a
      // non-overlapping layout. Visible motion is the point — users
      // watch the clusters spread from where they spawned.
      startPhysics();
  }
  loadGraph().catch(err => {
    statusEl.textContent = "Error loading graph: " + err.message;
  });
</script>
</body>
</html>"""


def _path_key(path: str | None) -> str:
    return str(path or "").replace("\\", "/").strip()


def _path_suffix(path: str | None) -> str:
    lower = _path_key(path).lower()
    for suffix in (".razor.cs",):
        if lower.endswith(suffix):
            return suffix
    idx = lower.rfind(".")
    return lower[idx:] if idx >= 0 else ""


def _file_stem(path: str | None) -> str:
    name = _path_key(path).split("/")[-1]
    lower = name.lower()
    if lower.endswith(".razor.cs"):
        return name[:-9]
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name or "unknown"


def _symbol_key(label: str | None) -> str:
    value = str(label or "").strip().lstrip(".")
    value = re.sub(r"\(.*\)$", "", value)
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _graph_node_id(node: dict) -> str:
    return str(node.get("id") or node.get("key") or "")


def _edge_endpoint(edge: dict, primary: str) -> str | None:
    if primary == "source":
        value = edge.get("source") or edge.get("from") or edge.get("source_id")
    else:
        value = edge.get("target") or edge.get("to") or edge.get("target_id")
    return str(value) if value is not None else None


def _visual_member(node: dict) -> dict:
    label = display_label_for_graph_node(
        node.get("label") or _graph_node_id(node),
        node.get("source_file"),
    )
    return {
        "id": _graph_node_id(node),
        "label": label,
        "source_file": node.get("source_file") or "",
        "source_location": node.get("source_location") or "",
        "file_type": node.get("file_type") or "",
    }


def _csharp_owner_index(nodes: list[dict]) -> dict[str, str]:
    owners: dict[str, str] = {}
    for node in nodes:
        source_file = node.get("source_file")
        if _path_suffix(source_file) not in _CS_SUFFIXES:
            continue
        label = str(node.get("label") or "")
        if label.startswith("."):
            continue
        node_id = _graph_node_id(node)
        if not node_id:
            continue
        owners[node_id] = display_label_for_graph_node(label, source_file)
    return owners


def _csharp_visual_leaf(node: dict, owner_labels: dict[str, str]) -> tuple[str, str]:
    node_id = _graph_node_id(node)
    source_file = _path_key(node.get("source_file"))
    label = str(node.get("label") or node_id)
    owner_id = node_id
    owner_label = display_label_for_graph_node(label, source_file)

    if label.startswith("."):
        method_key = _symbol_key(label)
        prefix = f"{node_id[: -(len(method_key) + 1)]}" if method_key else ""
        if method_key and node_id.endswith(f"_{method_key}") and prefix in owner_labels:
            owner_id = prefix
            owner_label = owner_labels[prefix]
        else:
            owner_id = f"file:{source_file or node_id}"
            owner_label = _file_stem(source_file) or owner_label
    elif node_id in owner_labels:
        owner_label = owner_labels[node_id]

    return f"type::{source_file or 'unknown'}::{owner_id}", owner_label


def _visual_leaf_for_node(node: dict, owner_labels: dict[str, str]) -> tuple[str, str, str]:
    source_file = _path_key(node.get("source_file"))
    suffix = _path_suffix(source_file)
    node_id = _graph_node_id(node)
    if suffix in _CS_SUFFIXES:
        visual_id, label = _csharp_visual_leaf(node, owner_labels)
        return visual_id, label, "type"
    if suffix in _TS_JS_SUFFIXES or node.get("file_type") == "unresolved_call":
        label = _file_stem(source_file) or display_label_for_graph_node(
            node.get("label") or node_id,
            source_file,
        )
        return f"file::{source_file or node_id}", label, "file"
    label = display_label_for_graph_node(node.get("label") or node_id, source_file)
    return node_id, label, "symbol"


def _most_common_value(counter: Counter) -> object | None:
    for value, _count in counter.most_common():
        if value is not None and value != "":
            return value
    return None


def _visual_file_type(node: dict, visual_kind: str) -> str:
    if visual_kind in {"type", "file"}:
        return visual_kind
    return str(node.get("file_type") or visual_kind)


def _collapse_visual_graph(
    raw_nodes: list[dict],
    raw_edges: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Collapse graphify symbol leaves into product-level visual leaves.

    C# visual leaves represent owning types. TypeScript/JavaScript visual
    leaves represent files. The original methods/functions stay available
    as an outline in the inspector and search index, but they no longer
    dominate the graph layout.
    """
    owner_labels = _csharp_owner_index(raw_nodes)
    groups: dict[str, dict] = {}
    raw_to_visual: dict[str, str] = {}

    for node in raw_nodes:
        node_id = _graph_node_id(node)
        if not node_id:
            continue
        visual_id, visual_label, visual_kind = _visual_leaf_for_node(node, owner_labels)
        raw_to_visual[node_id] = visual_id
        group = groups.setdefault(
            visual_id,
            {
                "id": visual_id,
                "label": visual_label,
                "visual_kind": visual_kind,
                "source_file": _path_key(node.get("source_file")),
                "source_location": node.get("source_location") or "",
                "file_type": _visual_file_type(node, visual_kind),
                "members": [],
                "communities": Counter(),
                "layers": Counter(),
            },
        )
        if visual_kind != "symbol" and group["visual_kind"] == "symbol":
            group["visual_kind"] = visual_kind
            group["file_type"] = visual_kind
        if not group.get("source_file") and node.get("source_file"):
            group["source_file"] = _path_key(node.get("source_file"))
        if not group.get("source_location") and node.get("source_location"):
            group["source_location"] = node.get("source_location")
        group["members"].append(_visual_member(node))
        group["communities"][node.get("community")] += 1
        layer = infer_architectural_layer(
            node.get("source_file"),
            file_type=node.get("file_type"),
            label=node.get("label") or node_id,
        )
        group["layers"][layer] += 1

    out_nodes: list[dict] = []
    for group in groups.values():
        community = _most_common_value(group["communities"])
        layer = _most_common_value(group["layers"]) or infer_architectural_layer(
            group.get("source_file"),
            file_type=group.get("file_type"),
            label=group.get("label"),
        )
        hierarchy = compute_node_hierarchy(
            group.get("source_file"),
            fallback_community=community,
        )
        members = group["members"]
        out_nodes.append({
            "id": group["id"],
            "label": group["label"],
            "visual_kind": group["visual_kind"],
            "file_type": group["file_type"],
            "source_file": group.get("source_file") or "",
            "source_location": group.get("source_location") or "",
            "level": 3,
            "layer": layer,
            "community": community,
            "member_count": len(members),
            "symbol_count": len(members),
            "symbols": members[:_VISUAL_MEMBER_LIMIT],
            **hierarchy,
        })

    edge_groups: dict[tuple[str, str, str], dict] = {}
    for edge in raw_edges:
        source = _edge_endpoint(edge, "source")
        target = _edge_endpoint(edge, "target")
        visual_source = raw_to_visual.get(source or "")
        visual_target = raw_to_visual.get(target or "")
        if not visual_source or not visual_target or visual_source == visual_target:
            continue
        relation = str(edge.get("relation") or edge.get("kind") or edge.get("type") or "related")
        key = (visual_source, visual_target, relation)
        aggregate = edge_groups.setdefault(
            key,
            {
                **edge,
                "source": visual_source,
                "target": visual_target,
                "relation": relation,
                "aggregate_count": 0,
            },
        )
        aggregate["aggregate_count"] += 1
        aggregate["weight"] = aggregate["aggregate_count"]

    return out_nodes, list(edge_groups.values())


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


@app.get("/graphify-visual/{project_id}/hierarchy.json")
def _graphify_hierarchy(project_id: str):
    """Multi-level hierarchical view of the project graph.

    Each leaf node is tagged with l0/l1/l2 parent keys. L0 is graphify's
    Leiden community when available; L1/L2 are path prefixes nested under
    that community. Edges reference leaf ids only — the client computes
    super-edges per level on demand by aggregating leaf edges by the parent
    of each endpoint.

    This is what the Sigma viewer fetches — it replaces the older
    graph.json + communities.json pair and folds in the data needed
    to render the L0–L3 zoom hierarchy.
    """
    from fastapi.responses import JSONResponse
    if not _SAFE_PROJECT_RE.match(project_id or ""):
        raise HTTPException(status_code=400, detail="invalid project id")
    ctx = get_project(project_id)
    json_path = ctx._data_dir / "graphify-src" / "graphify-out" / "graph.json"
    if not json_path.exists():
        raise HTTPException(
            status_code=404, detail="graph.json not generated yet"
        )
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="graph.json parse error")

    raw_nodes = [
        n for n in data.get("nodes", [])
        if n.get("file_type") != "rationale"
    ]
    raw_edges = data.get("links") or data.get("edges") or []
    out_nodes, out_edges = _collapse_visual_graph(raw_nodes, raw_edges)

    # Pull DB-derived community labels so super-nodes that fall back to
    # comm:<id> at L0 (flat repos) get a human label instead of the raw id.
    db_path = ctx._data_dir / "graph.db"
    comm_labels: dict[int, str] = {}
    comm_meta: dict[int, dict] = {}
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            def _loads_json_list(value: str | None) -> list:
                try:
                    parsed = json.loads(value or "[]")
                    return parsed if isinstance(parsed, list) else []
                except json.JSONDecodeError:
                    return []
            try:
                for r in conn.execute(
                    "SELECT id, label, size, top_files, top_entities, summary "
                    "FROM communities"
                ):
                    cid = int(r["id"])
                    label = r["label"] or ""
                    comm_labels[cid] = label
                    comm_meta[cid] = {
                        "label": label,
                        "size": int(r["size"] or 0),
                        "top_files": _loads_json_list(r["top_files"]),
                        "top_entities": _loads_json_list(r["top_entities"]),
                        "summary": r["summary"] or "",
                    }
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()
        except sqlite3.Error:
            pass

    return JSONResponse({
        "nodes": out_nodes,
        "edges": out_edges,
        "community_labels": comm_labels,
        "community_meta": comm_meta,
    })


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
