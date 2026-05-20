import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, Kpi, SectionLabel, Empty } from "@/components/ui";

type Outcome = {
  session_id?: string;
  ts?: string;
  tokens?: number;
  duration_ms?: number;
  files_touched?: number;
  outcome?: string;
};

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
    api.get<{ outcomes: Outcome[]; skill_usage: SkillRow[] }>(`/api/sessions?project=${project}&limit=50`)
      .then((d) => { setOutcomes(d.outcomes); setSkills(d.skill_usage); })
      .catch(() => { setOutcomes([]); setSkills([]); });
  }, [project]);

  useEffect(() => {
    load();
    const es = new EventSource(`/sse/sessions?project=${project}`);
    es.onmessage = () => load();
    return () => es.close();
  }, [project, load]);

  const tokens = outcomes.map((o) => o.tokens ?? 0).filter(Boolean);
  const durs = outcomes.map((o) => o.duration_ms ?? 0).filter(Boolean);
  const files = outcomes.map((o) => o.files_touched ?? 0).filter(Boolean);
  const totalFiles = files.reduce((a, b) => a + b, 0) || 1;
  const totalTokens = tokens.reduce((a, b) => a + b, 0);

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        <Kpi label="Sessions" value={outcomes.length} />
        <Kpi label="Median tokens" value={Math.round(median(tokens)).toLocaleString()} />
        <Kpi label="p95 tokens" value={Math.round(p95(tokens)).toLocaleString()} />
        <Kpi label="Tokens / file" value={Math.round(totalTokens / totalFiles).toLocaleString()} />
        <Kpi label="Median duration" value={`${Math.round(median(durs) / 1000)}s`} />
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
            {outcomes.map((o, i) => (
              <div key={o.session_id ?? i} className="py-2 flex items-center gap-4 text-sm">
                <span className="font-mono opacity-70 w-44 text-xs truncate">{o.ts ?? ""}</span>
                <span className="font-mono opacity-80 flex-1 truncate">{o.session_id ?? "—"}</span>
                <span className="text-xs opacity-60 w-20 text-right">{(o.tokens ?? 0).toLocaleString()}</span>
                <span className="text-xs opacity-60 w-16 text-right">{Math.round((o.duration_ms ?? 0) / 1000)}s</span>
                <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70 w-20 text-center">{o.outcome ?? "—"}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Page>
  );
}
