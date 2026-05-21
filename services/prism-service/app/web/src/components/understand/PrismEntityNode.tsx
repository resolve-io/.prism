/**
 * PrismEntityNode — entity card for the inside-a-domain drill view.
 *
 * Shows entity name + kind chip + actions + defined_in path. Tinted
 * with the parent domain's accent color.
 */
import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import type { Node, NodeProps } from "@xyflow/react";

export interface PrismEntityNodeData extends Record<string, unknown> {
  name: string;
  kind?: string;
  defined_in?: string;
  actions?: string[];
  layerColor: string;
}

export type PrismEntityFlowNode = Node<PrismEntityNodeData, "prism-entity">;

function PrismEntityNode({ data, selected }: NodeProps<PrismEntityFlowNode>) {
  return (
    <div
      className="rounded-md border px-3 py-2 min-w-[200px] max-w-[280px]"
      style={{
        borderColor: selected ? "rgba(255,255,255,0.45)" : data.layerColor,
        background: selected ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.35)",
        boxShadow: selected ? "0 0 0 1px rgba(255,255,255,0.18)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left}
              className="!w-1 !h-1" style={{ background: data.layerColor }} />
      <Handle type="source" position={Position.Right}
              className="!w-1 !h-1" style={{ background: data.layerColor }} />

      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[12px] font-semibold truncate">
          {data.name}
        </span>
        {data.kind && (
          <span className="text-[9px] uppercase tracking-wider opacity-60 shrink-0">
            {data.kind}
          </span>
        )}
      </div>
      {data.defined_in && (
        <div className="text-[10px] font-mono opacity-50 mt-0.5 truncate">
          {data.defined_in}
        </div>
      )}
      {data.actions && data.actions.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {data.actions.slice(0, 4).map((a) => (
            <span
              key={a}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[color:var(--background-base)]/40"
            >
              {a}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(PrismEntityNode);
