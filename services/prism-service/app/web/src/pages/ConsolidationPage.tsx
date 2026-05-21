import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Kpi, Card, SectionLabel, Empty } from "@/components/ui";

type QueueRow = { state: string; count: number };
// Mirrors columns from consolidation_candidates (see consolidation_data.
// get_unreflected_briefs). The page formerly assumed { brief_id,
// age_hours, retry_count } — neither of the first two are real columns.
type Brief = {
  id: string;
  task_id?: string | null;
  trigger?: string;
  queued_at?: string;
  last_nudged_at?: string | null;
  retry_count?: number;
};
type Run = {
  id: string;
  candidate_id?: string;
  run_at?: string;
  output_json?: string;
  subagent_type?: string;
  confidence?: number;
  narrative_excerpt?: string;
};

// The /api/consolidation endpoint returns `queue` as an object keyed
// by state ({pending: N, completed: N, ...}), not an array. The page
// renders one Kpi per state, so we flatten to QueueRow[] on receipt
// instead of guarding every render site against the object shape.
function normalizeQueue(q: unknown): QueueRow[] {
  if (Array.isArray(q)) return q as QueueRow[];
  if (q && typeof q === "object") {
    return Object.entries(q as Record<string, number>)
      .map(([state, count]) => ({ state, count: Number(count) || 0 }));
  }
  return [];
}

export default function ConsolidationPage() {
  const [project] = useProject();
  const [queue, setQueue] = useState<QueueRow[]>([]);
  const [unreflected, setUnreflected] = useState<Brief[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const load = () => {
    api.get<{ queue: unknown; unreflected: Brief[]; recent_runs: Run[] }>(
      `/api/consolidation?project=${project}`,
    ).then((d) => {
      setQueue(normalizeQueue(d.queue));
      setUnreflected(d.unreflected ?? []);
      setRuns(d.recent_runs ?? []);
    })
     .catch(() => { setQueue([]); setUnreflected([]); setRuns([]); });
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [project]);

  // Auto-dismiss the notice 5s after it lands so it doesn't stick.
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 5000);
    return () => clearTimeout(t);
  }, [notice]);

  const triggerBackfill = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ created: number; skipped: number; scanned: number }>(
        `/api/consolidation/backfill?project=${project}`, {},
      );
      setNotice(
        `Backfill scanned ${r.scanned} sessions — created ${r.created} new candidate${r.created === 1 ? "" : "s"}, ${r.skipped} already enqueued.`,
      );
      load();
    } catch (e) {
      setNotice(`Backfill failed: ${(e as Error).message ?? e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl tracking-tight">Consolidation</h1>
          <p className="text-sm opacity-60 mt-1">
            Reflection queue — one candidate per session, dispensed to a
            sub-agent for post-hoc review. Populated by the Stop hook on
            session end; backfill if the hook hasn't run yet.
          </p>
        </div>
        <button
          onClick={triggerBackfill}
          disabled={busy}
          className="px-4 py-2 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-xs uppercase tracking-wider disabled:opacity-40"
        >
          {busy ? "Working…" : "Backfill from sessions"}
        </button>
      </div>

      {notice && (
        <div className="fixed bottom-6 right-6 z-40 max-w-[420px] rounded-md border border-[color:var(--midground-base)]/20 bg-[color:var(--background-base)]/95 backdrop-blur-sm shadow-lg px-4 py-3 text-[12px] flex items-start gap-3">
          <span className="flex-1 opacity-90 leading-relaxed">{notice}</span>
          <button
            onClick={() => setNotice(null)}
            className="text-[10px] uppercase tracking-wider opacity-60 hover:opacity-100 shrink-0"
          >
            dismiss
          </button>
        </div>
      )}

      <section className="flex flex-wrap gap-3">
        {queue.length === 0 && <Kpi label="Queue" value="—" />}
        {queue.map((r) => <Kpi key={r.state} label={r.state} value={r.count} />)}
      </section>

      <Card>
        <SectionLabel>Pending briefs</SectionLabel>
        {unreflected.length === 0 ? (
          <Empty>Nothing pending reflection.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {unreflected.map((b) => {
              const ageH = b.queued_at
                ? (Date.now() - new Date(b.queued_at).getTime()) / 3600000
                : 0;
              return (
                <div key={b.id} className="py-2 flex items-center gap-4 text-sm">
                  <span className="font-mono opacity-80 flex-1 truncate" title={b.id}>{b.id}</span>
                  <span className="text-xs opacity-60 w-32 truncate" title={b.trigger ?? ""}>
                    {b.trigger ?? "—"}
                  </span>
                  <span className="text-xs opacity-60 w-24 text-right">retries {b.retry_count ?? 0}</span>
                  <span className="text-xs opacity-60 w-16 text-right">{ageH.toFixed(1)}h</span>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card>
        <SectionLabel>Recent reflection runs</SectionLabel>
        {runs.length === 0 ? (
          <Empty>No runs yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {runs.map((r) => (
              <div key={r.id} className="py-3 flex items-start gap-4 text-sm">
                <span className="font-mono opacity-70 text-xs w-44 shrink-0">{r.run_at ?? ""}</span>
                <span className="text-xs uppercase tracking-wider opacity-70 w-24 shrink-0">
                  {r.subagent_type ?? "—"}
                </span>
                {r.narrative_excerpt && (
                  <span className="opacity-80 flex-1">{r.narrative_excerpt}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </Page>
  );
}
