import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, Kpi, SectionLabel, Pill, Empty } from "@/components/ui";

type Entry = {
  name?: string;
  type?: string;
  classification?: string;
  status?: string;
  description?: string;
  domain?: string;
};

const TYPES = ["all", "expertise", "convention", "decision", "anti-pattern"];
const STATUSES = ["all", "active", "stale", "retired"];

export default function MemoryPage() {
  const [project] = useProject();
  const [domains, setDomains] = useState<string[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [domain, setDomain] = useState<string>("all");
  const [type, setType] = useState<string>("all");
  const [status, setStatus] = useState<string>("all");
  const [entries, setEntries] = useState<Entry[]>([]);

  useEffect(() => {
    api.get<{ domains: string[]; stats: Record<string, number> }>(`/api/memory/domains?project=${project}`)
      .then((d) => { setDomains(d.domains); setStats(d.stats); })
      .catch(() => { setDomains([]); setStats({}); });
  }, [project]);

  useEffect(() => {
    const params = new URLSearchParams({ project });
    if (domain !== "all") params.set("domain", domain);
    if (type !== "all") params.set("type", type);
    if (status !== "all") params.set("status", status);
    api.get<{ entries: Entry[] }>(`/api/memory/entries?${params}`)
      .then((d) => setEntries(d.entries)).catch(() => setEntries([]));
  }, [project, domain, type, status]);

  const total = useMemo(() => Object.values(stats).reduce((a, b) => a + b, 0), [stats]);

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        <Kpi label="Entries" value={total} />
        <Kpi label="Domains" value={domains.length} />
        <Kpi label="Showing" value={entries.length} />
      </section>

      <Card>
        <SectionLabel>Domain</SectionLabel>
        <div className="flex flex-wrap gap-2 mb-4">
          <Pill active={domain === "all"} onClick={() => setDomain("all")}>all</Pill>
          {domains.map((d) => (
            <Pill key={d} active={domain === d} onClick={() => setDomain(d)}>{d}</Pill>
          ))}
        </div>
        <SectionLabel>Type</SectionLabel>
        <div className="flex flex-wrap gap-2 mb-4">
          {TYPES.map((t) => <Pill key={t} active={type === t} onClick={() => setType(t)}>{t}</Pill>)}
        </div>
        <SectionLabel>Status</SectionLabel>
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => <Pill key={s} active={status === s} onClick={() => setStatus(s)}>{s}</Pill>)}
        </div>
      </Card>

      <Card>
        <SectionLabel>{entries.length} entr{entries.length === 1 ? "y" : "ies"}</SectionLabel>
        {entries.length === 0 ? (
          <Empty>No entries match these filters.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {entries.map((e, i) => (
              <div key={i} className="py-3">
                <div className="flex items-center gap-3 text-sm">
                  <span className="font-medium flex-1 truncate">{e.name ?? "—"}</span>
                  {e.type && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{e.type}</span>}
                  {e.classification && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{e.classification}</span>}
                  {e.status && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{e.status}</span>}
                </div>
                {e.description && <div className="text-xs opacity-60 mt-1 line-clamp-2">{e.description}</div>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </Page>
  );
}
