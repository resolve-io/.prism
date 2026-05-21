/**
 * useVersion — reads the live service version from /api/version.
 *
 * The string is owned by app/__version__.py.PRISM_VERSION; the
 * Sidebar footer and the Settings page both consume this hook so
 * the version label can't drift between them. Result is cached
 * module-scope after the first fetch — version doesn't change
 * mid-session, so re-fetching on every mount is wasted.
 */
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export type ServiceVersion = { version: string; notes: string };

let cached: ServiceVersion | null = null;
let inflight: Promise<ServiceVersion> | null = null;

export function useVersion(): ServiceVersion | null {
  const [v, setV] = useState<ServiceVersion | null>(cached);
  useEffect(() => {
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
