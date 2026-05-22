/**
 * Live status strip — a thin slate-blue bar at the top of every page
 * that surfaces what PRISM is doing right now. When the analyzer queue
 * is empty the strip is collapsed (zero height); when work is in
 * flight it shows the running analyzer(s) + elapsed time, ticking
 * every second.
 *
 * Persistent across page navigation because it lives inside the Layout
 * shell above <PageHeader>, so the user can wander away from Settings
 * and still see scan progress.
 */
import { useEffect, useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { useScanActivity, type ScanJob } from "@/lib/scan-activity";

export default function LiveStatusStrip() {
  const { isActive, inProgress, pending } = useScanActivity();
  const [now, setNow] = useState(() => Date.now() / 1000);

  // Tick once a second while active so elapsed-time labels update live.
  useEffect(() => {
    if (!isActive) return;
    const t = setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => clearInterval(t);
  }, [isActive]);

  if (!isActive) return null;

  return (
    <div className="border-b border-sky-500/30 bg-sky-500/[0.08] text-sky-100">
      <div className="px-6 py-2 flex items-center gap-3 text-xs">
        <Activity className="w-3.5 h-3.5 animate-pulse text-sky-300 shrink-0" />
        <span className="uppercase tracking-wider text-[10px] opacity-80">
          Scanning
        </span>
        <div className="flex items-center gap-4 flex-wrap min-w-0">
          {inProgress.length === 0 ? (
            <span className="opacity-80">
              {pending} job{pending === 1 ? "" : "s"} queued — waiting for drainer
            </span>
          ) : (
            inProgress.map((j) => (
              <RunningJobBadge key={j.id} job={j} now={now} />
            ))
          )}
        </div>
        {inProgress.length > 0 && pending > 0 && (
          <span className="opacity-60 ml-auto whitespace-nowrap">
            +{pending} queued
          </span>
        )}
      </div>
    </div>
  );
}

function RunningJobBadge({ job, now }: { job: ScanJob; now: number }) {
  const elapsed = job.started_at > 0 ? Math.max(0, now - job.started_at) : 0;
  return (
    <span className="inline-flex items-center gap-2 min-w-0">
      <Loader2 className="w-3 h-3 animate-spin shrink-0" />
      <span className="font-mono opacity-90 truncate">{job.analyzer}</span>
      <span className="opacity-60 truncate">
        on <span className="font-mono">{job.project}</span>
      </span>
      <span className="opacity-60 tabular-nums">{elapsed.toFixed(0)}s</span>
    </span>
  );
}
