/**
 * PrismLayerNode — layer node renderer for the architecture graph.
 *
 * Structure ported from Lum1104/Understand-Anything's LayerClusterNode
 * (understand-anything-plugin/packages/dashboard/src/components/
 * LayerClusterNode.tsx @ sha 57a25ed4, MIT). Reskinned to Hermes
 * (PRISM design tokens, font-serif headings, no UA-specific store).
 *
 * Copyright (c) 2026 Yuxiang Lin (MIT) — original structure
 * Adapted for PRISM under MIT-compatible terms.
 */
import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";

export interface PrismLayerNodeData extends Record<string, unknown> {
  layerId: string;
  name: string;
  description?: string;
  complexity?: "simple" | "moderate" | "complex";
  file_count?: number;
  colorIdx: number;
  selected?: boolean;
}

export type PrismLayerFlowNode = Node<PrismLayerNodeData, "prism-layer">;

// Slate Blue palette — all swatches sit in the cool blue-grey hue
// family so the layer cards harmonize with the new background tokens.
// Variation comes from L+S rather than hue so 7 layers stay
// distinguishable without breaking the "one theme" read.
const PALETTE = [
  { border: "rgba(74,124,155,0.55)",  bg: "rgba(74,124,155,0.10)",  dot: "#4a7c9b" },  // steel blue
  { border: "rgba(110,150,190,0.55)", bg: "rgba(110,150,190,0.10)", dot: "#6e96be" },  // sky blue
  { border: "rgba(140,165,200,0.55)", bg: "rgba(140,165,200,0.10)", dot: "#8ca5c8" },  // periwinkle
  { border: "rgba(95,170,180,0.55)",  bg: "rgba(95,170,180,0.10)",  dot: "#5faab4" },  // teal blue
  { border: "rgba(130,140,165,0.55)", bg: "rgba(130,140,165,0.10)", dot: "#828ca5" },  // grey blue
  { border: "rgba(75,110,140,0.55)",  bg: "rgba(75,110,140,0.10)",  dot: "#4b6e8c" },  // navy blue
  { border: "rgba(160,180,200,0.55)", bg: "rgba(160,180,200,0.10)", dot: "#a0b4c8" },  // silver blue
];
export const prismLayerColor = (i: number) => PALETTE[i % PALETTE.length];


const COMPLEXITY_LABEL: Record<string, string> = {
  simple: "simple", moderate: "moderate", complex: "complex",
};


function PrismLayerNode({ data, selected }: NodeProps<PrismLayerFlowNode>) {
  const color = prismLayerColor(data.colorIdx);
  return (
    <div
      className="rounded-lg border-2 px-4 py-3 min-w-[220px] max-w-[280px]"
      style={{
        borderColor: selected ? "rgba(255,255,255,0.45)" : color.border,
        background: color.bg,
        boxShadow: selected ? "0 0 0 2px rgba(255,255,255,0.15)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left}
              className="!w-1.5 !h-1.5"
              style={{ background: color.border }} />
      <Handle type="source" position={Position.Right}
              className="!w-1.5 !h-1.5"
              style={{ background: color.border }} />

      <div className="flex items-center justify-between mb-1">
        <span className="text-[9px] uppercase tracking-[0.18em] opacity-60">
          Layer
        </span>
        {data.complexity && (
          <span className="text-[9px] uppercase tracking-wider opacity-60">
            {COMPLEXITY_LABEL[data.complexity] ?? data.complexity}
          </span>
        )}
      </div>
      <div className="font-serif text-base tracking-tight leading-tight">
        {data.name}
      </div>
      {data.description && (
        <p className="text-[11px] opacity-70 mt-1 leading-snug line-clamp-2">
          {data.description}
        </p>
      )}
      <div className="text-[10px] opacity-60 mt-2 inline-flex items-center gap-1">
        <span className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: color.dot }} />
        {data.file_count ?? 0} file{data.file_count === 1 ? "" : "s"}
      </div>
    </div>
  );
}

export default memo(PrismLayerNode);
