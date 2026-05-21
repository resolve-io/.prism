import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, Kpi, SectionLabel, Empty } from "@/components/ui";

// Mirrors what conductor_service.get_session_outcomes() returns. The
// keys are DB columns (snake_case_with_units) — the page renders the
// scored sessions from scores.db, not raw transcripts.
type Outcome = {
  session_id?: string;
  timestamp?: string;          // ISO-ish; "recorded_at" is the same field
  recorded_at?: string;
  tokens?: number;             // alias of tokens_used
  tokens_used?: number;
  duration?: number;           // seconds (alias of duration_s)
  duration_s?: number;
  files_read?: number;
  files_modified?: number;
  skills_invoked?: number;
  tokens_per_file?: number | null;
};

// Per-event skill_usage rows from scores.db (id/session_id/skill_name/
// timestamp). Aggregated to {skill, count} on the client so a single
// API call powers both the table and the chart.
type SkillEvent = { id: number; session_id: string; skill_name: string; timestamp: string };
type SkillRow = { skill: string; count: number };

function median(xs: number[]) {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function p95(xs: number[]) {
  if (!xs.length) return 0;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(s.length * 0.95))];
}

export default function SessionsPage() {
  const [project] = useProject();
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [skills, setSkills] = useState<SkillRow[]>([]);

  const load = useCallback(() => {
    api.get<{ outcomes: Outcome[]; skill_usage: SkillEvent[] }>(`/api/sessions?project=${project}&limit=50`)
      .then((d) => {
        setOutcomes(d.outcomes);
        const counts = new Map<string, number>();
        for (const ev of d.skill_usage ?? []) {
          const k = ev.skill_name || "(unknown)";
          counts.set(k, (counts.get(k) ?? 0) + 1);
        }
        setSkills([...counts.entries()]
          .map(([skill, count]) => ({ skill, count }))
          .sort((a, b) => b.count - a.count));
      })
      .catch(() => { setOutcomes([]); setSkills([]); });
  }, [project]);

  useEffect(() => {
    load();
    const es = new EventSource(`/sse/sessions?project=${project}`);
    es.onmessage = () => load();
    return () => es.close();
  }, [project, load]);

  const tokens = outcomes.map((o) => o.tokens ?? o.tokens_used ?? 0).filter(Boolean);
  // API returns duration in SECONDS (column duration_s aliased to "duration").
  const durSec = outcomes.map((o) => o.duration ?? o.duration_s ?? 0).filter(Boolean);
  const files = outcomes.map((o) => o.files_modified ?? 0).filter(Boolean);
  const totalFiles = files.reduce((a, b) => a + b, 0) || 1;
  const totalTokens = tokens.reduce((a, b) => a + b, 0);
  const fmtTs = (s?: string) =>
    s ? s.replace("T", " ").replace(/\.\d+/, "").slice(0, 19) : "";

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        <Kpi label="Sessions" value={outcomes.length} />
        <Kpi label="Median tokens" value={Math.round(median(tokens)).toLocaleString()} />
        <Kpi label="p95 tokens" value={Math.round(p95(tokens)).toLocaleString()} />
        <Kpi label="Tokens / file" value={Math.round(totalTokens / totalFiles).toLocaleString()} />
        <Kpi label="Median duration" value={`${Math.round(median(durSec))}s`} />
      </section>

      <Card>
        <SectionLabel>Skill usage</SectionLabel>
        {skills.length === 0 ? (
          <Empty>No skills invoked yet in scored sessions.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {skills.map((s) => (
              <div key={s.skill} className="py-2 flex items-center gap-4 text-sm">
                <span className="flex-1 font-mono opacity-80">{s.skill}</span>
                <span className="font-mono opacity-70">{s.count}</span>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <SectionLabel>Recent sessions</SectionLabel>
        {outcomes.length === 0 ? (
          <Empty>No session outcomes yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {outcomes.map((o, i) => {
              const tk = o.tokens ?? o.tokens_used ?? 0;
              const d = o.duration ?? o.duration_s ?? 0;
              const fm = o.files_modified ?? 0;
              const fr = o.files_read ?? 0;
              return (
                <div key={o.session_id ?? i} className="py-2 flex items-center gap-4 text-sm">
                  <span className="font-mono opacity-70 w-40 text-xs truncate" title={o.timestamp ?? o.recorded_at ?? ""}>
                    {fmtTs(o.timestamp ?? o.recorded_at)}
                  </span>
                  <span className="font-mono opacity-80 flex-1 truncate" title={o.session_id ?? ""}>
                    {o.session_id ?? "—"}
                  </span>
                  <span className="text-xs opacity-60 w-20 text-right" title="tokens used">
                    {tk.toLocaleString()}
                  </span>
                  <span className="text-xs opacity-60 w-16 text-right" title="duration (s)">
                    {Math.round(d)}s
                  </span>
                  <span className="text-xs opacity-60 w-24 text-right" title="files read / modified">
                    {fr}r · {fm}w
                  </span>
                  <span className="text-xs opacity-60 w-20 text-right" title="tokens / file modified">
                    {o.tokens_per_file ? `${o.tokens_per_file.toLocaleString()}/file` : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </Page>
  );
}
