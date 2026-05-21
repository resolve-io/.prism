/**
 * PrismDomainGraph — top-level domain cluster graph.
 *
 * Layout: circular for >4 domains, single row for ≤4. No inter-domain
 * edges in the analyzer schema yet, so the graph is just floating
 * cluster cards. Click a domain → drill into its entities (handled by
 * DomainsView).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background, BackgroundVariant, Controls, MiniMap,
  ReactFlow, ReactFlowProvider,
  useEdgesState, useNodesState,
  type Edge as RfEdge, type Node as RfNode,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import PrismDomainNode, {
  type PrismDomainNodeData,
} from "@/components/understand/PrismDomainNode";

type DomainIn = {
  id?: string;
  description?: string;
  entities?: { name?: string }[];
};

type Props = {
  domains: DomainIn[];
  selectedId?: string | null;
  onSelect?: (id: string | null) => void;
};

const NODE_TYPES = { "prism-domain": PrismDomainNode };


function layoutDomains(domains: DomainIn[]): RfNode<PrismDomainNodeData>[] {
  const n = domains.length;
  return domains.map((d, i) => {
    const entities = d.entities ?? [];
    const data: PrismDomainNodeData = {
      domainId: d.id ?? `domain-${i}`,
      description: d.description ?? "",
      entityCount: entities.length,
      entityPreview: entities.map((e) => e.name ?? "").filter(Boolean),
      colorIdx: i,
    };

    if (n <= 4) {
      // Single row layout.
      return {
        id: data.domainId, type: "prism-domain",
        position: { x: i * 360, y: 0 }, data,
      };
    }
    // Circular layout.
    const r = Math.max(280, n * 70);
    const angle = (i / Math.max(1, n)) * Math.PI * 2 - Math.PI / 2;
    return {
      id: data.domainId, type: "prism-domain",
      position: { x: Math.cos(angle) * r, y: Math.sin(angle) * r },
      data,
    };
  });
}


export default function PrismDomainGraph(props: Props) {
  if (props.domains.length === 0) return null;
  return (
    <div className="h-[640px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 overflow-hidden relative">
      <ReactFlowProvider>
        <DomainGraphInner {...props} />
      </ReactFlowProvider>
    </div>
  );
}


function DomainGraphInner({
  domains, selectedId: externalSelected, onSelect,
}: Props) {
  const initialNodes = useMemo(() => layoutDomains(domains), [domains]);
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState(initialNodes);
  const [rfEdges, , onEdgesChange] = useEdgesState<RfEdge>([]);
  const [localSelected, setLocalSelected] = useState<string | null>(null);

  const selectedId = externalSelected !== undefined ? externalSelected : localSelected;
  const setSelectedId = onSelect ?? setLocalSelected;

  useEffect(() => {
    setRfNodes(initialNodes);
    if (!onSelect) setLocalSelected(null);
  }, [initialNodes, setRfNodes, onSelect]);

  const handleNodeClick = useCallback(
    (_e: React.MouseEvent, node: RfNode<PrismDomainNodeData>) => {
      setSelectedId(node.id === selectedId ? null : node.id);
    },
    [selectedId, setSelectedId],
  );

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
      onPaneClick={() => setSelectedId(null)}
      nodesDraggable
      panOnDrag
      nodesConnectable={false}
      zoomOnScroll
      zoomOnDoubleClick={false}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      proOptions={{ hideAttribution: true }}
      minZoom={0.2}
      maxZoom={2}
    >
      <Background variant={BackgroundVariant.Dots}
                  color="rgba(200,180,140,0.12)" gap={24} size={1} />
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
        pannable zoomable
        nodeColor={(n) => {
          const palette = ["#a58cc8","#6eb496","#dca078","#96b4d2","#c88c8c","#8cc8c8"];
          const i = (n.data as PrismDomainNodeData | undefined)?.colorIdx ?? 0;
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
