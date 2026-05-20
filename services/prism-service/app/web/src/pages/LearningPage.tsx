import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, SectionLabel, Empty } from "@/components/ui";

type Row = {
  task_id?: string;
  composite_score?: number;
  layer_a_score?: number;
  variant?: string;
  scored_at?: string;
};

type Variant = { variant: string; n: number; mean_score: number };

export default function LearningPage() {
  const [project] = useProject();
  const [rows, setRows] = useState<Row[]>([]);
  const [variants, setVariants] = useState<Variant[]>([]);

  useEffect(() => {
    api.get<{ rows: Row[]; variants: Variant[] }>(`/api/learning?project=${project}`)
      .then((d) => { setRows(d.rows); setVariants(d.variants); })
      .catch(() => { setRows([]); setVariants([]); });
  }, [project]);

  const lowN = variants.length > 0 && variants.every((v) => v.n < 20);

  return (
    <Page>
      <Card>
        <SectionLabel>Variant performance</SectionLabel>
        {variants.length === 0 ? (
          <Empty>No variant scores yet — needs scored task outcomes.</Empty>
        ) : (
          <>
            {lowN && (
              <div className="mb-3 text-[11px] uppercase tracking-wider text-amber-300/80">
                Correlational only — every variant has n &lt; 20.
              </div>
            )}
            <div className="divide-y divide-[color:var(--midground-base)]/10">
              {variants.map((v) => (
                <div key={v.variant} className="py-2 flex items-center gap-4 text-sm">
                  <span className="font-mono opacity-80 flex-1">{v.variant}</span>
                  <span className="text-xs opacity-60 w-20 text-right">n={v.n}</span>
                  <span className="font-mono w-24 text-right">{v.mean_score?.toFixed?.(3) ?? "—"}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      <Card>
        <SectionLabel>Scored tasks (Layer-A)</SectionLabel>
        {rows.length === 0 ? (
          <Empty>No scored tasks yet.</Empty>
        ) : (
          <div className="divide-y divide-[color:var(--midground-base)]/10">
            {rows.map((r, i) => (
              <div key={i} className="py-2 flex items-center gap-4 text-sm">
                <span className="font-mono opacity-80 flex-1 truncate">{r.task_id ?? "—"}</span>
                <span className="text-xs opacity-60 w-32 truncate">{r.variant ?? ""}</span>
                <span className="font-mono w-20 text-right">{r.composite_score?.toFixed?.(3) ?? "—"}</span>
                <span className="text-xs opacity-50 w-40 text-right">{r.scored_at ?? ""}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </Page>
  );
}
