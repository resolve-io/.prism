/**
 * PrismFileDetail — per-file right-panel for the layer drill view.
 *
 * Lazy-fetches /api/graph/file-detail on mount / path change. Mirrors
 * UA's per-node panel (entity list + referenced components) but
 * sourced from PRISM's existing graph.db.
 */
import { useEffect, useState } from "react";
import { ArrowLeft, FileCode, GitBranch } from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { SectionLabel } from "@/components/ui";

type EntityRow = { name: string; kind: string | null; line: number | null };
type EdgeRow = { from?: string; to?: string; weight: number };
type Detail = {
  path: string;
  entities: EntityRow[];
  inbound: EdgeRow[];
  outbound: EdgeRow[];
};

type Props = {
  path: string;
  isHub: boolean;
  layerColor: string;
  onBack: () => void;
};


function splitPath(p: string): { dirName: string; fileName: string } {
  const norm = p.split("\\").join("/");
  const i = norm.lastIndexOf("/");
  return i < 0
    ? { dirName: "", fileName: norm }
    : { dirName: norm.slice(0, i), fileName: norm.slice(i + 1) };
}


export default function PrismFileDetail({
  path, isHub, layerColor, onBack,
}: Props) {
  const [project] = useProject();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    setDetail(null);
    setError(null);
    api
      .get<Detail>(
        `/api/graph/file-detail?project=${encodeURIComponent(project)}` +
        `&path=${encodeURIComponent(path)}`,
      )
      .then((d) => { if (!cancel) setDetail(d); })
      .catch((e) => { if (!cancel) setError(String(e.message ?? e)); });
    return () => { cancel = true; };
  }, [project, path]);

  const { dirName, fileName } = splitPath(path);
  const entities = detail?.entities ?? [];
  const inbound = detail?.inbound ?? [];
  const outbound = detail?.outbound ?? [];

  return (
    <aside
      className="w-[360px] shrink-0 space-y-5 pl-4 border-l-4"
      style={{ borderLeftColor: layerColor }}
    >
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
      >
        <ArrowLeft className="w-3 h-3" /> Back to layer
      </button>

      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] opacity-60 flex items-center gap-2">
          File
          {isHub && (
            <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[color:var(--midground-base)]/15">
              hub
            </span>
          )}
        </div>
        <div className="text-[11px] opacity-50 mt-1 truncate">{dirName || "/"}</div>
        <h2 className="font-mono text-base mt-0.5 break-all">{fileName}</h2>
      </div>

      {error && (
        <div className="text-[11px] text-rose-300 opacity-80">{error}</div>
      )}

      <div className="grid grid-cols-3 gap-2">
        <KpiTiny label="Symbols" value={entities.length} />
        <KpiTiny label="In"
          value={inbound.reduce((a, e) => a + e.weight, 0)} />
        <KpiTiny label="Out"
          value={outbound.reduce((a, e) => a + e.weight, 0)} />
      </div>

      {entities.length > 0 && (
        <div>
          <SectionLabel>Symbols ({entities.length})</SectionLabel>
          <ul className="mt-2 space-y-1 max-h-[180px] overflow-auto">
            {entities.slice(0, 40).map((e, i) => (
              <li key={`${e.name}-${i}`} className="text-[12px] flex items-baseline gap-2">
                <span className="font-mono">{e.name}</span>
                {e.kind && (
                  <span className="text-[9px] uppercase tracking-wider opacity-50">
                    {e.kind}
                  </span>
                )}
                {e.line && (
                  <span className="text-[10px] font-mono opacity-40 ml-auto">
                    L{e.line}
                  </span>
                )}
              </li>
            ))}
            {entities.length > 40 && (
              <li className="text-[10px] opacity-50">
                +{entities.length - 40} more
              </li>
            )}
          </ul>
        </div>
      )}

      {(inbound.length > 0 || outbound.length > 0) && (
        <div>
          <SectionLabel>Referenced from / to</SectionLabel>
          <ul className="mt-2 space-y-1 text-[11px]">
            {inbound.slice(0, 6).map((e, i) => (
              <li key={`in${i}`} className="font-mono opacity-80 flex items-baseline gap-2">
                <GitBranch className="w-3 h-3 opacity-50 shrink-0" />
                <span className="truncate">{shortPath(e.from ?? "")}</span>
                <span className="opacity-50 ml-auto shrink-0">→ here ×{e.weight}</span>
              </li>
            ))}
            {outbound.slice(0, 6).map((e, i) => (
              <li key={`out${i}`} className="font-mono opacity-80 flex items-baseline gap-2">
                <FileCode className="w-3 h-3 opacity-50 shrink-0" />
                <span className="opacity-50 shrink-0">here →</span>
                <span className="truncate">{shortPath(e.to ?? "")}</span>
                <span className="opacity-50 ml-auto shrink-0">×{e.weight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </aside>
  );
}


function shortPath(p: string): string {
  const parts = p.split("\\").join("/").split("/");
  return parts.slice(-2).join("/");
}


function KpiTiny({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 px-2 py-2 text-center">
      <div className="text-[9px] uppercase tracking-wider opacity-60">{label}</div>
      <div className="text-lg font-semibold leading-none mt-1">{value}</div>
    </div>
  );
}
