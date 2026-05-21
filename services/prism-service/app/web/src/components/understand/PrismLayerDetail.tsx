/**
 * PrismLayerDetail — right-side panel shown when a layer is selected
 * in the architecture graph. Replaces PrismProjectPanel for the
 * duration of the selection.
 */
import { ArrowLeft, FileCode, GitBranch } from "lucide-react";
import { SectionLabel } from "@/components/ui";
import { prismLayerColor } from "@/components/understand/PrismLayerNode";

type Layer = {
  id?: string;
  name?: string;
  description?: string;
  complexity?: "simple" | "moderate" | "complex";
  file_count?: number;
  files?: string[];
  hub_symbols?: string[];
};

type Edge = { from?: string; to?: string; weight?: number };

type Props = {
  layer: Layer;
  colorIdx: number;
  edges: Edge[];
  onBack: () => void;
};

export default function PrismLayerDetail({
  layer, colorIdx, edges, onBack,
}: Props) {
  const color = prismLayerColor(colorIdx);
  const inbound = edges.filter((e) => e.to === layer.id && e.from !== layer.id);
  const outbound = edges.filter((e) => e.from === layer.id && e.to !== layer.id);
  const files = layer.files ?? [];
  const hubs = layer.hub_symbols ?? [];

  return (
    <aside
      className="w-[360px] shrink-0 space-y-5 rounded-md border-l-4 pl-4"
      style={{ borderLeftColor: color.border }}
    >
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
      >
        <ArrowLeft className="w-3 h-3" /> Back to overview
      </button>

      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] opacity-60">
          Layer
        </div>
        <h2 className="font-serif text-xl tracking-tight">
          {layer.name ?? layer.id ?? "—"}
        </h2>
        {layer.complexity && (
          <span className="inline-block text-[10px] uppercase tracking-wider opacity-60 mt-1">
            {layer.complexity}
          </span>
        )}
      </div>

      {layer.description && (
        <p className="text-[13px] opacity-80 leading-relaxed">
          {layer.description}
        </p>
      )}

      <div className="grid grid-cols-3 gap-2">
        <KpiTiny label="Files" value={layer.file_count ?? files.length} />
        <KpiTiny label="In" value={inbound.reduce((a, e) => a + (e.weight ?? 0), 0)} />
        <KpiTiny label="Out" value={outbound.reduce((a, e) => a + (e.weight ?? 0), 0)} />
      </div>

      {hubs.length > 0 && (
        <div>
          <SectionLabel>Hub symbols</SectionLabel>
          <div className="flex flex-wrap gap-1 mt-2">
            {hubs.map((s) => (
              <span key={s} className="text-[11px] font-mono px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {files.length > 0 && (
        <div>
          <SectionLabel>Files ({files.length})</SectionLabel>
          <ul className="mt-2 text-[12px] font-mono opacity-80 space-y-0.5 max-h-[280px] overflow-auto">
            {files.map((f) => (
              <li key={f} className="flex items-center gap-1.5 truncate">
                <FileCode className="w-3 h-3 opacity-50 shrink-0" />
                <span className="truncate">{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {(inbound.length > 0 || outbound.length > 0) && (
        <div>
          <SectionLabel>Edges</SectionLabel>
          <ul className="mt-2 text-[12px] space-y-1">
            {inbound.map((e, i) => (
              <li key={`in${i}`} className="font-mono opacity-80">
                <GitBranch className="w-3 h-3 inline opacity-50 mr-1" />
                {e.from} → <span className="opacity-100">{e.to}</span>{" "}
                <span className="opacity-50">×{e.weight}</span>
              </li>
            ))}
            {outbound.map((e, i) => (
              <li key={`out${i}`} className="font-mono opacity-80">
                <GitBranch className="w-3 h-3 inline opacity-50 mr-1" />
                <span className="opacity-100">{e.from}</span> → {e.to}{" "}
                <span className="opacity-50">×{e.weight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}


function KpiTiny({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 px-2 py-2 text-center">
      <div className="text-[9px] uppercase tracking-wider opacity-60">
        {label}
      </div>
      <div className="text-lg font-semibold leading-none mt-1">{value}</div>
    </div>
  );
}
