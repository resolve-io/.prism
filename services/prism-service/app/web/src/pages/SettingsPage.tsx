import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";
import {
  ChevronDown, ChevronRight, ExternalLink, GitBranch,
  Github, Loader2, Plus, Search, X,
} from "lucide-react";
import { api } from "@/lib/api";
import { notifyProjectsChanged, useProject } from "@/lib/project";
import { Card, Empty, ErrorBanner, Page, SectionLabel } from "@/components/ui";

type SectionId = "projects" | "connections" | "jobs" | "logs" | "service";

const SECTION_META: Record<SectionId, { title: string; description: string }> = {
  projects: {
    title: "Projects",
    description: "Add, configure, sync, and delete tracked repos.",
  },
  connections: {
    title: "Connections",
    description: "Claude OAuth subscription and GitHub access for private-repo clones.",
  },
  jobs: {
    title: "Jobs",
    description: "Analyzer queue across every project — what's in flight, pending, or failed.",
  },
  logs: {
    title: "Logs",
    description: "Every PRISM-initiated claude -p call with timing, tokens, and assistant output.",
  },
  service: {
    title: "Service",
    description: "Container name, version, intervals, MCP endpoint.",
  },
};

const KNOWN_SECTIONS: SectionId[] = ["projects", "connections", "jobs", "logs", "service"];

function resolveSection(raw: string | undefined): SectionId {
  // `/settings/auth` is the legacy v5.1.8 URL for what's now Connections.
  // Keep it working so bookmarked links don't 404.
  if (raw === "auth") return "connections";
  return (raw && (KNOWN_SECTIONS as string[]).includes(raw)) ? (raw as SectionId) : "projects";
}

type QueueCounts = {
  pending: number;
  in_progress: number;
  completed: number;
  failed: number;
};

type ProjectInfo = {
  name: string;
  remote_url: string | null;
  tracked_ref: string | null;
  current_sha: string | null;
  last_analyzed_sha: string | null;
  queue: QueueCounts;
};

const ZERO_QUEUE: QueueCounts = { pending: 0, in_progress: 0, completed: 0, failed: 0 };

async function fetchInfo(name: string): Promise<ProjectInfo> {
  const s = await api.get<{
    tracked_ref: string;
    remote_url: string | null;
    current_sha: string | null;
    last_analyzed_sha: string | null;
    queue: QueueCounts | null;
  }>(`/api/understand?project=${encodeURIComponent(name)}`);
  return {
    name,
    remote_url: s.remote_url ?? null,
    tracked_ref: s.tracked_ref ?? null,
    current_sha: s.current_sha ?? null,
    last_analyzed_sha: s.last_analyzed_sha ?? null,
    queue: s.queue ?? ZERO_QUEUE,
  };
}

function isDrifted(info: ProjectInfo | undefined): boolean {
  if (!info?.current_sha) return false;
  if (!info.last_analyzed_sha) return Boolean(info.remote_url);
  return info.current_sha !== info.last_analyzed_sha;
}

function queueIsBusy(q: QueueCounts | undefined): boolean {
  if (!q) return false;
  return q.pending > 0 || q.in_progress > 0;
}


export default function SettingsPage() {
  const [active, setActive] = useProject();
  const [projects, setProjects] = useState<string[]>([]);
  const [infos, setInfos] = useState<Record<string, ProjectInfo>>({});
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    try {
      const r = await api.get<{ projects: string[] }>("/api/projects");
      setProjects(r.projects);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    }
  }, []);

  const loadAllInfos = useCallback(async (names: string[]) => {
    const rows = await Promise.all(
      names.map((n) => fetchInfo(n).catch(() => null)),
    );
    setInfos((prev) => {
      const next = { ...prev };
      rows.forEach((r, i) => { if (r) next[names[i]] = r; });
      return next;
    });
  }, []);

  const reloadOne = useCallback(async (name: string) => {
    try {
      const info = await fetchInfo(name);
      setInfos((prev) => ({ ...prev, [name]: info }));
    } catch {
      // ignore — card stays with last known data
    }
  }, []);

  useEffect(() => { loadProjects(); }, [loadProjects]);
  useEffect(() => {
    if (projects.length > 0) loadAllInfos(projects);
  }, [projects, loadAllInfos]);


  const { section: sectionParam } = useParams<{ section?: string }>();
  const section: SectionId = resolveSection(sectionParam);
  const meta = SECTION_META[section];

  return (
    <Page>
      <div>
        <h1 className="font-serif text-3xl tracking-tight">{meta.title}</h1>
        <p className="text-sm opacity-60 mt-1">{meta.description}</p>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {section === "projects" && (
        <Card>
          <SectionLabel>Projects</SectionLabel>
          <NewProjectRow onCreated={async (name) => {
            await loadProjects();
            await reloadOne(name);
            setActive(name);
            notifyProjectsChanged();
          }} />
          {projects.length === 0 ? (
            <Empty>No projects yet — create one above.</Empty>
          ) : (
            <ul className="divide-y divide-[color:var(--midground-base)]/10">
              {projects.map((p) => (
                <ProjectCard
                  key={p}
                  info={infos[p]}
                  name={p}
                  isActive={p === active}
                  onActivate={() => setActive(p)}
                  onSaved={() => reloadOne(p)}
                  onDeleted={async () => {
                    setInfos((prev) => {
                      const next = { ...prev };
                      delete next[p];
                      return next;
                    });
                    if (p === active) setActive("default");
                    await loadProjects();
                    notifyProjectsChanged();
                  }}
                />
              ))}
            </ul>
          )}
        </Card>
      )}

      {section === "connections" && (
        <div className="space-y-6">
          <Card>
            <SectionLabel>Claude</SectionLabel>
            <ClaudeAuthCard />
          </Card>
          <Card>
            <SectionLabel>GitHub</SectionLabel>
            <GithubAuthCard />
          </Card>
        </div>
      )}

      {section === "jobs" && (
        <Card>
          <SectionLabel>Jobs</SectionLabel>
          <JobsPanel />
        </Card>
      )}

      {section === "logs" && (
        <Card>
          <SectionLabel>Logs</SectionLabel>
          <ClaudeRunsPanel />
        </Card>
      )}

      {section === "service" && (
        <Card>
          <SectionLabel>Service</SectionLabel>
          <ServiceInfoPanel />
        </Card>
      )}
    </Page>
  );
}


type ClaudeAuthStatus = {
  authenticated: boolean;
  config_dir: string;
  credentials_path: string;
  container: string;
  login_command: string;
  instructions: string;
};

function ClaudeAuthCard() {
  const [status, setStatus] = useState<ClaudeAuthStatus | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    api.get<ClaudeAuthStatus>("/api/claude-auth/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => { load(); }, [load]);
  // Poll while not authenticated so the card flips to "authenticated"
  // as soon as the operator's docker-exec login completes.
  useEffect(() => {
    if (status?.authenticated) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [status?.authenticated, load]);

  if (!status) {
    return <div className="text-sm opacity-60">Loading…</div>;
  }

  if (status.authenticated) {
    return (
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 text-sm">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-200 text-[9px] uppercase tracking-wider">
            authenticated
          </span>
          <span className="opacity-70">
            Claude CLI is logged in. The drainer can run analyzers.
          </span>
        </div>
        <div className="text-[11px] opacity-50 font-mono">
          credentials → {status.credentials_path}
        </div>
      </div>
    );
  }

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(status.login_command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore clipboard failures
    }
  };

  return (
    <div className="space-y-3">
      <div className="inline-flex items-center gap-2 text-sm">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-200 text-[9px] uppercase tracking-wider">
          not authenticated
        </span>
        <span className="opacity-70">
          Run this once on the host to complete OAuth:
        </span>
      </div>
      <div className="flex items-center gap-2">
        <code className="flex-1 px-3 py-2 rounded-md bg-[color:var(--midground-base)]/[0.04] border border-[color:var(--midground-base)]/15 text-xs font-mono select-all break-all">
          {status.login_command}
        </code>
        <button
          type="button"
          onClick={copy}
          className="px-3 py-2 rounded-md border border-[color:var(--midground-base)]/30 text-[10px] uppercase tracking-wider hover:bg-[color:var(--midground-base)]/10"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <p className="text-[11px] opacity-60 leading-snug">
        {status.instructions} This panel polls every 5 seconds and will flip
        to <span className="font-mono">authenticated</span> automatically as
        soon as the OAuth flow completes.
      </p>
    </div>
  );
}


type GithubAuthStatus = {
  authenticated: boolean;
  credentials_path: string;
  fingerprint: string;
  instructions: string;
  // OAuth metadata — empty when the active token came from the PAT path.
  login: string;
  avatar_url: string;
  scopes: string;
  connected_at: number;
  // Device-flow setup state — drives the first-time-setup vs Connect button choice.
  client_id_configured: boolean;
  client_id_preview: string;
  register_url: string;
};

type DeviceCode = {
  flow_id: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
};

type DevicePoll =
  | { status: "pending"; interval?: number }
  | { status: "success"; login: string }
  | { status: "expired" }
  | { status: "denied" }
  | { status: "error"; error: string };

type GhRepo = {
  full_name: string;
  name: string;
  owner: string;
  private: boolean;
  default_branch: string;
  description: string;
  clone_url: string;
  html_url: string;
  pushed_at: string;
  stargazers_count: number;
};

function GithubAuthCard() {
  const [status, setStatus] = useState<GithubAuthStatus | null>(null);
  const [device, setDevice] = useState<DeviceCode | null>(null);
  const [showPat, setShowPat] = useState(false);
  const [showClientIdSetup, setShowClientIdSetup] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api.get<GithubAuthStatus>("/api/github-auth/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => { load(); }, [load]);

  const startDeviceFlow = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const code = await api.post<DeviceCode>("/api/github-auth/device/start", {});
      setDevice(code);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  const disconnect = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const next = await api.post<GithubAuthStatus>("/api/github-auth/clear", {});
      setStatus(next);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  if (!status) {
    return <div className="text-sm opacity-60">Loading…</div>;
  }

  if (status.authenticated) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          {status.avatar_url ? (
            <img
              src={status.avatar_url}
              alt={status.login}
              className="w-10 h-10 rounded-full border border-[color:var(--midground-base)]/20"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-[color:var(--midground-base)]/10 flex items-center justify-center">
              <Github className="w-5 h-5 opacity-70" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-200 text-[9px] uppercase tracking-wider">
                connected
              </span>
              <span className="text-sm font-semibold">
                {status.login || status.fingerprint || "GitHub"}
              </span>
            </div>
            <div className="text-[11px] opacity-60 mt-0.5">
              {status.scopes
                ? <>scopes: <span className="font-mono">{status.scopes}</span></>
                : status.fingerprint
                  ? <>using <span className="font-mono">{status.fingerprint}</span> (PAT)</>
                  : "PRISM can clone private GitHub repos"}
            </div>
          </div>
        </div>
        {error && (
          <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
            {error}
          </div>
        )}
        <button
          type="button"
          onClick={disconnect}
          disabled={submitting}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-[color:var(--midground-base)]/30 text-[11px] uppercase tracking-wider hover:bg-[color:var(--midground-base)]/10 disabled:opacity-40"
        >
          {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
          {submitting ? "Disconnecting…" : "Disconnect"}
        </button>
      </div>
    );
  }

  // Not connected — three sub-states drive the visual:
  //   1. no client_id    → first-time setup card with deep link to register
  //   2. client_id ok    → big "Connect with GitHub" button (device flow)
  //   3. PAT fallback    → collapsed by default, expandable
  return (
    <div className="space-y-3">
      <div className="inline-flex items-center gap-2 text-sm">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-200 text-[9px] uppercase tracking-wider">
          not connected
        </span>
        <span className="opacity-70">
          Connect once — PRISM uses the token for every clone after that.
        </span>
      </div>

      {!status.client_id_configured || showClientIdSetup ? (
        <ClientIdSetup
          status={status}
          onSaved={() => { setShowClientIdSetup(false); load(); }}
          onCancel={status.client_id_configured ? () => setShowClientIdSetup(false) : undefined}
        />
      ) : (
        <button
          type="button"
          onClick={startDeviceFlow}
          disabled={submitting}
          className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-sm uppercase tracking-wider disabled:opacity-30 hover:opacity-90"
        >
          {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Github className="w-4 h-4" />}
          {submitting ? "Starting…" : "Connect with GitHub"}
        </button>
      )}

      {status.client_id_configured && !showClientIdSetup && (
        <div className="text-[11px] opacity-50 flex items-center gap-2">
          <span>OAuth App ID: <span className="font-mono">{status.client_id_preview}</span></span>
          <button
            type="button"
            onClick={() => setShowClientIdSetup(true)}
            className="underline hover:no-underline opacity-70 hover:opacity-100"
          >
            change
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
          {error}
        </div>
      )}

      <details
        open={showPat}
        onToggle={(e) => setShowPat((e.target as HTMLDetailsElement).open)}
        className="pt-2 border-t border-[color:var(--midground-base)]/10"
      >
        <summary className="text-[11px] uppercase tracking-wider opacity-60 cursor-pointer hover:opacity-100 list-none">
          Or paste a Personal Access Token instead →
        </summary>
        <PatFallback onConnected={(next) => { setStatus(next); }} />
      </details>

      {device && (
        <DeviceFlowModal
          device={device}
          onClose={() => setDevice(null)}
          onSuccess={() => { setDevice(null); load(); }}
        />
      )}
    </div>
  );
}


function ClientIdSetup({
  status, onSaved, onCancel,
}: {
  status: GithubAuthStatus;
  onSaved: () => void;
  onCancel?: () => void;
}) {
  const [clientId, setClientId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clientId.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/api/github-auth/client-id", { client_id: clientId.trim() });
      onSaved();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={save}
      className="rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--midground-base)]/[0.03] p-4 space-y-3"
    >
      <div className="text-[10px] uppercase tracking-[0.18em] opacity-60">
        First-time setup
      </div>
      <ol className="text-xs leading-relaxed opacity-85 list-decimal pl-5 space-y-1.5 marker:opacity-50">
        <li>
          <a
            href={status.register_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 underline hover:no-underline"
          >
            Register a PRISM OAuth App on github.com
            <ExternalLink className="w-3 h-3 opacity-70" />
          </a>{" "}
          (any callback URL is fine).
        </li>
        <li>
          On the app's settings page, flip on <span className="font-mono">Enable Device Flow</span>.
        </li>
        <li>Copy the <span className="font-mono">Client ID</span> from the top of the app page and paste it below.</li>
      </ol>
      <input
        value={clientId}
        onChange={(e) => setClientId(e.target.value)}
        placeholder="Ov23li…"
        autoComplete="off"
        spellCheck={false}
        className="w-full px-3 py-2 rounded-md bg-[color:var(--background-base)]/60 border border-[color:var(--midground-base)]/20 text-sm font-mono"
      />
      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
          {error}
        </div>
      )}
      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={submitting || !clientId.trim()}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-xs uppercase tracking-wider disabled:opacity-30"
        >
          {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
          {submitting ? "Saving…" : "Save Client ID"}
        </button>
      </div>
    </form>
  );
}


function DeviceFlowModal({
  device, onClose, onSuccess,
}: {
  device: DeviceCode;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [poll, setPoll] = useState<DevicePoll>({ status: "pending" });
  const [copied, setCopied] = useState(false);
  const [interval_, setInterval_] = useState(device.interval);

  // Auto-open the GitHub device-confirmation page in a new tab so the
  // user doesn't have to copy/paste a URL too — the code still has to
  // be entered manually but the page is one click closer.
  useEffect(() => {
    try { window.open(device.verification_uri, "_blank", "noopener"); } catch { /* ignore */ }
  }, [device.verification_uri]);

  useEffect(() => {
    if (poll.status !== "pending") return;
    const t = setTimeout(async () => {
      try {
        const next = await api.post<DevicePoll>("/api/github-auth/device/poll", {
          flow_id: device.flow_id,
        });
        setPoll(next);
        if (next.status === "pending" && "interval" in next && next.interval) {
          setInterval_(next.interval);
        }
        if (next.status === "success") onSuccess();
      } catch (e) {
        setPoll({ status: "error", error: String((e as Error).message ?? e) });
      }
    }, interval_ * 1000);
    return () => clearTimeout(t);
  }, [poll, interval_, device.flow_id, onSuccess]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(device.user_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[460px] max-w-[90vw] rounded-lg border border-[color:var(--midground-base)]/20 bg-[color:var(--background-base)] p-6 space-y-4 relative shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-3 right-3 opacity-60 hover:opacity-100"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2">
          <Github className="w-5 h-5" />
          <h2 className="font-serif text-lg tracking-tight">Connect to GitHub</h2>
        </div>
        <p className="text-sm opacity-80">
          Enter this code on the GitHub page that just opened:
        </p>
        <div className="flex items-center gap-2 justify-center">
          <code className="px-4 py-3 rounded-md bg-[color:var(--midground-base)]/10 border border-[color:var(--midground-base)]/20 text-xl font-mono tracking-[0.3em] select-all">
            {device.user_code}
          </code>
          <button
            type="button"
            onClick={copy}
            className="px-3 py-3 rounded-md border border-[color:var(--midground-base)]/30 text-[10px] uppercase tracking-wider hover:bg-[color:var(--midground-base)]/10"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
        <a
          href={device.verification_uri}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs underline hover:no-underline opacity-80 hover:opacity-100"
        >
          Re-open <span className="font-mono">{device.verification_uri}</span>
          <ExternalLink className="w-3 h-3" />
        </a>
        <DeviceFlowFooter poll={poll} onClose={onClose} />
      </div>
    </div>
  );
}

function DeviceFlowFooter({ poll, onClose }: { poll: DevicePoll; onClose: () => void }) {
  if (poll.status === "pending") {
    return (
      <div className="flex items-center gap-2 text-xs opacity-70">
        <Loader2 className="w-3 h-3 animate-spin" />
        Waiting for confirmation… this panel will close automatically.
      </div>
    );
  }
  if (poll.status === "success") {
    return (
      <div className="text-xs text-emerald-200">
        Connected as <span className="font-mono">{poll.login}</span>!
      </div>
    );
  }
  if (poll.status === "expired") {
    return (
      <div className="space-y-2">
        <div className="text-xs text-amber-200">
          Code expired — start a new connect attempt.
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-[11px] uppercase tracking-wider underline hover:no-underline"
        >
          Close
        </button>
      </div>
    );
  }
  if (poll.status === "denied") {
    return (
      <div className="text-xs text-amber-200">
        You declined the authorization. Close this dialog and try again if that was a mistake.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
        {poll.error}
      </div>
    </div>
  );
}


function PatFallback({ onConnected }: { onConnected: (s: GithubAuthStatus) => void }) {
  const [token, setToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const next = await api.post<GithubAuthStatus>("/api/github-auth/configure", {
        token: token.trim(),
        user: "x-access-token",
      });
      onConnected(next);
      setToken("");
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="ghp_… or github_pat_…"
          autoComplete="off"
          className="flex-1 px-3 py-2 rounded-md bg-[color:var(--background-base)]/60 border border-[color:var(--midground-base)]/20 text-sm font-mono"
        />
        <button
          type="submit"
          disabled={submitting || !token.trim()}
          className="px-3 py-2 rounded-md border border-[color:var(--midground-base)]/30 text-[11px] uppercase tracking-wider hover:bg-[color:var(--midground-base)]/10 disabled:opacity-30"
        >
          {submitting && <Loader2 className="w-3 h-3 animate-spin inline mr-1" />}
          {submitting ? "Connecting…" : "Use token"}
        </button>
      </div>
      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
          {error}
        </div>
      )}
      <p className="text-[11px] opacity-50 leading-snug">
        Create a fine-grained PAT at{" "}
        <a
          href="https://github.com/settings/personal-access-tokens/new"
          target="_blank"
          rel="noreferrer"
          className="underline hover:no-underline"
        >
          github.com/settings/personal-access-tokens/new
        </a>{" "}
        with <span className="font-mono">Contents: read</span> on the repos PRISM should clone.
      </p>
    </form>
  );
}


function RepoPickerModal({
  onPick, onClose,
}: {
  onPick: (url: string, defaultBranch: string) => void;
  onClose: () => void;
}) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [repos, setRepos] = useState<GhRepo[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (resetPage: boolean) => {
    setLoading(true);
    setError(null);
    try {
      const nextPage = resetPage ? 1 : page;
      const r = await api.get<{ repos: GhRepo[]; has_more: boolean }>(
        `/api/github-auth/repos?q=${encodeURIComponent(q)}&page=${nextPage}`,
      );
      setRepos((prev) => resetPage ? r.repos : [...prev, ...r.repos]);
      setHasMore(r.has_more);
      if (resetPage) setPage(1);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setLoading(false);
    }
  }, [q, page]);

  useEffect(() => { load(true); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [q]);

  const loadMore = async () => {
    setPage((p) => p + 1);
    setLoading(true);
    try {
      const r = await api.get<{ repos: GhRepo[]; has_more: boolean }>(
        `/api/github-auth/repos?q=${encodeURIComponent(q)}&page=${page + 1}`,
      );
      setRepos((prev) => [...prev, ...r.repos]);
      setHasMore(r.has_more);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-[560px] max-w-[90vw] max-h-[80vh] rounded-lg border border-[color:var(--midground-base)]/20 bg-[color:var(--background-base)] p-5 flex flex-col gap-3 shadow-2xl">
        <div className="flex items-center gap-2">
          <Github className="w-5 h-5" />
          <h2 className="font-serif text-lg tracking-tight flex-1">Pick a GitHub repo</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="opacity-60 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
        <label className="flex items-center gap-2 px-3 py-2 rounded-md bg-[color:var(--midground-base)]/[0.04] border border-[color:var(--midground-base)]/15">
          <Search className="w-4 h-4 opacity-50" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="filter by name…"
            className="flex-1 bg-transparent text-sm focus:outline-none"
            autoFocus
          />
        </label>
        {error && (
          <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
            {error}
          </div>
        )}
        <ul className="flex-1 overflow-y-auto divide-y divide-[color:var(--midground-base)]/10 -mx-2">
          {repos.map((r) => (
            <li key={r.full_name}>
              <button
                type="button"
                onClick={() => onPick(
                  `https://github.com/${r.full_name}`,
                  r.default_branch || "main",
                )}
                className="w-full text-left px-2 py-2 hover:bg-[color:var(--midground-base)]/[0.04]"
              >
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-mono">{r.full_name}</span>
                  {r.private && (
                    <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[color:var(--midground-base)]/15 opacity-80">
                      private
                    </span>
                  )}
                  <span className="ml-auto text-[11px] opacity-50 font-mono">
                    {r.default_branch}
                  </span>
                </div>
                {r.description && (
                  <div className="text-[11px] opacity-60 mt-0.5 truncate">{r.description}</div>
                )}
              </button>
            </li>
          ))}
          {repos.length === 0 && !loading && (
            <li className="px-2 py-6 text-center text-sm opacity-60">
              {q ? `No repos match "${q}".` : "No repos found."}
            </li>
          )}
        </ul>
        <div className="flex items-center gap-2">
          {hasMore && (
            <button
              type="button"
              onClick={loadMore}
              disabled={loading}
              className="px-3 py-1.5 rounded-md border border-[color:var(--midground-base)]/20 text-[11px] uppercase tracking-wider hover:bg-[color:var(--midground-base)]/10 disabled:opacity-40"
            >
              {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : "Load more"}
            </button>
          )}
          <span className="text-[11px] opacity-50 ml-auto">
            {repos.length} repo{repos.length === 1 ? "" : "s"}
            {loading && <Loader2 className="w-3 h-3 animate-spin inline ml-2" />}
          </span>
        </div>
      </div>
    </div>
  );
}


type ClaudeRun = {
  run_id: string;
  ts_start: number;
  ts_end: number;
  duration_s: number;
  project: string;
  purpose: string;
  exit_code: number;
  tokens_used: number;
  input_tokens: number;
  output_tokens: number;
  final_text: string;
  stderr_excerpt: string;
  stream_path: string;
  stream_bytes: number;
};

type Job = {
  id: string;
  project: string;
  analyzer: string;
  target_sha: string;
  scope_hash: string;
  state: "pending" | "in_progress" | "completed" | "failed";
  enqueued_at: number;
  started_at: number;
  completed_at: number;
  attempts: number;
  error: string;
  result_path: string;
};

const JOB_STATES: Array<Job["state"] | "all"> = [
  "all", "pending", "in_progress", "failed", "completed",
];

function JobsPanel() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [filter, setFilter] = useState<Job["state"] | "all">("all");

  const load = useCallback(async () => {
    try {
      const q = filter === "all" ? "" : `&status=${filter}`;
      const r = await api.get<{ jobs: Job[] }>(`/api/jobs?limit=200${q}`);
      setJobs(r.jobs);
    } catch {
      setJobs([]);
    } finally {
      setLoaded(true);
    }
  }, [filter]);

  useEffect(() => { load(); }, [load]);
  // Poll while there's anything in flight or pending so the list
  // reflects what the drainer is actually doing.
  useEffect(() => {
    const anyHot = jobs.some(
      (j) => j.state === "pending" || j.state === "in_progress",
    );
    if (!anyHot) return;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [jobs, load]);

  if (!loaded) {
    return <div className="text-sm opacity-60">Loading…</div>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        {JOB_STATES.map((s) => {
          const isActive = filter === s;
          return (
            <button
              key={s}
              type="button"
              onClick={() => setFilter(s)}
              className={
                "px-2 py-1 rounded-full text-[10px] uppercase tracking-wider border " +
                (isActive
                  ? "bg-[color:var(--midground-base)]/15 border-[color:var(--midground-base)]/30"
                  : "border-[color:var(--midground-base)]/15 opacity-70 hover:opacity-100")
              }
            >
              {s}
            </button>
          );
        })}
        <span className="text-[11px] opacity-50 ml-auto">
          {jobs.length} job{jobs.length === 1 ? "" : "s"}
        </span>
      </div>

      {jobs.length === 0 ? (
        <div className="text-sm opacity-60">
          {filter === "all"
            ? "No analyzer jobs yet — configure a repo on a project to enqueue some."
            : `No jobs in state "${filter}".`}
        </div>
      ) : (
        <ul className="divide-y divide-[color:var(--midground-base)]/10 -mx-2">
          {jobs.map((j) => (
            <li key={j.id} className="px-2 py-2">
              <div className="flex items-center gap-3 flex-wrap text-xs">
                <JobStatePill state={j.state} />
                <span className="font-mono opacity-80">{j.analyzer}</span>
                <span className="opacity-60">
                  project <span className="font-mono">{j.project}</span>
                </span>
                <span className="opacity-50 font-mono">
                  {j.target_sha.slice(0, 10)}
                </span>
                {j.attempts > 1 && (
                  <span className="opacity-50">attempts {j.attempts}</span>
                )}
                <span className="opacity-50 ml-auto text-[11px]">
                  {jobTimestamp(j)}
                </span>
              </div>
              {j.state === "failed" && j.error && (
                <pre className="mt-2 ml-2 text-[11px] whitespace-pre-wrap font-mono bg-rose-500/5 border border-rose-500/20 rounded-md p-3 text-rose-200 max-h-[200px] overflow-y-auto">
                  {j.error}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function JobStatePill({ state }: { state: Job["state"] }) {
  const palette: Record<Job["state"], string> = {
    pending: "bg-indigo-500/15 text-indigo-200",
    in_progress: "bg-sky-500/15 text-sky-200",
    completed: "bg-emerald-500/15 text-emerald-200",
    failed: "bg-rose-500/15 text-rose-200",
  };
  const label = state === "in_progress" ? "running" : state;
  return (
    <span className={
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider " +
      palette[state]
    }>
      {state === "in_progress" && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
      {label}
    </span>
  );
}

function jobTimestamp(j: Job): string {
  // Pick the most recent meaningful timestamp for the row's right gutter.
  const ts =
    j.state === "completed" || j.state === "failed"
      ? j.completed_at
      : j.state === "in_progress"
        ? j.started_at
        : j.enqueued_at;
  return ts ? new Date(ts * 1000).toLocaleString() : "—";
}


type ServiceInfo = {
  version: string;
  notes: string;
  container: string;
  claude_config_dir: string;
  claude_authenticated: boolean;
  github_authenticated: boolean;
  github_credentials_path: string;
  understand_drain_interval_s: number;
  drift_interval_s: number;
  governance_interval_s: number;
  quality_interval_s: number;
  mcp_endpoint: string;
};

function ServiceInfoPanel() {
  const [info, setInfo] = useState<ServiceInfo | null>(null);

  useEffect(() => {
    api.get<ServiceInfo>("/api/service-info")
      .then(setInfo)
      .catch(() => setInfo(null));
  }, []);

  if (!info) {
    return <div className="text-sm opacity-60">Loading…</div>;
  }
  return (
    <div className="space-y-6">
      {/* Runtime info — operationally useful fields the SPA needs at a glance. */}
      <dl className="text-sm grid grid-cols-[160px_1fr] gap-y-2">
        <dt className="opacity-60">Version</dt>
        <dd className="font-serif text-base tracking-tight">
          PRISM v{info.version}
        </dd>

        <dt className="opacity-60">Container</dt>
        <dd className="font-mono text-xs">{info.container}</dd>

        <dt className="opacity-60">Claude auth</dt>
        <dd className="text-xs">
          {info.claude_authenticated
            ? <span className="text-emerald-200">logged in</span>
            : <span className="text-amber-200">not logged in — see Connections tab</span>}
          <div className="opacity-60 font-mono mt-1">
            config dir → {info.claude_config_dir}
          </div>
        </dd>

        <dt className="opacity-60">GitHub</dt>
        <dd className="text-xs">
          {info.github_authenticated
            ? <span className="text-emerald-200">connected</span>
            : <span className="text-amber-200">not connected — see Connections tab</span>}
          <div className="opacity-60 font-mono mt-1">
            credentials → {info.github_credentials_path}
          </div>
        </dd>

        <dt className="opacity-60">Drainer poll</dt>
        <dd className="text-xs">
          every <span className="font-mono">{info.understand_drain_interval_s}s</span>
          {info.understand_drain_interval_s === 0 && (
            <span className="opacity-60 ml-2">(disabled)</span>
          )}
        </dd>

        <dt className="opacity-60">Background timers</dt>
        <dd className="text-xs space-y-0.5">
          <div>drift reindex: <span className="font-mono">{info.drift_interval_s}s</span></div>
          <div>governance: <span className="font-mono">{info.governance_interval_s}s</span></div>
          <div>quality: <span className="font-mono">{info.quality_interval_s}s</span></div>
        </dd>

        <dt className="opacity-60">MCP</dt>
        <dd className="font-mono text-xs">{info.mcp_endpoint}</dd>
      </dl>

      {/* Release notes — borrows the OnboardingView markdown chrome:
          font-serif headings, opacity-85 body, monospace chips for inline
          code in backticks. Each version becomes its own block. */}
      {info.notes && (
        <div className="space-y-5 max-w-[840px]">
          <div className="text-[10px] uppercase tracking-[0.18em] opacity-50">
            Release notes
          </div>
          <ReleaseNotes notes={info.notes} latest={info.version} />
        </div>
      )}
    </div>
  );
}


type Release = { version: string; body: string };

function ReleaseNotes({ notes, latest }: { notes: string; latest: string }) {
  const releases = splitReleases(notes);
  if (releases.length === 0) {
    return <p className="text-sm leading-relaxed opacity-85">{renderInlineNotes(notes)}</p>;
  }
  return (
    <div className="space-y-5">
      {releases.map((r, idx) => (
        <ReleaseBlock
          key={r.version}
          release={r}
          isLatest={idx === 0 || r.version === latest}
        />
      ))}
    </div>
  );
}

function ReleaseBlock({ release, isLatest }: { release: Release; isLatest: boolean }) {
  const items = isLatest ? splitNumberedItems(release.body) : null;
  return (
    <section
      className={
        "space-y-2 " +
        (isLatest
          ? "pt-1"
          : "pt-3 border-t border-[color:var(--midground-base)]/10")
      }
    >
      <h2 className={
        "font-serif tracking-tight " +
        (isLatest ? "text-xl" : "text-base opacity-80")
      }>
        v{release.version}
      </h2>
      {items && items.length > 0 ? (
        <>
          {items[0] && (
            <p className="text-sm leading-relaxed opacity-85">
              {renderInlineNotes(items[0])}
            </p>
          )}
          {items.length > 1 && (
            <ol className="text-sm leading-relaxed opacity-85 list-decimal pl-5 space-y-2 marker:opacity-50">
              {items.slice(1).map((it, i) => (
                <li key={i}>{renderInlineNotes(it)}</li>
              ))}
            </ol>
          )}
        </>
      ) : (
        <p className="text-sm leading-relaxed opacity-85">
          {renderInlineNotes(release.body)}
        </p>
      )}
    </section>
  );
}


/** Split a notes string on `vX.Y.Z:` boundaries (newest first). */
function splitReleases(notes: string): Release[] {
  const pattern = /v(\d+\.\d+(?:\.\d+)?):\s+/g;
  const matches: { version: string; index: number; len: number }[] = [];
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(notes)) !== null) {
    matches.push({ version: m[1], index: m.index, len: m[0].length });
  }
  if (matches.length === 0) return [];
  const out: Release[] = [];
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].index + matches[i].len;
    const end = i + 1 < matches.length ? matches[i + 1].index : notes.length;
    out.push({
      version: matches[i].version,
      body: notes.slice(start, end).trim(),
    });
  }
  return out;
}

/** Split the body on `(N)` numbered-item markers. First element is any
 *  preamble before `(1)`; subsequent elements are the items themselves. */
function splitNumberedItems(body: string): string[] {
  const parts = body.split(/\s*\((\d+)\)\s+/);
  // `split` with a capturing group: ["preamble", "1", "item1", "2", "item2", ...]
  if (parts.length <= 1) return [body];
  const out: string[] = [parts[0].trim()];
  for (let i = 2; i < parts.length; i += 2) out.push(parts[i].trim());
  return out.filter((s) => s.length > 0);
}

/** Render inline `code` spans as monospace chips. Matches OnboardingView. */
function renderInlineNotes(text: string): ReactNode {
  const parts: ReactNode[] = [];
  const pattern = /`([^`]+)`/g;
  let lastIndex = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > lastIndex) {
      parts.push(text.slice(lastIndex, m.index));
    }
    parts.push(
      <code
        key={key++}
        className="text-[12px] font-mono px-1 py-0.5 rounded bg-[color:var(--midground-base)]/10"
      >
        {m[1]}
      </code>,
    );
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length === 0 ? text : <>{parts}</>;
}


function ClaudeRunsPanel() {
  const [runs, setRuns] = useState<ClaudeRun[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.get<{ runs: ClaudeRun[] }>("/api/claude-runs?limit=20");
      setRuns(r.runs);
    } catch {
      setRuns([]);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  // Poll every 10s so the panel surfaces newly-completed runs while
  // the user is staring at the page (e.g. right after configuring a
  // new repo). Cheap — server reads at most RUN_LOG_LIMIT lines.
  useEffect(() => {
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [load]);

  if (!loaded) {
    return <div className="text-sm opacity-60">Loading…</div>;
  }
  if (runs.length === 0) {
    return (
      <div className="text-sm opacity-60">
        No PRISM-initiated claude executions yet. Configure a repo on a
        project, or click <span className="font-mono">Sync now</span> to
        trigger one.
      </div>
    );
  }

  return (
    <ul className="divide-y divide-[color:var(--midground-base)]/10 -mx-2">
      {runs.map((r) => {
        const isExpanded = expandedId === r.run_id;
        const ok = r.exit_code === 0;
        return (
          <li key={r.run_id} className="px-2 py-2">
            <button
              type="button"
              onClick={() => setExpandedId(isExpanded ? null : r.run_id)}
              className="w-full text-left"
            >
              <div className="flex items-center gap-3 flex-wrap text-xs">
                <span
                  className={
                    "inline-flex items-center px-2 py-0.5 rounded-full uppercase tracking-wider text-[9px] " +
                    (ok
                      ? "bg-emerald-500/15 text-emerald-200"
                      : "bg-rose-500/15 text-rose-200")
                  }
                  title={ok ? "exit 0" : `exit ${r.exit_code}`}
                >
                  {ok ? "ok" : `exit ${r.exit_code}`}
                </span>
                <span className="font-mono opacity-80">{r.purpose || "—"}</span>
                {r.project && (
                  <span className="opacity-60">
                    project <span className="font-mono">{r.project}</span>
                  </span>
                )}
                <span className="opacity-60">
                  {r.duration_s.toFixed(1)}s
                </span>
                <span className="opacity-60">
                  {r.tokens_used.toLocaleString()} tok
                </span>
                <span className="opacity-50 ml-auto text-[11px]">
                  {new Date(r.ts_end * 1000).toLocaleString()}
                </span>
              </div>
            </button>
            {isExpanded && (
              <div className="mt-2 ml-2 space-y-2">
                {r.final_text ? (
                  <pre className="text-[11px] whitespace-pre-wrap font-mono bg-[color:var(--midground-base)]/[0.04] border border-[color:var(--midground-base)]/10 rounded-md p-3 max-h-[400px] overflow-y-auto">
                    {r.final_text}
                  </pre>
                ) : (
                  <div className="text-[11px] opacity-60">
                    No assistant text captured.
                  </div>
                )}
                {r.stderr_excerpt && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider opacity-60 mb-1">
                      stderr
                    </div>
                    <pre className="text-[11px] whitespace-pre-wrap font-mono bg-rose-500/5 border border-rose-500/20 rounded-md p-3 max-h-[200px] overflow-y-auto text-rose-200">
                      {r.stderr_excerpt}
                    </pre>
                  </div>
                )}
                <div className="text-[10px] opacity-60">
                  run_id <span className="font-mono">{r.run_id}</span>
                  {" · "}
                  <a
                    href={`/api/claude-runs/${r.run_id}/stream`}
                    className="underline hover:no-underline"
                  >
                    download raw stream ({Math.round(r.stream_bytes / 1024)} KB)
                  </a>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}


function NewProjectRow({ onCreated }: { onCreated: (name: string) => void | Promise<void> }) {
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.post("/api/projects", { name: trimmed });
      setName("");
      await onCreated(trimmed);
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex items-center gap-2 mb-2">
      <Plus className="w-4 h-4 opacity-60" />
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="new project name…"
        className="flex-1 px-2 py-1.5 rounded-md bg-transparent border-0 border-b border-dashed border-[color:var(--midground-base)]/20 text-sm font-mono focus:outline-none focus:border-[color:var(--midground-base)]/50"
      />
      <button
        type="submit"
        disabled={submitting || !name.trim()}
        className="px-3 py-1.5 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-[11px] uppercase tracking-wider disabled:opacity-30"
      >
        {submitting ? <Loader2 className="w-3 h-3 animate-spin" /> : "Add"}
      </button>
      {error && <span className="text-[11px] text-rose-300">{error}</span>}
    </form>
  );
}


function ProjectCard({
  name, info, isActive, onActivate, onSaved, onDeleted,
}: {
  name: string;
  info: ProjectInfo | undefined;
  isActive: boolean;
  onActivate: () => void;
  onSaved: () => void;
  onDeleted: () => Promise<void> | void;
}) {
  const [expanded, setExpanded] = useState(false);
  const busy = queueIsBusy(info?.queue);
  const drifted = isDrifted(info);

  // Auto-poll info every 5s while the queue is busy so the user sees
  // pending → in_progress → completed transitions without refreshing.
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(() => { onSaved(); }, 5000);
    return () => clearInterval(t);
  }, [busy, onSaved]);

  return (
    <li className="py-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 text-left group"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 opacity-60" />
        ) : (
          <ChevronRight className="w-4 h-4 opacity-60" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-[color:var(--midground-base)]">
              {name}
            </span>
            {isActive && (
              <span className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[color:var(--midground-base)]/15">
                active
              </span>
            )}
            <QueueBadge queue={info?.queue} />
            {drifted && !busy && (
              <span
                className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-200"
                title="The tracked ref has advanced past last_analyzed_sha — click to re-run analyzers."
              >
                drift
              </span>
            )}
          </div>
          <div className="text-[11px] opacity-60 mt-1 flex flex-wrap gap-x-4 gap-y-1">
            <span className="inline-flex items-center gap-1">
              <GitBranch className="w-3 h-3" />
              {info?.tracked_ref ?? "—"}
            </span>
            <span className="truncate max-w-[420px]">
              {info?.remote_url ?? <em className="opacity-60">no source</em>}
            </span>
            <span>
              sha: <span className="font-mono">
                {info?.current_sha ? info.current_sha.slice(0, 10) : "—"}
              </span>
            </span>
            <span>
              analyzed: <span className="font-mono">
                {info?.last_analyzed_sha ? info.last_analyzed_sha.slice(0, 10) : "—"}
              </span>
            </span>
          </div>
        </div>
      </button>
      {expanded && (
        <ProjectEditor
          name={name}
          info={info}
          onActivate={onActivate}
          onSaved={onSaved}
          onDeleted={onDeleted}
        />
      )}
    </li>
  );
}


function QueueBadge({ queue }: { queue: QueueCounts | undefined }) {
  if (!queue) return null;
  if (queue.in_progress > 0) {
    return (
      <span className="inline-flex items-center gap-1 text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/15 text-sky-200">
        <Loader2 className="w-2.5 h-2.5 animate-spin" />
        analyzing {queue.in_progress}
      </span>
    );
  }
  if (queue.pending > 0) {
    return (
      <span className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-200">
        {queue.pending} queued
      </span>
    );
  }
  if (queue.failed > 0) {
    return (
      <span className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-200">
        {queue.failed} failed
      </span>
    );
  }
  return null;
}


function ProjectEditor({
  name, info, onActivate, onSaved, onDeleted,
}: {
  name: string;
  info: ProjectInfo | undefined;
  onActivate: () => void;
  onSaved: () => void;
  onDeleted: () => Promise<void> | void;
}) {
  const [remote, setRemote] = useState(info?.remote_url ?? "");
  const [ref, setRef] = useState(info?.tracked_ref ?? "origin/main");
  const [submitting, setSubmitting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ghAuthed, setGhAuthed] = useState(false);
  const [picking, setPicking] = useState(false);
  const isProtected = name === "default";

  useEffect(() => {
    setRemote(info?.remote_url ?? "");
    setRef(info?.tracked_ref ?? "origin/main");
  }, [info?.remote_url, info?.tracked_ref]);

  // Lazy-load github auth status so the Browse button only renders when
  // a repo list call would actually succeed. Cheap — single GET.
  useEffect(() => {
    api.get<GithubAuthStatus>("/api/github-auth/status")
      .then((s) => setGhAuthed(s.authenticated))
      .catch(() => setGhAuthed(false));
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!remote.trim()) {
      setError("git url is required (leave a project sourceless by closing this editor without saving)");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await api.post(`/api/understand/configure?project=${encodeURIComponent(name)}`, {
        remote_url: remote.trim(),
        tracked_ref: ref.trim() || "origin/main",
      });
      onSaved();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  const sync = async () => {
    setSyncing(true);
    setError(null);
    try {
      await api.post(`/api/understand/refresh?project=${encodeURIComponent(name)}`, {});
      onSaved();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSyncing(false);
    }
  };

  const remove = async () => {
    if (confirmText !== name) {
      setError(`Type "${name}" to confirm deletion.`);
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await api.delete(`/api/projects/${encodeURIComponent(name)}`);
      await onDeleted();
    } catch (e) {
      setError(String((e as Error).message ?? e));
      setDeleting(false);
    }
  };

  const drifted = isDrifted(info);
  const hasSource = Boolean(info?.remote_url);

  return (
    <form
      onSubmit={save}
      className="mt-3 ml-7 rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--midground-base)]/[0.03] p-4 space-y-3"
    >
      <div className="grid grid-cols-[1fr_180px] gap-3">
        <label className="flex flex-col gap-1 min-w-0">
          <span className="text-[10px] uppercase tracking-wider opacity-60 flex items-center gap-2">
            Git URL <span className="opacity-50 normal-case">(optional)</span>
            {ghAuthed && (
              <button
                type="button"
                onClick={() => setPicking(true)}
                className="ml-auto inline-flex items-center gap-1 text-[10px] uppercase tracking-wider opacity-80 hover:opacity-100"
              >
                <Github className="w-3 h-3" /> Browse my repos
              </button>
            )}
          </span>
          <input
            value={remote}
            onChange={(e) => setRemote(e.target.value)}
            placeholder="https://github.com/owner/repo"
            className="px-3 py-2 rounded-md bg-[color:var(--background-base)]/60 border border-[color:var(--midground-base)]/20 text-sm font-mono"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-wider opacity-60">
            Tracked ref
          </span>
          <input
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            className="px-3 py-2 rounded-md bg-[color:var(--background-base)]/60 border border-[color:var(--midground-base)]/20 text-sm font-mono"
          />
        </label>
      </div>
      {info?.remote_url && info.remote_url !== remote.trim() && (
        <div className="text-[11px] opacity-60">
          Changing the URL is refused server-side once a clone exists — to
          re-point, delete the project's source/ dir first.
        </div>
      )}
      {error && (
        <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-3 py-2 text-xs">
          {error}
        </div>
      )}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <button
          type="button"
          onClick={onActivate}
          className="text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
        >
          Make active
        </button>
        <div className="flex items-center gap-2">
          {hasSource && (
            <button
              type="button"
              onClick={sync}
              disabled={syncing || submitting || deleting}
              title={drifted
                ? "Re-run analyzers against the latest commit"
                : "Re-run analyzers (no drift detected)"}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-[color:var(--midground-base)]/30 text-xs uppercase tracking-wider disabled:opacity-40 hover:bg-[color:var(--midground-base)]/10"
            >
              {syncing && <Loader2 className="w-3 h-3 animate-spin" />}
              {syncing ? "Syncing…" : "Sync now"}
            </button>
          )}
          <button
            type="submit"
            disabled={submitting || deleting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-xs uppercase tracking-wider disabled:opacity-40"
          >
            {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
            {submitting ? "Saving…" : info?.remote_url ? "Update source" : "Set source"}
          </button>
        </div>
      </div>

      {!isProtected && (
        <div className="pt-3 border-t border-[color:var(--midground-base)]/10">
          {!confirming ? (
            <button
              type="button"
              onClick={() => { setConfirming(true); setError(null); }}
              className="text-[11px] uppercase tracking-wider text-rose-300/80 hover:text-rose-200"
            >
              Delete project + all data
            </button>
          ) : (
            <div className="space-y-2">
              <div className="text-[11px] text-rose-200">
                This wipes <span className="font-mono">data/projects/{name}</span>:
                brain, graph, tasks, scores, source clone, queue, all artifacts.
                Type <span className="font-mono">{name}</span> to confirm.
              </div>
              <div className="flex items-center gap-2">
                <input
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder={name}
                  disabled={deleting}
                  className="flex-1 px-3 py-2 rounded-md bg-[color:var(--background-base)]/60 border border-rose-500/30 text-sm font-mono"
                />
                <button
                  type="button"
                  onClick={remove}
                  disabled={deleting || confirmText !== name}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-rose-500/80 text-white text-xs uppercase tracking-wider disabled:opacity-30"
                >
                  {deleting && <Loader2 className="w-3 h-3 animate-spin" />}
                  {deleting ? "Deleting…" : "Delete forever"}
                </button>
                <button
                  type="button"
                  onClick={() => { setConfirming(false); setConfirmText(""); }}
                  disabled={deleting}
                  className="text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {picking && (
        <RepoPickerModal
          onClose={() => setPicking(false)}
          onPick={(url, defaultBranch) => {
            setRemote(url);
            // Only auto-fill the tracked ref when the user hasn't
            // customized it from the default — otherwise we'd clobber
            // their choice on every pick.
            if (!ref || ref === "origin/main") {
              setRef(`origin/${defaultBranch}`);
            }
            setPicking(false);
          }}
        />
      )}
    </form>
  );
}
