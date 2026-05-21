import { useState, useEffect, useCallback } from "react";
import { Search, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type BrainStatus = {
  doc_count?: number;
  entity_count?: number;
  vector_enabled?: boolean;
  last_reindex?: string | null;
};

type SearchResult = {
  entity_name?: string;
  entity_kind?: string;
  domain?: string;
  file?: string;
  source?: string;
  rrf_score?: number;
  score?: number;
};

const DOMAINS = ["all", "py", "ts", "js", "md", "expertise"];

function Kpi({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex-1 min-w-[150px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 p-4">
      <div className="text-[10px] uppercase tracking-wider opacity-60 mb-2">{label}</div>
      <div className="text-2xl font-semibold leading-none">{value}</div>
    </div>
  );
}

export default function BrainPage() {
  const [project] = useState("default");
  const [status, setStatus] = useState<BrainStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState<string>("all");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  const loadStatus = useCallback(() => {
    api.get<BrainStatus>(`/api/brain/status?project=${project}`)
      .then(s => { setStatus(s); setStatusError(null); })
      .catch(e => setStatusError(String(e)));
  }, [project]);

  useEffect(loadStatus, [loadStatus]);

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const params = new URLSearchParams({ q: query.trim(), project, limit: "20" });
      if (domain !== "all") params.set("domain", domain);
      const data = await api.get<{ results: SearchResult[] }>(`/api/brain/search?${params}`);
      setResults(data.results);
    } catch { setResults([]); } finally { setSearching(false); }
  }, [query, domain, project]);

  const doReindex = useCallback(async () => {
    setReindexing(true);
    try { await api.post(`/api/brain/reindex?project=${project}`, {}); loadStatus(); }
    catch { /* surface via status error */ } finally { setReindexing(false); }
  }, [project, loadStatus]);

  return (
    <div className="p-8 space-y-6 w-full min-w-[720px]">
      <section className="flex flex-wrap gap-3">
        <Kpi label="Documents" value={status?.doc_count ?? "—"} />
        <Kpi label="Entities" value={status?.entity_count ?? "—"} />
        <Kpi label="Vectors" value={
          status?.vector_enabled === undefined ? "—"
            : <span className={cn("text-base px-2 py-1 rounded-md",
                status.vector_enabled
                  ? "bg-emerald-500/15 text-emerald-300"
                  : "bg-rose-500/15 text-rose-300")}>
                {status.vector_enabled ? "Enabled" : "Disabled"}
              </span>} />
        <Kpi label="Last Reindex" value={
          <span className="font-mono text-sm">{String(status?.last_reindex ?? "—").slice(0,19)}</span>} />
        <button
          onClick={doReindex}
          disabled={reindexing}
          className="self-stretch min-w-[150px] rounded-md border border-[color:var(--midground-base)]/30 bg-[color:var(--midground-base)]/5 hover:bg-[color:var(--midground-base)]/10 px-4 transition-colors flex items-center justify-center gap-2 text-sm uppercase tracking-wider disabled:opacity-50"
        >
          <RefreshCw className={cn("w-4 h-4", reindexing && "animate-spin")} />
          {reindexing ? "Reindexing…" : "Reindex"}
        </button>
      </section>
      {statusError && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-4 py-3 text-sm">
          Brain status unreachable — is the PRISM service running on :7777? <span className="opacity-60">({statusError.slice(0, 120)})</span>
        </div>
      )}

      <section className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 p-5">
        <div className="text-[10px] uppercase tracking-wider opacity-60 mb-3">Search the knowledge base</div>
        <div className="flex gap-3">
          <div className="flex-1 flex items-center gap-2 rounded-md border border-[color:var(--midground-base)]/20 bg-[color:var(--background-base)]/50 px-3 py-2">
            <Search className="w-4 h-4 opacity-60" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && doSearch()}
              placeholder="Search concepts, entities, files…"
              className="flex-1 bg-transparent outline-none text-sm placeholder:opacity-40"
            />
          </div>
          <button
            onClick={doSearch}
            disabled={searching || !query.trim()}
            className="px-5 rounded-md border border-[color:var(--midground-base)]/30 bg-[color:var(--midground-base)]/10 hover:bg-[color:var(--midground-base)]/20 text-sm uppercase tracking-wider disabled:opacity-40 transition-colors"
          >
            {searching ? "Searching…" : "Search"}
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {DOMAINS.map((d) => (
            <button key={d} onClick={() => setDomain(d)}
              className={cn(
                "px-3 py-1 rounded-full text-[11px] uppercase tracking-wider transition-colors",
                domain === d
                  ? "bg-[color:var(--midground-base)] text-[color:var(--background-base)]"
                  : "bg-[color:var(--midground-base)]/10 text-[color:var(--midground-base)]/70 hover:bg-[color:var(--midground-base)]/20"
              )}>{d}</button>
          ))}
        </div>
      </section>

      {results && (
        <section>
          <div className="text-[10px] uppercase tracking-wider opacity-60 mb-3">
            {results.length} result{results.length === 1 ? "" : "s"}
          </div>
          <div className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 divide-y divide-[color:var(--midground-base)]/10">
            {results.length === 0 && (
              <div className="px-5 py-8 text-center text-sm opacity-60">No matches.</div>
            )}
            {results.map((r, i) => {
              const score = r.rrf_score ?? r.score ?? 0;
              return (
                <div key={i} className="px-5 py-3 flex items-start gap-4 hover:bg-[color:var(--midground-base)]/5 transition-colors">
                  <div className="w-8 text-xs opacity-50 font-mono pt-0.5">{i + 1}</div>
                  <div className="w-16 text-xs font-mono opacity-70 pt-0.5">{score ? score.toFixed(3) : "—"}</div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{r.entity_name ?? "—"}</div>
                    <div className="text-xs opacity-60 truncate font-mono mt-0.5">{r.file ?? r.source ?? ""}</div>
                  </div>
                  {r.entity_kind && (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{r.entity_kind}</span>
                  )}
                  {r.domain && (
                    <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{r.domain}</span>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
