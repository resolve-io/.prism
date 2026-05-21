/**
 * PrismFileGraph — drill-down view: a layer's files rendered as nodes.
 *
 * Files are laid out in a grid grouped by directory prefix so files in
 * the same subtree cluster together. Hub-symbol files (those referenced
 * in layer.hub_symbols) get a brighter accent. The clicked layer's color
 * tints all borders.
 */
import { useEffect, useMemo } from "react";
import {
  Background, BackgroundVariant, Controls, MiniMap,
  ReactFlow, ReactFlowProvider,
  useEdgesState, useNodesState,
  type Edge as RfEdge, type Node as RfNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import PrismFileNode, {
  type PrismFileNodeData,
} from "@/components/understand/PrismFileNode";

type Props = {
  files: string[];
  hub_symbols?: string[];
  layerColor: string;
  selectedPath?: string | null;
  onSelectPath?: (path: string | null) => void;
};

type FileEdge = { from: string; to: string; weight: number };

const NODE_TYPES = { "prism-file": PrismFileNode };


function splitPath(p: string): { dirName: string; fileName: string } {
  const norm = p.split("\\").join("/");
  const idx = norm.lastIndexOf("/");
  if (idx < 0) return { dirName: "", fileName: norm };
  return { dirName: norm.slice(0, idx), fileName: norm.slice(idx + 1) };
}


function topDir(dir: string, depth = 2): string {
  // Group by the first `depth` path segments (e.g. "services/prism-service").
  const parts = dir.split("/").filter(Boolean);
  return parts.slice(0, depth).join("/");
}


function layoutGrid(
  files: string[],
  hubs: string[],
  layerColor: string,
): RfNode<PrismFileNodeData>[] {
  // Bucket by topDir; lay each bucket out as a column.
  const buckets = new Map<string, { path: string; isHub: boolean }[]>();
  const hubSet = new Set(hubs.map((s) => s.split(".").pop() ?? s));
  for (const p of files) {
    const { dirName, fileName } = splitPath(p);
    const key = topDir(dirName);
    const stem = fileName.replace(/\.[^.]+$/, "");
    const isHub =
      hubSet.has(fileName) || hubSet.has(stem) || hubs.some((s) => p.includes(s));
    const arr = buckets.get(key) ?? [];
    arr.push({ path: p, isHub });
    buckets.set(key, arr);
  }

  const ROW_H = 76;
  const COL_W = 260;
  const COL_GAP = 28;
  const out: RfNode<PrismFileNodeData>[] = [];
  let colIndex = 0;
  const sortedKeys = Array.from(buckets.keys()).sort();
  for (const key of sortedKeys) {
    const items = buckets.get(key) ?? [];
    items.forEach((it, row) => {
      const { dirName, fileName } = splitPath(it.path);
      out.push({
        id: it.path,
        type: "prism-file",
        position: { x: colIndex * (COL_W + COL_GAP), y: row * ROW_H },
        data: {
          path: it.path,
          fileName,
          dirName,
          isHub: it.isHub,
          layerColor,
        },
      });
    });
    colIndex++;
  }
  return out;
}


export default function PrismFileGraph(props: Props) {
  if (props.files.length === 0) return null;
  return (
    <div className="h-[640px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 overflow-hidden relative">
      <ReactFlowProvider>
        <FileGraphInner
          files={props.files}
          hub_symbols={props.hub_symbols ?? []}
          layerColor={props.layerColor}
          selectedPath={props.selectedPath ?? null}
          onSelectPath={props.onSelectPath}
        />
      </ReactFlowProvider>
    </div>
  );
}


function FileGraphInner({
  files, hub_symbols, layerColor, selectedPath, onSelectPath,
}: {
  files: string[]; hub_symbols: string[]; layerColor: string;
  selectedPath: string | null; onSelectPath?: (p: string | null) => void;
}) {
  const [project] = useProject();
  const initialNodes = useMemo(
    () => layoutGrid(files, hub_symbols, layerColor),
    [files, hub_symbols, layerColor],
  );
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(initialNodes);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<RfEdge>([]);

  useEffect(() => { setRfNodes(initialNodes); }, [initialNodes, setRfNodes]);

  // Pull file-to-file edges from the Graph service (graph.db). Empty
  // when the project hasn't been indexed yet — the layout still works
  // as a grid without edges.
  useEffect(() => {
    let cancel = false;
    if (files.length === 0) {
      setRfEdges([]);
      return;
    }
    api
      .post<{ edges: FileEdge[] }>(
        `/api/graph/edges-between?project=${encodeURIComponent(project)}`,
        { paths: files },
      )
      .then((res) => {
        if (cancel) return;
        const built: RfEdge[] = (res.edges ?? []).map((e, i) => ({
          id: `fe-${i}-${e.from}-${e.to}`,
          source: e.from, target: e.to,
          label: e.weight > 1 ? String(e.weight) : undefined,
          style: {
            stroke: layerColor,
            strokeOpacity: 0.4,
            strokeWidth: Math.min(3, 1 + Math.log2(e.weight + 1)),
          },
          labelStyle: { fill: layerColor, fontSize: 10, fontFamily: "monospace" },
          labelBgStyle: { fill: "transparent" },
        }));
        setRfEdges(built);
      })
      .catch(() => { if (!cancel) setRfEdges([]); });
    return () => { cancel = true; };
  }, [files, project, layerColor, setRfEdges]);

  // Apply selection so PrismFileNode shows its halo.
  const renderedNodes = useMemo(
    () => rfNodes.map((n) => ({ ...n, selected: n.id === selectedPath })),
    [rfNodes, selectedPath],
  );

  return (
    <ReactFlow
      nodes={renderedNodes}
      edges={rfEdges}
      nodeTypes={NODE_TYPES}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={(_e, node) => {
        if (onSelectPath) {
          onSelectPath(node.id === selectedPath ? null : node.id);
        }
      }}
      onPaneClick={() => { if (onSelectPath) onSelectPath(null); }}
      nodesDraggable
      panOnDrag
      nodesConnectable={false}
      zoomOnScroll
      fitView
      fitViewOptions={{ padding: 0.15 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2.5}
    >
      <Background
        variant={BackgroundVariant.Dots}
        color="rgba(200,180,140,0.10)"
        gap={24}
        size={1}
      />
      <Controls
        showInteractive={false}
        position="bottom-left"
        style={{
          background: "rgba(0,0,0,0.65)",
          border: "1px solid rgba(255,255,255,0.18)",
          borderRadius: 6,
          color: "rgba(255,255,255,0.9)",
          ["--xy-controls-button-background-color" as never]: "transparent",
          ["--xy-controls-button-background-color-hover" as never]: "rgba(255,255,255,0.08)",
          ["--xy-controls-button-color" as never]: "rgba(255,255,255,0.9)",
          ["--xy-controls-button-border-color" as never]: "rgba(255,255,255,0.12)",
        }}
      />
      <MiniMap
        pannable
        zoomable
        nodeColor={() => layerColor}
        style={{
          background: "rgba(0,0,0,0.55)",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 6,
        }}
      />
    </ReactFlow>
  );
}
