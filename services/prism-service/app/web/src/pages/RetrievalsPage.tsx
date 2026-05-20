import { useEffect, useState, useCallback } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, SectionLabel, Empty } from "@/components/ui";

type Hit = {
  doc_id: string;
  rrf_score?: number | null;
  rerank_score?: number | null;
  domain?: string | null;
  entity_name?: string | null;
};

type SearchRow = {
  id: number;
  ts?: string;
  query: string;
  mode?: string;
  rerank?: string;
  latency_ms?: number;
  n_results?: number;
  final_top?: string; // JSON-encoded Hit[]
};

function parseHits(raw: string | undefined): Hit[] {
  if (!raw) return [];
  try { return JSON.parse(raw) as Hit[]; } catch { return []; }
}

export default function RetrievalsPage() {
  const [project] = useProject();
  const [rows, setRows] = useState<SearchRow[]>([]);

  const load = useCallback(() => {
    api.get<{ searches: SearchRow[] }>(`/api/retrievals?project=${project}&limit=50`)
      .then((d) => setRows(d.searches))
      .catch(() => setRows([]));
  }, [project]);

  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);

  const rate = useCallback((search_id: number, doc_id: string, signal: "up" | "down") => {
    const params = new URLSearchParams({
      search_id: String(search_id), doc_id, signal, project,
    });
    api.post(`/api/retrievals/feedback?${params}`, {}).then(load);
  }, [project, load]);

  return (
    <Page>
      <Card>
        <SectionLabel>Recent retrievals</SectionLabel>
        {rows.length === 0 ? (
          <Empty>No retrievals recorded yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {rows.map((r) => {
              const hits = parseHits(r.final_top);
              return (
                <div key={r.id} className="py-3">
                  <div className="flex items-start gap-4 text-sm">
                    <span className="flex-1 truncate font-medium">{r.query}</span>
                    <span className="text-xs opacity-60 font-mono whitespace-nowrap">{r.n_results ?? 0} hits</span>
                    <span className="text-xs opacity-60 font-mono whitespace-nowrap">{r.latency_ms ?? 0}ms</span>
                    {r.mode && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{r.mode}</span>}
                    {r.rerank && r.rerank !== "off" && <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">rerank: {r.rerank}</span>}
                  </div>
                  {r.ts && <div className="text-[10px] uppercase tracking-wider opacity-40 mt-1 font-mono">{r.ts}</div>}
                  {hits.length > 0 && (
                    <div className="mt-2 pl-4 space-y-1">
                      {hits.slice(0, 3).map((h, i) => (
                        <div key={`${r.id}-${i}-${h.doc_id}`} className="flex items-center gap-3 text-xs">
                          <span className="font-mono opacity-70 flex-1 truncate">{h.doc_id}</span>
                          <span className="opacity-60 w-12 text-right">{h.rrf_score?.toFixed?.(3) ?? ""}</span>
                          <button onClick={() => rate(r.id, h.doc_id, "up")} className="p-1 rounded hover:bg-[color:var(--midground-base)]/10" title="Mark as useful"><ThumbsUp className="w-3 h-3" /></button>
                          <button onClick={() => rate(r.id, h.doc_id, "down")} className="p-1 rounded hover:bg-[color:var(--midground-base)]/10" title="Mark as not useful"><ThumbsDown className="w-3 h-3" /></button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </Page>
  );
}
