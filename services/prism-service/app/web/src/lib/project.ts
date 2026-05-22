/**
 * Active-project hook. Persists in localStorage; broadcasts changes across
 * components via a tiny pub-sub so the header selector and pages stay in sync.
 *
 * Also exposes `notifyProjectsChanged()` so creators/deleters (SettingsPage)
 * can prod the header to re-fetch /api/projects — otherwise the picker stays
 * stale until a page reload.
 */
import { useEffect, useState } from "react";

const KEY = "prism.project";
const listeners = new Set<(p: string) => void>();
const listChangeListeners = new Set<() => void>();

export function getProject(): string {
  return localStorage.getItem(KEY) || "default";
}

export function setProject(p: string) {
  localStorage.setItem(KEY, p);
  listeners.forEach((fn) => fn(p));
}

export function useProject(): [string, (p: string) => void] {
  const [p, setP] = useState<string>(getProject);
  useEffect(() => {
    const fn = (v: string) => setP(v);
    listeners.add(fn);
    return () => { listeners.delete(fn); };
  }, []);
  return [p, setProject];
}

/**
 * Fire to tell every subscriber (e.g. the PageHeader picker) that the
 * /api/projects list may have changed — they should re-fetch.
 */
export function notifyProjectsChanged(): void {
  listChangeListeners.forEach((fn) => {
    try { fn(); } catch { /* swallow — UI subscriber crash shouldn't fan out */ }
  });
}

/** Subscribe to projects-list-changed events. Unsubscribes on unmount. */
export function useProjectsListChange(onChange: () => void): void {
  useEffect(() => {
    listChangeListeners.add(onChange);
    return () => { listChangeListeners.delete(onChange); };
  }, [onChange]);
}
