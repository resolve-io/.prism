import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Kpi, Card, SectionLabel, Empty } from "@/components/ui";

type QueueRow = { state: string; count: number };
type Brief = { brief_id: string; age_hours: number; retry_count: number };
type Run = { ran_at: string; outcome: string; narrative?: string };

export default function ConsolidationPage() {
  const [project] = useProject();
  const [queue, setQueue] = useState<QueueRow[]>([]);
  const [unreflected, setUnreflected] = useState<Brief[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);

  useEffect(() => {
    api.get<{ queue: QueueRow[]; unreflected: Brief[]; recent_runs: Run[] }>(
      `/api/consolidation?project=${project}`,
    ).then((d) => { setQueue(d.queue); setUnreflected(d.unreflected); setRuns(d.recent_runs); })
     .catch(() => { setQueue([]); setUnreflected([]); setRuns([]); });
  }, [project]);

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        {queue.length === 0 && <Kpi label="Queue" value="—" />}
        {queue.map((r) => <Kpi key={r.state} label={r.state} value={r.count} />)}
      </section>

      <Card>
        <SectionLabel>Unreflected briefs &gt; 24h</SectionLabel>
        {unreflected.length === 0 ? (
          <Empty>Nothing pending reflection.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {unreflected.map((b) => (
              <div key={b.brief_id} className="py-2 flex items-center gap-4 text-sm">
                <span className="font-mono opacity-80 flex-1 truncate">{b.brief_id}</span>
                <span className="text-xs opacity-60">retries {b.retry_count}</span>
                <span className="text-xs opacity-60">{b.age_hours.toFixed(1)}h</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <SectionLabel>Recent reflection runs</SectionLabel>
        {runs.length === 0 ? (
          <Empty>No runs yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {runs.map((r, i) => (
              <div key={i} className="py-3 flex items-start gap-4 text-sm">
                <span className="font-mono opacity-70 text-xs w-44 shrink-0">{r.ran_at}</span>
                <span className="text-xs uppercase tracking-wider opacity-70 w-24 shrink-0">{r.outcome}</span>
                {r.narrative && <span className="opacity-80 flex-1">{r.narrative}</span>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </Page>
  );
}
