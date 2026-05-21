/**
 * PrismFileNode — file node renderer for the inside-a-layer view.
 *
 * Structure inspired by Lum1104/Understand-Anything's CustomNode / FlowNode
 * (@ sha 57a25ed4, MIT). Reskinned to Hermes; hub files get a brighter
 * border + bold filename. No edges yet — the analyzer prompt only emits
 * layer-level dependencies; per-file edges are a v5.2 schema extension.
 */
import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";

export interface PrismFileNodeData extends Record<string, unknown> {
  path: string;
  fileName: string;
  dirName: string;
  isHub: boolean;
  layerColor: string;
}

export type PrismFileFlowNode = Node<PrismFileNodeData, "prism-file">;

function PrismFileNode({ data, selected }: NodeProps<PrismFileFlowNode>) {
  return (
    <div
      className="rounded-md border px-3 py-2 min-w-[180px] max-w-[240px]"
      style={{
        borderColor: data.isHub || selected ? data.layerColor : "rgba(255,255,255,0.10)",
        borderWidth: data.isHub ? 2 : 1,
        background: selected
          ? "rgba(255,255,255,0.06)"
          : "rgba(0,0,0,0.35)",
        boxShadow: selected ? "0 0 0 1px rgba(255,255,255,0.18)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left}
              className="!w-1 !h-1" style={{ background: data.layerColor }} />
      <Handle type="source" position={Position.Right}
              className="!w-1 !h-1" style={{ background: data.layerColor }} />
      <div className="text-[11px] opacity-50 truncate">{data.dirName || "/"}</div>
      <div className={`text-[12px] font-mono mt-0.5 truncate ${data.isHub ? "font-semibold" : ""}`}>
        {data.fileName}
      </div>
      {data.isHub && (
        <div className="text-[9px] uppercase tracking-wider opacity-60 mt-1">
          hub
        </div>
      )}
    </div>
  );
}

export default memo(PrismFileNode);
