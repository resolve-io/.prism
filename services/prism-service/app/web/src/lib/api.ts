/**
 * Typed fetch wrapper for PRISM's /api surface.
 *
 * Same-origin in prod (FastAPI serves the SPA). Vite dev proxies /api,
 * /sse, /graph to the PRISM service via vite.config.ts.
 */
export async function fetchJSON<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { accept: "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T = unknown>(p: string) => fetchJSON<T>(p),
  post: <T = unknown>(p: string, body: unknown) =>
    fetchJSON<T>(p, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  delete: <T = unknown>(p: string) =>
    fetchJSON<T>(p, { method: "DELETE" }),
};
