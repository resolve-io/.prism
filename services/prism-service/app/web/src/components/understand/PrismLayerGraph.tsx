/**
 * PrismLayerGraph — architecture graph using @xyflow/react.
 *
 * Structure ported from Lum1104/Understand-Anything's GraphView/
 * KnowledgeGraphView (@ sha 57a25ed4, MIT). Reskinned to Hermes
 * (PRISM design tokens, no UA store, fitView on mount, smooth
 * zoom-to-node on click).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background, BackgroundVariant, Controls, MiniMap,
  ReactFlow, ReactFlowProvider, useReactFlow,
  useEdgesState, useNodesState,
  type Edge as RfEdge, type Node as RfNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import PrismLayerNode, {
  type PrismLayerNodeData,
} from "@/components/understand/PrismLayerNode";

type LayerIn = {
  id?: string;
  name?: string;
  description?: string;
  complexity?: "simple" | "moderate" | "complex";
  file_count?: number;
};
type EdgeIn = { from?: string; to?: string; weight?: number };

type Props = {
  layers: LayerIn[];
  edges: EdgeIn[];
  selectedId?: string | null;
  onSelect?: (id: string | null) => void;
};

const NODE_TYPES = { "prism-layer": PrismLayerNode };


function layoutCircular(layers: LayerIn[]): RfNode<PrismLayerNodeData>[] {
  const n = layers.length;
  const cx = 0, cy = 0;
  const r = Math.max(260, n * 70);
  return layers.map((layer, i) => {
    const angle = (i / Math.max(1, n)) * Math.PI * 2 - Math.PI / 2;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    const id = layer.id ?? `l${i}`;
    return {
      id,
      type: "prism-layer",
      position: { x, y },
      data: {
        layerId: id,
        name: layer.name ?? layer.id ?? "—",
        description: layer.description ?? "",
        complexity: layer.complexity,
        file_count: layer.file_count ?? 0,
        colorIdx: i,
      },
    };
  });
}


function buildEdges(edges: EdgeIn[]): RfEdge[] {
  return edges
    .filter((e) => e.from && e.to)
    .map((e, i) => ({
      id: `e${i}-${e.from}-${e.to}`,
      source: String(e.from),
      target: String(e.to),
      label: e.weight ? String(e.weight) : undefined,
      animated: false,
      style: {
        stroke: "rgba(200,180,140,0.4)",
        strokeWidth: Math.min(4, Math.max(1, Math.log2((e.weight ?? 1) + 1))),
      },
      labelStyle: {
        fill: "rgba(200,180,140,0.85)",
        fontSize: 10,
        fontFamily: "monospace",
      },
      labelBgStyle: { fill: "transparent" },
    }));
}


export default function PrismLayerGraph(props: Props) {
  if (props.layers.length === 0) return null;
  return (
    <div className="h-[640px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 overflow-hidden relative">
      <ReactFlowProvider>
        <GraphInner {...props} />
      </ReactFlowProvider>
    </div>
  );
}


function GraphInner({
  layers, edges, selectedId: externalSelected, onSelect,
}: Props) {
  const initialNodes = useMemo(() => layoutCircular(layers), [layers]);
  const initialEdges = useMemo(() => buildEdges(edges), [edges]);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(initialNodes);
  const [rfEdges, , onEdgesChange] = useEdgesState(initialEdges);
  const [localSelected, setLocalSelected] = useState<string | null>(null);
  const rf = useReactFlow();

  const selectedId = externalSelected !== undefined ? externalSelected : localSelected;
  const setSelectedId = onSelect ?? setLocalSelected;

  useEffect(() => {
    setRfNodes(initialNodes);
    if (!onSelect) setLocalSelected(null);
  }, [initialNodes, setRfNodes, onSelect]);

  const handleNodeClick = useCallback(
    (_e: React.MouseEvent, node: RfNode<PrismLayerNodeData>) => {
      // Click = navigate to this layer's drill-down view. LayersView
      // observes the selection change and swaps to PrismFileGraph.
      setSelectedId(node.id === selectedId ? null : node.id);
    },
    [selectedId, setSelectedId],
  );

  const handlePaneClick = useCallback(() => {
    setSelectedId(null);
  }, [setSelectedId]);

  // Silence the now-unused `rf` if controlled mode doesn't need it.
  void rf;

  // Project selection into each node so PrismLayerNode renders its halo.
  const renderedNodes = useMemo(
    () => rfNodes.map((n) => ({ ...n, selected: n.id === selectedId })),
    [rfNodes, selectedId],
  );

  return (
    <ReactFlow
      nodes={renderedNodes}
      edges={rfEdges}
      nodeTypes={NODE_TYPES}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      onPaneClick={handlePaneClick}
      nodesDraggable
      panOnDrag
      selectionOnDrag={false}
      nodesConnectable={false}
      zoomOnScroll
      zoomOnPinch
      zoomOnDoubleClick={false}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
    >
      <Background
        variant={BackgroundVariant.Dots}
        color="rgba(200,180,140,0.12)"
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
        nodeColor={(n) => {
          const i = (n.data as PrismLayerNodeData | undefined)?.colorIdx ?? 0;
          const palette = ["#4a7c9b","#5a9e6f","#8b6fb0","#c9a06c","#b07a8a","#4a9b8c","#788291"];
          return palette[i % palette.length];
        }}
        style={{
          background: "rgba(0,0,0,0.55)",
          border: "1px solid rgba(255,255,255,0.15)",
          borderRadius: 6,
        }}
      />
    </ReactFlow>
  );
}
