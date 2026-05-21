/**
 * Active-project hook. Persists in localStorage; broadcasts changes across
 * components via a tiny pub-sub so the header selector and pages stay in sync.
 */
import { useEffect, useState } from "react";

const KEY = "prism.project";
const listeners = new Set<(p: string) => void>();

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
