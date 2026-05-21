/**
 * DomainsView — the domain-analyzer tab.
 *
 * Top-level: PrismDomainGraph showing each domain as a cluster card.
 * Click a domain → drill into PrismEntityGraph of its entities, with a
 * detail panel summarizing the domain on the right.
 */
import { useState } from "react";
import { Empty, SectionLabel } from "@/components/ui";
import PrismDomainGraph from "@/components/understand/PrismDomainGraph";
import PrismEntityGraph from "@/components/understand/PrismEntityGraph";
import { prismDomainColor } from "@/components/understand/PrismDomainNode";

type Entity = {
  name?: string;
  kind?: string;
  defined_in?: string;
  actions?: string[];
};

type Domain = {
  id?: string;
  description?: string;
  entities?: Entity[];
};

type Domains = {
  schema?: string;
  status?: string;
  domains?: Domain[];
  uncategorized?: string[];
};


export default function DomainsView({ data }: { data: Domains }) {
  const domains = data.domains ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  if (domains.length === 0) {
    return <Empty>No domains extracted yet.</Empty>;
  }

  const idx = domains.findIndex((d) => d.id === selectedId);
  const selectedDomain = idx >= 0 ? domains[idx] : null;
  const color = idx >= 0 ? prismDomainColor(idx) : prismDomainColor(0);

  return (
    <div className="space-y-5">
      <div className="flex gap-6 items-start">
        <div className="flex-1 min-w-0 space-y-3">
          {selectedDomain ? (
            <DrillCrumb
              domainId={selectedDomain.id ?? "—"}
              color={color.border}
              onBack={() => setSelectedId(null)}
            />
          ) : null}
          {selectedDomain ? (
            <PrismEntityGraph
              entities={selectedDomain.entities ?? []}
              layerColor={color.dot}
            />
          ) : (
            <PrismDomainGraph
              domains={domains}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>
        {selectedDomain ? (
          <DomainDetail
            domain={selectedDomain}
            colorIdx={idx}
            onBack={() => setSelectedId(null)}
          />
        ) : (
          <DomainsOverviewPanel
            domains={domains}
            uncategorized={data.uncategorized}
          />
        )}
      </div>

      {data.uncategorized && data.uncategorized.length > 0 && (
        <div className="text-[11px] opacity-60">
          {data.uncategorized.length} entit{data.uncategorized.length === 1 ? "y was" : "ies were"} not categorized.
        </div>
      )}
    </div>
  );
}


function DrillCrumb({
  domainId, color, onBack,
}: { domainId: string; color: string; onBack: () => void }) {
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
      <span className="font-medium">{domainId}</span>
      <span className="opacity-50">— entity view</span>
    </div>
  );
}


function DomainsOverviewPanel({
  domains, uncategorized,
}: { domains: Domain[]; uncategorized?: string[] }) {
  const totalEntities = domains.reduce(
    (a, d) => a + (d.entities?.length ?? 0), 0,
  );
  return (
    <aside className="w-[320px] shrink-0 space-y-5">
      <div>
        <h2 className="font-serif text-xl tracking-tight">Domain glossary</h2>
        <p className="text-[13px] opacity-70 leading-relaxed mt-1">
          {domains.length} domain{domains.length === 1 ? "" : "s"} ·{" "}
          {totalEntities} total entit{totalEntities === 1 ? "y" : "ies"}.
          Click a domain to drill into its entities.
        </p>
      </div>
      <div>
        <SectionLabel>Domains by size</SectionLabel>
        <ul className="space-y-1.5 mt-2">
          {[...domains]
            .sort((a, b) => (b.entities?.length ?? 0) - (a.entities?.length ?? 0))
            .slice(0, 8)
            .map((d, i) => {
              const c = prismDomainColor(domains.findIndex((x) => x.id === d.id));
              return (
                <li key={d.id ?? i} className="flex items-center justify-between text-[12px]">
                  <span className="inline-flex items-center gap-2 truncate">
                    <span className="inline-block w-2 h-2 rounded-full" style={{ background: c.dot }} />
                    <span className="truncate">{d.id ?? "—"}</span>
                  </span>
                  <span className="opacity-60 font-mono">{d.entities?.length ?? 0}</span>
                </li>
              );
            })}
        </ul>
      </div>
      {uncategorized && uncategorized.length > 0 && (
        <div className="text-[11px] opacity-50">
          {uncategorized.length} entit{uncategorized.length === 1 ? "y" : "ies"} not assigned.
        </div>
      )}
    </aside>
  );
}


function DomainDetail({
  domain, colorIdx, onBack,
}: { domain: Domain; colorIdx: number; onBack: () => void }) {
  const c = prismDomainColor(colorIdx);
  const entities = domain.entities ?? [];
  const kinds = new Map<string, number>();
  for (const e of entities) {
    const k = (e.kind || "other").toLowerCase();
    kinds.set(k, (kinds.get(k) ?? 0) + 1);
  }
  return (
    <aside
      className="w-[360px] shrink-0 space-y-5 pl-4 border-l-4"
      style={{ borderLeftColor: c.border }}
    >
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
      >
        ← Back to overview
      </button>
      <div>
        <div className="text-[10px] uppercase tracking-[0.18em] opacity-60">
          Domain
        </div>
        <h2 className="font-serif text-xl tracking-tight">{domain.id ?? "—"}</h2>
      </div>
      {domain.description && (
        <p className="text-[13px] opacity-80 leading-relaxed">
          {domain.description}
        </p>
      )}
      <div>
        <SectionLabel>Entities by kind ({entities.length})</SectionLabel>
        <ul className="space-y-1 mt-2">
          {Array.from(kinds.entries())
            .sort((a, b) => b[1] - a[1])
            .map(([k, n]) => (
              <li key={k} className="flex items-center justify-between text-[12px]">
                <span className="capitalize">{k}</span>
                <span className="opacity-60 font-mono">{n}</span>
              </li>
            ))}
        </ul>
      </div>
    </aside>
  );
}
