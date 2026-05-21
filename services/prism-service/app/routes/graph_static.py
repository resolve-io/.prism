"""Graph static routes — Sigma.js viewer HTML and graphify-visual JSON.

Extracted from the deleted app/ui/graph_page.py during the v5.0.0 cutover.
The interactive viewer is server-rendered HTML that delegates rendering to
the user's browser GPU; community labels and graph.json are served as JSON
files. None of these routes depend on NiceGUI.
"""

from __future__ import annotations

import json
import re
import sqlite3

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app.project_context import get_project
from app.services.graph_service import compute_node_hierarchy

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
  .legend-hide { width: 16px; height: 16px; line-height: 14px; border-radius: 3px;
                 background: transparent; border: 0; color: #888; cursor: pointer;
                 font-size: 14px; padding: 0; opacity: 0; flex-shrink: 0; }
  .legend-item:hover .legend-hide { opacity: 0.6; }
  .legend-hide:hover { opacity: 1 !important; background: rgba(255,230,203,0.15);
                       color: var(--midground-base, #ffe6cb); }
  .legend-item.dimmed .legend-hide { opacity: 0.9; color: #ffe6cb; }
  #sidebar-stats { padding: 10px 14px; border-top: 1px solid #2a2a4e;
                   font-size: 11px; color: #666; }
  * { scrollbar-color: #2a2a4e transparent; scrollbar-width: thin; }
  /* GitNexus-style chrome (round 1) — MIT, see header. */
  #toolbar { position: absolute; top: 8px; right: 8px; display: flex;
             gap: 4px; padding: 4px;
             background: rgba(15,15,26,0.85); border: 1px solid #2a2a4e;
             border-radius: 6px; z-index: 12; }
  #toolbar button { background: transparent; border: 0;
             color: #cfd2dc; cursor: pointer; padding: 6px 8px;
             border-radius: 4px; font-size: 11px;
             display: inline-flex; align-items: center; gap: 4px;
             min-width: 30px; justify-content: center; }
  #toolbar button:hover { background: #2a2a4e; }
  #toolbar button.active { color: #fff; background: #2a2a4e; }
  #toolbar button svg { width: 14px; height: 14px;
             stroke: currentColor; stroke-width: 2; fill: none;
             stroke-linecap: round; stroke-linejoin: round; }
  .tb-sep { width: 1px; background: #2a2a4e; margin: 4px 2px; }
  /* Filter section in sidebar */
  #filters { padding: 14px 14px 8px 14px;
             border-bottom: 1px solid #2a2a4e; }
  #filters h3 { font-size: 12px; color: #aaa; margin: 0 0 8px 0;
                text-transform: uppercase; letter-spacing: 0.05em;
                font-weight: 600; }
  .chip-row { display: flex; flex-wrap: wrap; gap: 4px;
              margin-bottom: 10px; }
  .chip-row:last-child { margin-bottom: 0; }
  .chip-label { font-size: 9px; text-transform: uppercase;
                letter-spacing: 0.06em; color: #777;
                width: 100%; margin-bottom: 2px; }
  .chip { font-size: 11px; padding: 3px 8px; border-radius: 999px;
          border: 1px solid #2a2a4e; background: transparent;
          color: #cfd2dc; cursor: pointer; user-select: none; }
  .chip:hover { background: #2a2a4e; }
  .chip.off { color: #555; border-style: dashed; }
  .chip-count { color: #666; font-size: 10px; margin-left: 4px; }

</style>
</head>
<body>
<div id="graph-wrap">
  <div id="status">Loading graph...</div>
  <div id="graph"></div>
  <div id="hint">Scroll to zoom L0→L3 · drag to pan · click a super-node to drill in</div>
<div id="toolbar">
  <button id="tb-zoom-in" title="Zoom in"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3M8 11h6M11 8v6"/></svg></button>
  <button id="tb-zoom-out" title="Zoom out"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3M8 11h6"/></svg></button>
  <button id="tb-fit" title="Fit to view"><svg viewBox="0 0 24 24"><path d="M3 9V5a2 2 0 012-2h4M21 9V5a2 2 0 00-2-2h-4M3 15v4a2 2 0 002 2h4M21 15v4a2 2 0 01-2 2h-4"/></svg></button>
  <button id="tb-focus" title="Focus selected node"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/></svg></button>
  <span class="tb-sep"></span>
  <button id="tb-pause" title="Pause / resume layout"><svg viewBox="0 0 24 24"><path d="M6 4v16M10 4v16M14 4v16M18 4v16"/></svg></button>
  <button id="tb-reset" title="Reset view"><svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 109-9M3 12V5M3 12h7"/></svg></button>
  <button id="tb-edges" title="Toggle curved edges" class="active"><svg viewBox="0 0 24 24"><path d="M3 21c0-9 6-9 9-9s9 0 9-9"/></svg></button>
  <button id="tb-labels" title="Toggle labels" class="active"><svg viewBox="0 0 24 24"><path d="M4 4h12M4 9h8M4 14h16M4 19h6"/></svg></button>
</div>
</div>
<aside id="sidebar">
  <div id="filters">
    <h3>Filters</h3>
    <div class="chip-label">Language</div>
    <div class="chip-row" id="filter-langs"></div>
    <div class="chip-label">Edge type</div>
    <div class="chip-row" id="filter-edges"></div>
  </div>
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
  import Sigma from "https://esm.sh/sigma@3.0.3";
  // Curved edges via @sigma/edge-curve — borrowed from
  // abhigyanpatwari/GitNexus (gitnexus-web/src/components/GraphCanvas.tsx,
  // MIT). Lets dense graphs read without the "all roads through the
  // hub" straight-line tangle.
  import EdgeCurveProgram from "https://esm.sh/@sigma/edge-curve@3.1.0?deps=sigma@3.0.3";
  // Yield to the browser between batches of synchronous work so paint /
  // input can run. requestAnimationFrame is the right primitive here —
  // it lines us up with the next frame, which is the moment Sigma will
  // try to redraw too.
  const yieldToBrowser = () => new Promise(r => requestAnimationFrame(r));
  const PROJECT_ID = "__PROJECT_ID__";
  const statusEl = document.getElementById("status");
  // Slate Blue palette: same dots used by the React LayersView /
  // DomainsView (PrismLayerNode.tsx PALETTE + PrismDomainNode.tsx
  // DOMAIN_PALETTE) so the viewer reads as part of the same app.
  // All 13 swatches sit in the blue-grey hue family — variety comes
  // from L+S rather than hue — against the #0d1726 background-base.
  const COMMUNITY_COLORS = [
    "#4a7c9b","#6e96be","#8ca5c8","#5faab4","#828ca5","#4b6e8c","#a0b4c8",
    "#6487b4","#7da5c3","#557396","#739baa","#96aac3","#5f8caa",
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
      const clusterLabel = community =>
        commLabelsMap.get(community) || commLabelsMap.get(String(community))
        || "unlabeled cluster";
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
        const out = [0, 0, 0, 0];
        const elapsed = performance.now() - levelTransitionStart;
        if (elapsed >= LEVEL_FADE_MS) {
          out[currentLevel] = 1;
          return out;
        }
        const t = elapsed / LEVEL_FADE_MS;
        const eased = t * t * (3 - 2 * t);
        out[currentLevel] = eased;
        out[prevLevel] = 1 - eased;
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

      // L0 cap (closes #76): big multi-repo projects (resolve-platform
      // had 108 L0 keys post-#74) ship a long tail of small clusters
      // that pile labels into an unreadable knot at default zoom. The
      // legend's count cliff is real signal — keep the dominant N and
      // bucket the rest into a synthetic "other" L0 super-node, which
      // a click drills into to reveal the tail at L1.
      const L0_CAP = 20;
      const l0Counts = new Map();
      for (const n of nodes) {
        if (!n.l0) continue;
        l0Counts.set(n.l0, (l0Counts.get(n.l0) || 0) + 1);
      }
      let bucketedTailKeys = 0;
      let bucketedTailEntities = 0;
      if (l0Counts.size > L0_CAP) {
        const ranked = [...l0Counts.entries()].sort((a, b) => b[1] - a[1]);
        const topL0 = new Set(ranked.slice(0, L0_CAP).map(([k]) => k));
        bucketedTailKeys = ranked.length - L0_CAP;
        for (const n of nodes) {
          if (n.l0 && !topL0.has(n.l0)) {
            // Re-tag the leaf so its L0 super-node is the synthetic
            // bucket, but keep l1/l2 untouched so descending into the
            // bucket reveals the original cluster structure at L1.
            n.l0 = "__other__";
            bucketedTailEntities++;
          }
        }
      }

      statusEl.textContent = `Loading ${nodes.length.toLocaleString()} nodes, `
        + `${edges.length.toLocaleString()} edges`
        + (dropped ? ` (hid ${dropped.toLocaleString()} rationale)` : "")
        + (bucketedTailKeys
            ? ` · ${bucketedTailKeys} small clusters → other`
            : "")
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
            // Preserved so filter chips can group by language.
            source_file: n.source_file || "",
            // Path keys for the L0→L3 hierarchy (already used by
            // the level-transition code below).
            l0: n.l0 ?? null, l1: n.l1 ?? null, l2: n.l2 ?? null,
            communityLabel: clusterLabel(n.community),
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
              level: 3,
              // Preserve relation type for filter chips and for
              // future edge-color-by-type styling.
              relation: e.relation || "",
              type: "curve",
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
            ids: [], sx: 0, sy: 0, comm: new Map(),
            // Capture the leaves' ancestor keys so descendants of the
            // synthetic "__other__" bucket get the right l0 for the
            // focus-filter to find them. Splitting the key on "/"
            // would route them back to their original (now bucketed)
            // L0 path instead.
            ancL0: attrs.l0, ancL1: attrs.l1, ancL2: attrs.l2,
          });
          const grp = groups.get(k);
          grp.ids.push(id);
          grp.sx += attrs.x; grp.sy += attrs.y;
          const c = attrs.community ?? "_";
          grp.comm.set(c, (grp.comm.get(c) || 0) + 1);
        });
        for (const [key, grp] of groups) {
          const n = grp.ids.length;
          let bestC = null, bestN = -1;
          for (const [c, cnt] of grp.comm)
            if (cnt > bestN) { bestN = cnt; bestC = c === "_" ? null : c; }
          // Strip path parents to the rightmost segment for a readable
          // label. comm:<id> fallback (flat repos) resolves to the
          // DB-derived community label, then truncated at the first
          // " · " separator so legend / canvas don't show the
          // graphify "<file> · <hub>" suffix as a mashed-up string.
          // The synthetic "__other__" bucket gets a friendly label.
          const rawLabel = key === "__other__"
            ? "other"
            : key.startsWith("comm:")
              ? (clusterLabel(Number(key.slice(5))) || ("cluster " + key.slice(5)))
              : (key.split("/").pop() || key);
          const labelText = (() => {
            const dot = rawLabel.indexOf(" · ");
            return dot > 0 ? rawLabel.substring(0, dot) : rawLabel;
          })();
          // Larger labels at higher abstraction levels so the L0 view
          // reads instantly. Sigma honors per-node labelSize.
          const labelSizeForLevel = lvl === 0 ? 22 : lvl === 1 ? 18 : 15;
          // Ancestor keys come from the leaves themselves, not from
          // splitting `key`. That's what lets the "__other__" bucket
          // properly filter — its L1/L2 descendants keep their
          // original path keys but have l0='__other__' on the leaf,
          // which propagates into super-node ancestor metadata here.
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
          const jx = (Math.random() - 0.5) * 8;
          const jy = (Math.random() - 0.5) * 8;
          g.addNode(`__super__${lvl}__${key}`, {
            label: labelText,
            level: lvl,
            x: targetX * 0.18 + jx,
            y: targetY * 0.18 + jy,
            targetX, targetY,
            // Super-node radius scales sublinearly with member count so
            // a 5000-member cluster doesn't swamp a 200-member one.
            size: 8 + 4 * Math.log(1 + n),
            color: colorFor(bestC),
            community: bestC,
            communityLabel: labelText,
            memberCount: n,
            labelSize: labelSizeForLevel,
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
        for (const v of agg.values()) {
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
          const ids = [];
          g.forEachNode((id, attrs) => {
            if (attrs.level === lvl) ids.push(id);
          });
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
      const HOVER_PUSH_RADIUS = 8;    // graph units
      const HOVER_PUSH_MAX = 3.5;     // graph units
      const HOVER_SIZE_MULT = 1.3;

      // layoutElapsed is filled in after the visible phase finishes; the
      // closure picks up whatever value it holds when baseStatus() is
      // called, so click handlers reading the status get the right text.
      let layoutElapsed = "...";
      const LEVEL_NAMES = ["domains", "services", "modules", "symbols"];
      // Counts items the LOD reducer would paint right now — i.e., at
      // currentLevel and inside the active focus subtree if any. So
      // status reads what the user actually sees, not raw level totals.
      function visibleCount() {
        const fk = focusKey();
        let c = 0;
        g.forEachNode((_id, attrs) => {
          if (attrs.level !== currentLevel) return;
          if (fk && attrs["l" + fk.level] !== fk.key) return;
          c++;
        });
        return c;
      }
      const baseStatus = () => {
        const showing = visibleCount();
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
        return `L${currentLevel}${trail} · ${where} · FA2 ${layoutElapsed}s${hint}`;
      };

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
        labelDensity: 0.15, labelGridCellSize: 80, minCameraRatio: 0.04,
        maxCameraRatio: 30, defaultNodeColor: "#6b7280",
        defaultEdgeColor: "rgba(107,114,128,0.3)",
        // Curved edges via @sigma/edge-curve. Defaults to "curve" so any
        // edge without an explicit type renders curved; nodes can still
        // opt out by setting `type: "line"` on individual edges if needed.
        defaultEdgeType: "curve",
        edgeProgramClasses: { curve: EdgeCurveProgram },
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
          if (fk && data["l" + fk.level] !== fk.key) {
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
          // Force-render labels for super-nodes — at L0 only ~10 of them
          // exist, so respecting labelDensity hides the most useful info
          // on the screen. Leaves still respect the density throttle.
          if (data.level !== undefined && data.level < 3) {
            out = { ...out, forceLabel: true };
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
          if (fk) {
            const ext = g.extremities(edge);
            const fld = "l" + fk.level;
            const sa = g.getNodeAttribute(ext[0], fld);
            const ta = g.getNodeAttribute(ext[1], fld);
            if (sa !== fk.key || ta !== fk.key) {
              return { ...data, hidden: true };
            }
          }
          let out = a < 0.999
            ? { ...data, color: multiplyAlpha(data.color, a) }
            : data;
          // Hover: any super-edge incident to the hovered cluster
          // gets boosted brightness + thickness so the user can
          // trace its connections at a glance. Edges to other
          // clusters stay at their dim default.
          if (hoveredNode) {
            const ext = g.extremities(edge);
            if (ext[0] === hoveredNode || ext[1] === hoveredNode) {
              return {
                ...out,
                color: "rgba(220,228,250,0.92)",
                size: (out.size || data.size) * 1.8,
                zIndex: 2,
              };
            }
          }
          if (!focusedNode) return out;
          const ext = g.extremities(edge);
          if (ext[0] === focusedNode || ext[1] === focusedNode) {
            return { ...out, size: 0.8, zIndex: 1 };
          }
          return { ...out, color: "rgba(40,40,60,0.2)", zIndex: 0 };
        },
      });

      // ----- LOD: mousewheel zoom drives abstraction level -----------
      // Sigma's camera ratio decreases as the user zooms in. Each ratio
      // band corresponds to one level of the hierarchy; crossing a
      // threshold flips currentLevel and the reducers swap the visible
      // layer. ratio=5 lands the user in the L0 band — Sigma's default
      // (x: 0.5, y: 0.5) keeps the camera centered on the graph bbox,
      // which is the right framing because the spread pass above places
      // super-nodes radially around the leaf-graph centroid.
      const camera = renderer.getCamera();
      camera.setState({ ratio: 1.8 });
      currentRatio = 1.8;
      currentLevel = 0;
      // Debug hooks — expose graph + renderer so devtools can inspect
      // node attributes, drive the camera, or smoke-test LOD swaps
      // without monkey-patching. Cheap and useful.
      window.__prismGraph = g;
      window.__prismSigma = renderer;
      // Size-based auto-drill: when the active cluster's bbox grows
      // past ~80% of the viewport (because the user keeps zooming in
      // within the current level), automatically transition to the
      // next-deeper level so its children spread back into view. The
      // ratio-based LOD bands still fire as a fallback; this just
      // catches the case where one cluster's spread doesn't map to
      // the same ratio band as another's. Debounced so a single zoom
      // burst can't cascade through every level at once.
      let lastAutoDrillT = 0;
      function maybeAutoDrill() {
        if (currentLevel >= 3) return;
        const now = performance.now();
        if (now - lastAutoDrillT < 500) return;
        const fk = focusKey();
        let mnX = Infinity, mxX = -Infinity;
        let mnY = Infinity, mxY = -Infinity;
        let count = 0;
        g.forEachNode((id, attrs) => {
          if (attrs.level !== currentLevel) return;
          if (fk && attrs["l" + fk.level] !== fk.key) return;
          if (attrs.x < mnX) mnX = attrs.x;
          if (attrs.x > mxX) mxX = attrs.x;
          if (attrs.y < mnY) mnY = attrs.y;
          if (attrs.y > mxY) mxY = attrs.y;
          count++;
        });
        if (count < 1) return;
        const tl = renderer.graphToViewport({ x: mnX, y: mnY });
        const br = renderer.graphToViewport({ x: mxX, y: mxY });
        const wPx = Math.abs(br.x - tl.x);
        const hPx = Math.abs(br.y - tl.y);
        const cw = renderer.getCanvases().mouse.clientWidth || 1;
        const ch = renderer.getCanvases().mouse.clientHeight || 1;
        const frac = Math.max(wPx / cw, hPx / ch);
        if (frac > 0.80) {
          lastAutoDrillT = now;
          setLevel(currentLevel + 1);
        }
      }

      // Inverse of maybeAutoDrill: when wheel-out shrinks the active
      // cluster below ~22% of the viewport, pop back up to the parent
      // level. Without this, scrolling out at L3 just shoves the leaf
      // mesh into a tiny corner forever — the user has to click empty
      // space to escape, which isn't discoverable.
      let lastAutoPopT = 0;
      function maybeAutoPop() {
        if (currentLevel === 0) return;
        const now = performance.now();
        if (now - lastAutoPopT < 500) return;
        const fk = focusKey();
        let mnX = Infinity, mxX = -Infinity;
        let mnY = Infinity, mxY = -Infinity;
        let count = 0;
        g.forEachNode((id, attrs) => {
          if (attrs.level !== currentLevel) return;
          if (fk && attrs["l" + fk.level] !== fk.key) return;
          if (attrs.x < mnX) mnX = attrs.x;
          if (attrs.x > mxX) mxX = attrs.x;
          if (attrs.y < mnY) mnY = attrs.y;
          if (attrs.y > mxY) mxY = attrs.y;
          count++;
        });
        if (count < 1) return;
        const tl = renderer.graphToViewport({ x: mnX, y: mnY });
        const br = renderer.graphToViewport({ x: mxX, y: mxY });
        const wPx = Math.abs(br.x - tl.x);
        const hPx = Math.abs(br.y - tl.y);
        const cw = renderer.getCanvases().mouse.clientWidth || 1;
        const ch = renderer.getCanvases().mouse.clientHeight || 1;
        const frac = Math.max(wPx / cw, hPx / ch);
        if (frac < 0.22) {
          lastAutoPopT = now;
          const newLevel = currentLevel - 1;
          // Pop any focus items at or below the new level so we don't
          // wind up filtered to a focus deeper than where we are.
          while (focusPath.length > 0
                 && focusPath[focusPath.length - 1].level >= newLevel) {
            focusPath.pop();
          }
          setLevel(newLevel);
        }
      }

      // setLevel — single entry point for level changes. Captures
      // the previous level for the fade, runs the side effects
      // (status text, legend rebuild, physics nudge), and refreshes.
      function setLevel(next) {
        if (next === currentLevel) return;
        prevLevel = currentLevel;
        currentLevel = next;
        levelTransitionStart = performance.now();
        if (focusedNode) {
          focusedNode = null;
          neighborSet = new Set();
        }
        statusEl.textContent = baseStatus();
        rebuildLegend();
        renderer.refresh();
        startPhysics();
      }

      camera.on("updated", () => {
        currentRatio = camera.getState().ratio;
        // Wheel zoom drives the camera ratio only — it never
        // crosses a level threshold by itself. Level changes are
        // size-driven: drill DOWN once the active cluster fills
        // 80% of the viewport, pop UP once it shrinks below 22%.
        renderer.refresh();
        maybeAutoDrill();
        maybeAutoPop();
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
        startPulseLoop();
      });
      renderer.on("leaveNode", () => {
        hoveredNode = null;
        document.body.style.cursor = "";
        renderer.refresh();
      });
      // Shared drill: pushes the node's own key onto the focus stack,
      // advances currentLevel, and pans the camera onto its centroid.
      // Called by both the canvas clickNode handler AND the legend-row
      // click handler so the two affordances behave identically — that
      // was the "tests has no clickthrough" bug, the legend used to only
      // dim/hide.
      function drillIntoSuperNode(nodeId) {
        const attrs = g.getNodeAttributes(nodeId);
        if (attrs.level === undefined || attrs.level >= 3) return false;
        const tgtLvl = attrs.level + 1;
        const ownKey = attrs["l" + attrs.level];
        if (ownKey) {
          focusPath.push({ level: attrs.level, key: ownKey });
        }
        setLevel(tgtLvl);
        const tgtRatio = tgtLvl === 1 ? 1.0
                       : tgtLvl === 2 ? 0.5
                       : 0.2;
        const target = renderer.normalizationFunction({
          x: attrs.x, y: attrs.y,
        });
        camera.animate(
          { x: target.x, y: target.y, ratio: tgtRatio },
          { duration: 600 }
        );
        // Suppress size-based auto-drill / auto-pop while the camera
        // animation runs — without this, the post-zoom bbox of the
        // focused cluster usually fills >80% of the viewport which
        // cascades 0→1→2→3 from a single click (the "first click and
        // I see 890 nodes" bug). The 500 ms throttle is preserved;
        // this just pushes the next eligibility past the animation.
        const suppressUntil = performance.now() + 1100;
        lastAutoDrillT = suppressUntil;
        lastAutoPopT = suppressUntil;
        return true;
      }
      renderer.on("clickNode", ({ node }) => {
        const attrs = g.getNodeAttributes(node);
        if (drillIntoSuperNode(node)) return;
        // L3 leaf — preserve the existing focus / dim-non-neighbors flow.
        focusedNode = node;
        neighborSet = new Set(g.neighbors(node));
        statusEl.textContent = `${attrs.label} `
          + `(cluster: ${attrs.communityLabel || "unlabeled cluster"}, `
          + `degree ${g.degree(node)}) — `
          + `click empty space to clear focus`;
        renderer.refresh();
      });
      // Click on empty space backs all the way out — clears the
      // focus stack, drops the leaf-focus dim-highlight, and resets
      // currentLevel to L0. With no ratio-based level changes,
      // this is the user's main escape hatch.
      renderer.on("clickStage", () => {
        const hadFocus = !!focusedNode || focusPath.length > 0;
        const wasDeep = currentLevel > 0;
        if (!hadFocus && !wasDeep) return;
        focusedNode = null;
        neighborSet = new Set();
        focusPath = [];
        if (wasDeep) {
          setLevel(0);
        } else {
          statusEl.textContent = baseStatus();
          rebuildLegend();
          renderer.refresh();
          startPhysics();
        }
      });

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
          !fk || attrs["l" + fk.level] === fk.key;
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
          g.forEachNode((_n, attrs) => {
            if (attrs.level !== 3) return;
            if (!inFocus(attrs)) return;
            const c = attrs.community;
            if (c === null || c === undefined) return;
            counts.set(c, (counts.get(c) || 0) + 1);
          });
          items = [...counts.entries()].map(([cid, n]) => ({
            kind: "community", cid,
            label: clusterLabel(cid),
            color: colorFor(cid),
            count: n,
          }));
        }
        items.sort((a, b) => b.count - a.count);

        for (const item of items) {
          const div = document.createElement("div");
          div.className = "legend-item";
          const display = truncateLabel(item.label);
          const fullLabel = (item.label || "").replace(/"/g, "&quot;");
          // Hide affordance moves to a small × on the right; the row
          // label/dot now drives the same drill-into action as clicking
          // the canvas super-node. The × keeps the "isolate by hiding
          // other clusters" workflow alive without stealing the main
          // gesture.
          const drillable = item.kind === "super" && currentLevel < 3;
          div.title = drillable ? "Click to drill into " + display
                                : (fullLabel || "");
          div.innerHTML =
            `<div class="legend-dot" style="background:${item.color}"></div>`
            + `<span class="legend-label">${display}</span>`
            + `<span class="legend-count">${item.count}</span>`
            + `<button class="legend-hide" title="Hide ${display}" aria-label="Hide">×</button>`;
          const hideBtn = div.querySelector(".legend-hide");
          hideBtn.addEventListener("click", (ev) => {
            ev.stopPropagation();
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
          div.addEventListener("click", () => {
            if (drillable) drillIntoSuperNode(item.id);
          });
          listEl.appendChild(div);
        }

        document.getElementById("sidebar-stats").textContent =
          `L${currentLevel} (${LEVEL_NAMES[currentLevel]}) · `
          + `${items.length.toLocaleString()} categories · `
          + `${nodes.length.toLocaleString()} symbols total`;
      }
      rebuildLegend();

      // ----- Toolbar wiring (round 1 chrome) ------------------------
      // Pattern borrowed from GitNexus's GraphCanvas toolbar (MIT).
      // The buttons exist in the DOM; this binds them to camera ops,
      // a re-runnable FA2 layout, and Sigma settings toggles.
      const cam = renderer.getCamera();
      const $tb = id => document.getElementById(id);
      $tb("tb-zoom-in")  && ($tb("tb-zoom-in").onclick  = () => cam.animatedZoom({ duration: 220 }));
      $tb("tb-zoom-out") && ($tb("tb-zoom-out").onclick = () => cam.animatedUnzoom({ duration: 220 }));
      $tb("tb-fit")      && ($tb("tb-fit").onclick      = () => cam.animatedReset({ duration: 320 }));
      $tb("tb-reset") && ($tb("tb-reset").onclick = () => {
        focusedNode = null; neighborSet = new Set();
        hidden.clear();
        document.querySelectorAll(".legend-item").forEach(el => el.classList.remove("dimmed"));
        hiddenLangs.clear(); hiddenRelations.clear();
        document.querySelectorAll(".chip").forEach(el => el.classList.remove("off"));
        applyFilters();
        cam.animatedReset({ duration: 320 });
      });
      $tb("tb-focus") && ($tb("tb-focus").onclick = () => {
        if (!focusedNode) return;
        const attrs = g.getNodeAttributes(focusedNode);
        cam.animate({ x: attrs.x, y: attrs.y, ratio: 0.3 }, { duration: 320 });
      });
      let physicsLayout = null;
      $tb("tb-pause") && ($tb("tb-pause").onclick = (ev) => {
        const btn = ev.currentTarget;
        if (physicsLayout) {
          physicsLayout.stop(); physicsLayout.kill(); physicsLayout = null;
          btn.classList.remove("active");
        } else {
          const s2 = forceAtlas2.inferSettings(g);
          s2.barnesHutOptimize = g.order > 2000;
          s2.gravity = 1.2; s2.slowDown = 5;
          physicsLayout = new FA2Layout(g, { settings: s2 });
          physicsLayout.start();
          btn.classList.add("active");
        }
      });
      let edgesCurved = true;
      $tb("tb-edges") && ($tb("tb-edges").onclick = (ev) => {
        edgesCurved = !edgesCurved;
        ev.currentTarget.classList.toggle("active", edgesCurved);
        // Switch every edge between "curve" and "line" type. Sigma
        // re-renders on the next frame.
        g.forEachEdge((eid) => {
          g.setEdgeAttribute(eid, "type", edgesCurved ? "curve" : "line");
        });
        renderer.refresh();
      });
      let labelsOn = true;
      $tb("tb-labels") && ($tb("tb-labels").onclick = (ev) => {
        labelsOn = !labelsOn;
        ev.currentTarget.classList.toggle("active", labelsOn);
        renderer.setSetting("renderLabels", labelsOn);
        renderer.refresh();
      });

      // ----- Filter chips (round 1 chrome) --------------------------
      // Count nodes by language (file extension) and edges by relation
      // type, then render chips with counts. Toggling adds to hidden
      // sets that applyFilters() applies via the `hidden` attr.
      const hiddenLangs = new Set();
      const hiddenRelations = new Set();
      const extOf = (p) => {
        const m = (p || "").match(/\.([a-zA-Z0-9]+)$/);
        return m ? "." + m[1].toLowerCase() : "(none)";
      };
      const langOf = (ext) => ({
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".cs": "C#", ".go": "Go", ".rs": "Rust", ".java": "Java",
        ".rb": "Ruby", ".php": "PHP", ".cpp": "C++", ".c": "C",
        ".md": "Markdown",
      }[ext] || ext);

      function applyFilters() {
        g.forEachNode((nid, attrs) => {
          const ext = extOf(attrs.source_file || "");
          const isHiddenByCluster =
            attrs.community !== undefined && attrs.community !== null
            && hidden.has(attrs.community);
          const isHiddenByLang = hiddenLangs.has(langOf(ext));
          g.setNodeAttribute(nid, "hidden", isHiddenByCluster || isHiddenByLang);
        });
        g.forEachEdge((eid, attrs) => {
          const rel = attrs.relation || "(none)";
          g.setEdgeAttribute(eid, "hidden", hiddenRelations.has(rel));
        });
        renderer.refresh();
      }

      function buildChipRow(containerId, items, hiddenSet) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = "";
        for (const [label, count] of items) {
          const chip = document.createElement("button");
          chip.className = "chip";
          chip.innerHTML =
            `<span>${label}</span><span class="chip-count">${count}</span>`;
          chip.onclick = () => {
            if (hiddenSet.has(label)) { hiddenSet.delete(label); chip.classList.remove("off"); }
            else { hiddenSet.add(label); chip.classList.add("off"); }
            applyFilters();
          };
          el.appendChild(chip);
        }
      }
      const langCounts = new Map();
      g.forEachNode((_n, a) => {
        const lang = langOf(extOf(a.source_file || ""));
        langCounts.set(lang, (langCounts.get(lang) || 0) + 1);
      });
      const edgeCounts = new Map();
      g.forEachEdge((_e, a) => {
        const r = a.relation || "(none)";
        edgeCounts.set(r, (edgeCounts.get(r) || 0) + 1);
      });
      buildChipRow("filter-langs",
        [...langCounts.entries()].sort((a, b) => b[1] - a[1]),
        hiddenLangs);
      buildChipRow("filter-edges",
        [...edgeCounts.entries()].sort((a, b) => b[1] - a[1]),
        hiddenRelations);

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
      const shouldAnimate = !skipped && l0Items.length >= SKIP_REVEAL_BELOW;

      if (shouldAnimate) {
        const revealBudget = 1600;
        const staggerMs = l0Items.length > 1
          ? Math.max(60, Math.min(180,
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


@router.get("/graphify-visual/{project_id}/hierarchy.json")
def _graphify_hierarchy(project_id: str):
    """Multi-level hierarchical view of the project graph.

    Each leaf node is tagged with l0/l1/l2 parent keys derived from
    its file path (with src/app/services-style container directories
    stripped). Edges reference leaf ids only — the client computes
    super-edges per level on demand by aggregating leaf edges by the
    parent of each endpoint.

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

    out_nodes = []
    for n in raw_nodes:
        h = compute_node_hierarchy(
            n.get("source_file"),
            fallback_community=n.get("community"),
        )
        # Mark leaves as level 3 so the client doesn't have to special-case
        # them after super-nodes are added with level 0/1/2.
        out_nodes.append({**n, "level": 3, **h})

    # Pull DB-derived community labels so super-nodes that fall back to
    # comm:<id> at L0 (flat repos) get a human label instead of the raw id.
    db_path = ctx._data_dir / "graph.db"
    comm_labels: dict[int, str] = {}
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                for r in conn.execute("SELECT id, label FROM communities"):
                    comm_labels[int(r[0])] = r[1] or ""
            except sqlite3.OperationalError:
                pass
            finally:
                conn.close()
        except sqlite3.Error:
            pass

    return JSONResponse({
        "nodes": out_nodes,
        "edges": raw_edges,
        "community_labels": comm_labels,
    })



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
