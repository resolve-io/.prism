import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Page, Card, SectionLabel, Empty, Kpi } from "@/components/ui";

type Task = {
  id?: string;
  title?: string;
  status?: string;
  priority?: string;
  tags?: string[];
  assignee?: string;
};

const COLUMNS: { key: string; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "in_progress", label: "In Progress" },
  { key: "blocked", label: "Blocked" },
  { key: "done", label: "Done" },
];

export default function TasksPage() {
  const [project] = useProject();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [next, setNext] = useState<Task | null>(null);

  const load = useCallback(() => {
    api.get<{ tasks: Task[] }>(`/api/tasks?project=${project}`).then((d) => setTasks(d.tasks)).catch(() => setTasks([]));
    api.get<{ next: Task | null }>(`/api/tasks/next?project=${project}`).then((d) => setNext(d.next)).catch(() => setNext(null));
  }, [project]);

  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t); }, [load]);

  const grouped = COLUMNS.map((c) => ({
    ...c, items: tasks.filter((t) => (t.status ?? "pending") === c.key),
  }));

  return (
    <Page>
      <section className="flex flex-wrap gap-3">
        {COLUMNS.map((c) => (
          <Kpi key={c.key} label={c.label} value={tasks.filter((t) => (t.status ?? "pending") === c.key).length} />
        ))}
      </section>

      <Card>
        <SectionLabel>What's next</SectionLabel>
        {next ? (
          <div className="text-sm">
            <div className="font-medium">{next.title ?? next.id}</div>
            <div className="text-xs opacity-60 mt-1 font-mono">{next.id}</div>
          </div>
        ) : (
          <Empty>Queue is clear.</Empty>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {grouped.map((col) => (
          <Card key={col.key} className="!p-4">
            <div className="flex items-center justify-between mb-3">
              <SectionLabel>{col.label}</SectionLabel>
              <span className="text-xs opacity-50 -mt-3">{col.items.length}</span>
            </div>
            {col.items.length === 0 ? (
              <div className="text-xs opacity-40 text-center py-6">empty</div>
            ) : (
              <div className="space-y-2">
                {col.items.map((t) => (
                  <div key={t.id} className="rounded-md border border-[color:var(--midground-base)]/10 bg-[color:var(--background-base)]/30 p-3 hover:border-[color:var(--midground-base)]/30 transition-colors">
                    <div className="text-sm font-medium">{t.title ?? "—"}</div>
                    <div className="flex items-center gap-2 mt-2">
                      {t.priority && <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{t.priority}</span>}
                      {t.assignee && <span className="text-[10px] opacity-60 font-mono">{t.assignee}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </Page>
  );
}
