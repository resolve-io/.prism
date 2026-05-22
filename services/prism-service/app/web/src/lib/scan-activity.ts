/**
 * useScanActivity — polls /api/jobs for in-flight + pending analyzer work.
 *
 * Backs two surfaces:
 *   * Sidebar Knowledge nav items pulse blue while anything is in flight.
 *   * LiveStatusStrip across the top of the page shows what's running
 *     and elapsed time.
 *
 * Polls fast (2s) while there is work, slow (10s) while idle, so the
 * UI feels live without DDoS'ing the API when nothing's happening.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type ScanJob = {
  id: string;
  project: string;
  analyzer: string;
  target_sha: string;
  state: "pending" | "in_progress" | "completed" | "failed";
  enqueued_at: number;
  started_at: number;
  completed_at: number;
  attempts: number;
};

export type ScanActivity = {
  isActive: boolean;
  inProgress: ScanJob[];
  pending: number;
  failed: number;
};

const IDLE: ScanActivity = {
  isActive: false, inProgress: [], pending: 0, failed: 0,
};

const POLL_HOT_MS = 2000;
const POLL_COLD_MS = 10000;

export function useScanActivity(): ScanActivity {
  const [state, setState] = useState<ScanActivity>(IDLE);

  useEffect(() => {
    let cancel = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const load = async () => {
      try {
        const r = await api.get<{ jobs: ScanJob[] }>("/api/jobs?limit=200");
        if (cancel) return;
        const inProgress = r.jobs.filter((j) => j.state === "in_progress");
        const pending = r.jobs.filter((j) => j.state === "pending").length;
        const failed = r.jobs.filter((j) => j.state === "failed").length;
        const isActive = inProgress.length > 0 || pending > 0;
        setState({ isActive, inProgress, pending, failed });
        timer = setTimeout(load, isActive ? POLL_HOT_MS : POLL_COLD_MS);
      } catch {
        if (cancel) return;
        timer = setTimeout(load, POLL_COLD_MS);
      }
    };

    load();
    return () => {
      cancel = true;
      if (timer !== null) clearTimeout(timer);
    };
  }, []);

  return state;
}
