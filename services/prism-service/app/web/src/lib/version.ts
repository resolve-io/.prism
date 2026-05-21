/**
 * useVersion — reads the live service version from /api/version.
 *
 * The string is owned by app/__version__.py.PRISM_VERSION; the
 * Sidebar footer and the Settings page both consume this hook so
 * the version label can't drift between them. Result is cached
 * module-scope after the first fetch — version doesn't change
 * mid-session, so re-fetching on every mount is wasted.
 *
 * On first use we also open an SSE stream to /sse/live. The server
 * emits its current version on connect; EventSource auto-reconnects
 * when the backend restarts (Watchtower swap), so the post-swap
 * reconnect surfaces a new version → we force-reload the page so
 * the user picks up the new bundle without having to hard-refresh.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type ServiceVersion = { version: string; notes: string };

let cached: ServiceVersion | null = null;
let inflight: Promise<ServiceVersion> | null = null;
let watchdogStarted = false;

function startLiveWatchdog() {
  if (watchdogStarted || typeof window === "undefined") return;
  watchdogStarted = true;
  let initial: string | null = null;
  const es = new EventSource("/sse/live");
  es.onmessage = (ev) => {
    try {
      const v = (JSON.parse(ev.data) as { version?: string }).version;
      if (!v) return;
      if (initial === null) {
        initial = v;
      } else if (v !== initial) {
        window.location.reload();
      }
    } catch {
      /* ignore malformed payloads */
    }
  };
}

export function useVersion(): ServiceVersion | null {
  const [v, setV] = useState<ServiceVersion | null>(cached);
  useEffect(() => {
    startLiveWatchdog();
    if (cached) return;
    if (!inflight) {
      inflight = api.get<ServiceVersion>("/api/version")
        .then((r) => { cached = r; return r; })
        .finally(() => { inflight = null; });
    }
    inflight.then((r) => setV(r)).catch(() => {});
  }, []);
  return v;
}
