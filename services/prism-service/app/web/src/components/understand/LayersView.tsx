/**
 * LayersView — the architecture-analyzer tab on /understand.
 *
 * Composition borrowed from Lum1104/Understand-Anything's dashboard
 * (Overview + project panel side-by-side) but reskinned to Hermes and
 * wired to PRISM's /api/understand/layers payload.
 */
import { useEffect, useState } from "react";
import { FileCode } from "lucide-react";
import { Empty } from "@/components/ui";
import PrismLayerGraph from "@/components/understand/PrismLayerGraph";
import PrismFileGraph from "@/components/understand/PrismFileGraph";
import PrismProjectPanel from "@/components/understand/PrismProjectPanel";
import PrismLayerDetail from "@/components/understand/PrismLayerDetail";
import PrismFileDetail from "@/components/understand/PrismFileDetail";
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

type Layers = {
  schema?: string;
  status?: string;
  project_overview?: {
    name?: string; summary?: string;
    node_count?: number; edge_count?: number; type_count?: number;
  };
  layers?: Layer[];
  edges?: Edge[];
  file_types?: { id?: string; count?: number }[];
  languages?: string[];
  frameworks?: string[];
  unindexed?: string[];
};


export default function LayersView({ data }: { data: Layers }) {
  const layers = data.layers ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Reset file selection when leaving the drill view.
  useEffect(() => { if (!selectedId) setSelectedFile(null); }, [selectedId]);

  if (layers.length === 0) {
    return <Empty>No layer classification yet.</Empty>;
  }

  const selectedIdx = layers.findIndex((l) => l.id === selectedId);
  const selectedLayer = selectedIdx >= 0 ? layers[selectedIdx] : null;
  const selectedFileIsHub =
    selectedFile != null &&
    (selectedLayer?.hub_symbols ?? []).some(
      (s) => selectedFile.includes(s) ||
             selectedFile.endsWith(s) ||
             (s.split(".").pop() === selectedFile.split("/").pop()?.replace(/\.[^.]+$/, "")),
    );

  return (
    <div className="space-y-5">
      <div className="flex gap-6 items-start">
        <div className="flex-1 min-w-0 space-y-3">
          {selectedLayer ? (
            <DrillCrumb
              layerName={selectedLayer.name ?? selectedLayer.id ?? "—"}
              color={prismLayerColor(selectedIdx).border}
              onBack={() => setSelectedId(null)}
            />
          ) : null}
          {selectedLayer ? (
            <PrismFileGraph
              files={selectedLayer.files ?? []}
              hub_symbols={selectedLayer.hub_symbols ?? []}
              layerColor={prismLayerColor(selectedIdx).dot}
              selectedPath={selectedFile}
              onSelectPath={setSelectedFile}
            />
          ) : (
            <PrismLayerGraph
              layers={layers}
              edges={data.edges ?? []}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
          {!selectedLayer && <LayerLegend layers={layers} />}
        </div>
        {selectedFile && selectedLayer ? (
          <PrismFileDetail
            path={selectedFile}
            isHub={selectedFileIsHub}
            layerColor={prismLayerColor(selectedIdx).border}
            onBack={() => setSelectedFile(null)}
          />
        ) : selectedLayer ? (
          <PrismLayerDetail
            layer={selectedLayer}
            colorIdx={selectedIdx}
            edges={data.edges ?? []}
            onBack={() => setSelectedId(null)}
          />
        ) : (
          <PrismProjectPanel
            overview={data.project_overview}
            layer_count={layers.length}
            file_types={data.file_types}
            languages={data.languages}
            frameworks={data.frameworks}
          />
        )}
      </div>

      <details className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/30">
        <summary className="px-4 py-2 text-[11px] uppercase tracking-wider opacity-70 cursor-pointer">
          Layer detail · {layers.length} layer{layers.length === 1 ? "" : "s"}
        </summary>
        <ul className="px-4 py-3 space-y-3">
          {layers.map((layer, i) => (
            <LayerDetailRow key={layer.id ?? i} layer={layer} colorIdx={i} />
          ))}
        </ul>
      </details>

      {data.unindexed && data.unindexed.length > 0 && (
        <div className="text-[11px] opacity-60">
          {data.unindexed.length} file(s) had no Brain outline (skipped).
        </div>
      )}
    </div>
  );
}


function LayerLegend({ layers }: { layers: Layer[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 text-[11px]">
      {layers.map((layer, i) => {
        const c = prismLayerColor(i);
        return (
          <span key={layer.id ?? i} className="inline-flex items-center gap-2">
            <span
              className="inline-block w-2 h-2 rounded-full"
              style={{ background: c.dot }}
            />
            <span className="font-medium">{layer.name ?? layer.id ?? "—"}</span>
            <span className="opacity-50">({layer.file_count ?? 0})</span>
          </span>
        );
      })}
    </div>
  );
}


function LayerDetailRow({ layer, colorIdx }: { layer: Layer; colorIdx: number }) {
  const c = prismLayerColor(colorIdx);
  return (
    <li
      className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 p-4"
      style={{ borderLeftColor: c.border, borderLeftWidth: 3 }}
    >
      <div className="flex items-baseline justify-between">
        <div className="font-serif text-base tracking-tight">
          {layer.name ?? layer.id ?? "—"}
        </div>
        <div className="text-[11px] opacity-50">
          {layer.file_count ?? 0} file{layer.file_count === 1 ? "" : "s"}
          {layer.complexity && (
            <span className="ml-2 opacity-60 uppercase tracking-wider">
              · {layer.complexity}
            </span>
          )}
        </div>
      </div>
      {layer.description && (
        <p className="text-[12px] opacity-70 mt-1 leading-relaxed">
          {layer.description}
        </p>
      )}
      {layer.hub_symbols && layer.hub_symbols.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {layer.hub_symbols.slice(0, 6).map((s) => (
            <span key={s} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[color:var(--midground-base)]/10">
              {s}
            </span>
          ))}
        </div>
      )}
      {layer.files && layer.files.length > 0 && (
        <ul className="mt-3 text-[11px] font-mono opacity-70 space-y-0.5 max-h-32 overflow-auto">
          {layer.files.slice(0, 10).map((f) => (
            <li key={f} className="flex items-center gap-1.5 truncate">
              <FileCode className="w-3 h-3 opacity-50 shrink-0" />
              <span className="truncate">{f}</span>
            </li>
          ))}
          {layer.files.length > 10 && (
            <li className="opacity-50">+{layer.files.length - 10} more</li>
          )}
        </ul>
      )}
    </li>
  );
}

// Keep the named export so callers don't break if someone imported it.
export { LayerLegend };


function DrillCrumb({
  layerName, color, onBack,
}: { layerName: string; color: string; onBack: () => void }) {
  return (
    <div
      className="flex items-center gap-3 text-[12px] px-3 py-2 rounded-md bg-[color:var(--background-base)]/40 border border-[color:var(--midground-base)]/15"
      style={{ borderLeftWidth: 3, borderLeftColor: color }}
    >
      <button
        onClick={onBack}
        className="uppercase tracking-wider text-[11px] opacity-70 hover:opacity-100"
      >
        ← Overview
      </button>
      <span className="opacity-40">/</span>
      <span className="font-medium">{layerName}</span>
      <span className="opacity-50">— file view</span>
    </div>
  );
}
