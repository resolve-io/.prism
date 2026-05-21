/**
 * PrismProjectPanel — project-overview side panel.
 *
 * Structure ported from Lum1104/Understand-Anything's ProjectOverview
 * (@ sha 57a25ed4, MIT). Reskinned to Hermes (PRISM design tokens).
 * Shows project summary, KPIs (nodes/edges/layers/types), file-type
 * breakdown, language chips, framework chips.
 */
import { SectionLabel } from "@/components/ui";

type Overview = {
  name?: string;
  summary?: string;
  node_count?: number;
  edge_count?: number;
  type_count?: number;
};

type FileTypeBin = { id?: string; count?: number };

type Props = {
  overview?: Overview;
  layer_count?: number;
  file_types?: FileTypeBin[];
  languages?: string[];
  frameworks?: string[];
};

const FILE_TYPE_DOT: Record<string, string> = {
  code: "#4a7c9b",
  config: "#788291",
  docs: "#c9a06c",
  infra: "#8b6fb0",
  data: "#5a9e6f",
  tests: "#b07a8a",
  ci: "#4a9b8c",
};


export default function PrismProjectPanel({
  overview, layer_count, file_types, languages, frameworks,
}: Props) {
  const total_file_types = (file_types ?? []).reduce(
    (acc, f) => acc + (f.count ?? 0), 0,
  );

  return (
    <aside className="w-[320px] shrink-0 space-y-5">
      {overview?.name && (
        <div>
          <h2 className="font-serif text-xl tracking-tight">{overview.name}</h2>
          {overview.summary && (
            <p className="text-[13px] opacity-75 leading-relaxed mt-1">
              {overview.summary}
            </p>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <KpiBox label="Nodes" value={overview?.node_count ?? 0} />
        <KpiBox label="Edges" value={overview?.edge_count ?? 0} />
        <KpiBox label="Layers" value={layer_count ?? 0} />
        <KpiBox label="Types" value={overview?.type_count ?? 0} />
      </div>

      {file_types && file_types.length > 0 && (
        <div>
          <SectionLabel>File Types</SectionLabel>
          <ul className="space-y-1.5 mt-2">
            {file_types.map((f) => (
              <li
                key={f.id ?? "?"}
                className="flex items-center justify-between text-[12px]"
              >
                <span className="inline-flex items-center gap-2">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ background: FILE_TYPE_DOT[f.id ?? ""] ?? "#788291" }}
                  />
                  <span className="capitalize">{f.id ?? "—"}</span>
                </span>
                <span className="opacity-60 font-mono">{f.count ?? 0}</span>
              </li>
            ))}
            {total_file_types > 0 && (
              <li className="flex items-center justify-between text-[11px] opacity-50 pt-1 border-t border-[color:var(--midground-base)]/10 mt-2">
                <span className="uppercase tracking-wider">Total</span>
                <span className="font-mono">{total_file_types}</span>
              </li>
            )}
          </ul>
        </div>
      )}

      {languages && languages.length > 0 && (
        <div>
          <SectionLabel>Languages</SectionLabel>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {languages.map((l) => (
              <span key={l} className="text-[11px] px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10">
                {l}
              </span>
            ))}
          </div>
        </div>
      )}

      {frameworks && frameworks.length > 0 && (
        <div>
          <SectionLabel>Frameworks</SectionLabel>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {frameworks.map((f) => (
              <span key={f} className="text-[11px] px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10">
                {f}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}


function KpiBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 px-3 py-2.5">
      <div className="text-[9px] uppercase tracking-wider opacity-60 mb-1">
        {label}
      </div>
      <div className="text-2xl font-semibold leading-none">{value}</div>
    </div>
  );
}
