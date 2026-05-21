/**
 * PrismEntityGraph — drill-down: entity nodes for a single domain.
 *
 * Entities are columned by `kind` so classes/dataclasses sit together,
 * actions cluster, etc. Tinted with the parent domain's accent color.
 */
import { useEffect, useMemo } from "react";
import {
  Background, BackgroundVariant, Controls, MiniMap,
  ReactFlow, ReactFlowProvider,
  useEdgesState, useNodesState,
  type Edge as RfEdge, type Node as RfNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import PrismEntityNode, {
  type PrismEntityNodeData,
} from "@/components/understand/PrismEntityNode";

type EntityIn = {
  name?: string;
  kind?: string;
  defined_in?: string;
  actions?: string[];
};

type Props = {
  entities: EntityIn[];
  layerColor: string;
};

const NODE_TYPES = { "prism-entity": PrismEntityNode };


function layoutByKind(
  entities: EntityIn[],
  layerColor: string,
): RfNode<PrismEntityNodeData>[] {
  const buckets = new Map<string, EntityIn[]>();
  for (const e of entities) {
    const k = (e.kind || "other").toLowerCase();
    const arr = buckets.get(k) ?? [];
    arr.push(e);
    buckets.set(k, arr);
  }

  const ROW_H = 100;
  const COL_W = 300;
  const COL_GAP = 36;
  const out: RfNode<PrismEntityNodeData>[] = [];
  const kinds = Array.from(buckets.keys()).sort();
  kinds.forEach((k, colIndex) => {
    (buckets.get(k) ?? []).forEach((e, row) => {
      out.push({
        id: `${e.name ?? "anon"}@${k}@${colIndex}-${row}`,
        type: "prism-entity",
        position: { x: colIndex * (COL_W + COL_GAP), y: row * ROW_H },
        data: {
          name: e.name ?? "—",
          kind: e.kind,
          defined_in: e.defined_in,
          actions: e.actions,
          layerColor,
        },
      });
    });
  });
  return out;
}


export default function PrismEntityGraph({ entities, layerColor }: Props) {
  if (entities.length === 0) return null;
  return (
    <div className="h-[640px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 overflow-hidden relative">
      <ReactFlowProvider>
        <EntityGraphInner entities={entities} layerColor={layerColor} />
      </ReactFlowProvider>
    </div>
  );
}


function EntityGraphInner({ entities, layerColor }: Props) {
  const initialNodes = useMemo(
    () => layoutByKind(entities, layerColor),
    [entities, layerColor],
  );
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(initialNodes);
  const [rfEdges, , onEdgesChange] = useEdgesState<RfEdge>([]);

  useEffect(() => { setRfNodes(initialNodes); }, [initialNodes, setRfNodes]);

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={NODE_TYPES}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
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
      <Background variant={BackgroundVariant.Dots}
                  color="rgba(200,180,140,0.10)" gap={24} size={1} />
      <Controls
        showInteractive={false} position="bottom-left"
        style={{
          background: "rgba(0,0,0,0.65)",
          border: "1px solid rgba(255,255,255,0.18)",
          borderRadius: 6, color: "rgba(255,255,255,0.9)",
          ["--xy-controls-button-background-color" as never]: "transparent",
          ["--xy-controls-button-background-color-hover" as never]: "rgba(255,255,255,0.08)",
          ["--xy-controls-button-color" as never]: "rgba(255,255,255,0.9)",
          ["--xy-controls-button-border-color" as never]: "rgba(255,255,255,0.12)",
        }}
      />
      <MiniMap pannable zoomable
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
