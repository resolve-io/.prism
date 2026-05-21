/**
 * PrismDomainNode — cluster card for a single domain.
 *
 * Structure ported from Lum1104/Understand-Anything's DomainClusterNode
 * (@ sha 57a25ed4, MIT). Reskinned to Hermes.
 */
import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";

export interface PrismDomainNodeData extends Record<string, unknown> {
  domainId: string;
  description?: string;
  entityCount: number;
  entityPreview: string[];
  colorIdx: number;
}

export type PrismDomainFlowNode = Node<PrismDomainNodeData, "prism-domain">;

// Slate Blue palette — paired companion set to PrismLayerNode.PALETTE
// so the two views read as the same theme even when shown side by
// side. Slightly lifted L for the domain (parent) tier so domain
// cards visually outrank the layer cards underneath them.
const DOMAIN_PALETTE = [
  { border: "rgba(100,135,180,0.55)", bg: "rgba(100,135,180,0.10)", dot: "#6487b4" },
  { border: "rgba(125,165,195,0.55)", bg: "rgba(125,165,195,0.10)", dot: "#7da5c3" },
  { border: "rgba(85,115,150,0.55)",  bg: "rgba(85,115,150,0.10)",  dot: "#557396" },
  { border: "rgba(115,155,170,0.55)", bg: "rgba(115,155,170,0.10)", dot: "#739baa" },
  { border: "rgba(150,170,195,0.55)", bg: "rgba(150,170,195,0.10)", dot: "#96aac3" },
  { border: "rgba(95,140,170,0.55)",  bg: "rgba(95,140,170,0.10)",  dot: "#5f8caa" },
];
export const prismDomainColor = (i: number) => DOMAIN_PALETTE[i % DOMAIN_PALETTE.length];


function PrismDomainNode({ data, selected }: NodeProps<PrismDomainFlowNode>) {
  const color = prismDomainColor(data.colorIdx);
  return (
    <div
      className="rounded-xl border-2 px-5 py-4 min-w-[260px] max-w-[340px]"
      style={{
        borderColor: selected ? "rgba(255,255,255,0.45)" : color.border,
        background: color.bg,
        boxShadow: selected ? "0 0 0 2px rgba(255,255,255,0.15)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left}
              className="!w-1.5 !h-1.5" style={{ background: color.border }} />
      <Handle type="source" position={Position.Right}
              className="!w-1.5 !h-1.5" style={{ background: color.border }} />

      <div className="text-[9px] uppercase tracking-[0.18em] opacity-60 mb-1">
        Domain
      </div>
      <div className="font-serif text-base tracking-tight">
        {data.domainId}
      </div>
      {data.description && (
        <p className="text-[11px] opacity-70 mt-1 leading-snug line-clamp-2">
          {data.description}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-1">
        {data.entityPreview.slice(0, 4).map((e) => (
          <span
            key={e}
            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[color:var(--background-base)]/40"
          >
            {e}
          </span>
        ))}
        {data.entityCount > 4 && (
          <span className="text-[10px] opacity-60 px-1 py-0.5">
            +{data.entityCount - 4}
          </span>
        )}
      </div>
      <div className="text-[10px] opacity-60 mt-2 inline-flex items-center gap-1">
        <span className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: color.dot }} />
        {data.entityCount} entit{data.entityCount === 1 ? "y" : "ies"}
      </div>
    </div>
  );
}

export default memo(PrismDomainNode);
