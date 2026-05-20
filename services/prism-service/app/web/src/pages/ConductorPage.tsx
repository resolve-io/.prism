import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, Kpi, SectionLabel, Empty } from "@/components/ui";

type Variant = {
  variant_id?: string;
  persona?: string;
  template?: string;
  n_uses?: number;
  mean_score?: number | null;
};

type Retired = Variant & { retired_at?: string; reason?: string };

type State = {
  exploration_rate: number;
  variants: Variant[];
  scores: Record<string, number>;
  session_outcomes: Array<{ ts?: string; variant?: string; score?: number }>;
  retired: Retired[];
};

export default function ConductorPage() {
  const [project] = useProject();
  const [data, setData] = useState<State | null>(null);

  const load = useCallback(() => {
    api.get<State>(`/api/conductor/state?project=${project}`).then(setData).catch(() => setData(null));
  }, [project]);

  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);

  const variants = data?.variants ?? [];
  const retired = data?.retired ?? [];

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        <Kpi label="Active variants" value={variants.length} />
        <Kpi label="Retired" value={retired.length} />
        <Kpi label="Exploration" value={data ? `${Math.round(data.exploration_rate * 100)}%` : "—"} />
      </section>

      <Card>
        <SectionLabel>Active variants</SectionLabel>
        {variants.length === 0 ? (
          <Empty>No variants — conductor hasn't seeded any yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {variants.map((v) => (
              <div key={v.variant_id} className="py-3">
                <div className="flex items-center gap-4 text-sm">
                  <span className="font-mono opacity-80 w-40 truncate">{v.variant_id}</span>
                  <span className="text-xs uppercase tracking-wider opacity-60 w-20">{v.persona ?? "—"}</span>
                  <span className="flex-1 truncate opacity-80">{v.template ?? ""}</span>
                  <span className="text-xs opacity-60 w-12 text-right">n={v.n_uses ?? 0}</span>
                  <span className="font-mono w-20 text-right">{v.mean_score?.toFixed?.(3) ?? "—"}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {retired.length > 0 && (
        <Card>
          <SectionLabel>Retired</SectionLabel>
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {retired.map((v) => (
              <div key={v.variant_id} className="py-2 flex items-center gap-4 text-sm">
                <span className="font-mono opacity-70 w-40 truncate">{v.variant_id}</span>
                <span className="text-xs opacity-60 w-32 truncate">{v.retired_at ?? ""}</span>
                <span className="flex-1 truncate text-xs opacity-70">{v.reason ?? ""}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </Page>
  );
}
