import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, GitBranch, Loader2, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { useVersion } from "@/lib/version";
import { Card, Empty, ErrorBanner, Page, SectionLabel } from "@/components/ui";

type ProjectInfo = {
  name: string;
  remote_url: string | null;
  tracked_ref: string | null;
  current_sha: string | null;
  last_analyzed_sha: string | null;
};

async function fetchInfo(name: string): Promise<ProjectInfo> {
  const s = await api.get<{
    tracked_ref: string;
    remote_url: string | null;
    current_sha: string | null;
    last_analyzed_sha: string | null;
  }>(`/api/understand?project=${encodeURIComponent(name)}`);
  return {
    name,
    remote_url: s.remote_url ?? null,
    tracked_ref: s.tracked_ref ?? null,
    current_sha: s.current_sha ?? null,
    last_analyzed_sha: s.last_analyzed_sha ?? null,
  };
}


export default function SettingsPage() {
  const [active, setActive] = useProject();
  const [projects, setProjects] = useState<string[]>([]);
  const [infos, setInfos] = useState<Record<string, ProjectInfo>>({});
  const [error, setError] = useState<string | null>(null);
  const version = useVersion();

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


  return (
    <Page>
      <div>
        <h1 className="font-serif text-3xl tracking-tight">Settings</h1>
        <p className="text-sm opacity-60 mt-1">
          Manage projects and service configuration. Click a project to
          edit its source — projects without a git source are valid.
        </p>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      <Card>
        <SectionLabel>Projects</SectionLabel>
        <NewProjectRow onCreated={async (name) => {
          await loadProjects();
          await reloadOne(name);
          setActive(name);
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
              />
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <SectionLabel>Service</SectionLabel>
        <dl className="text-sm grid grid-cols-[140px_1fr] gap-y-2">
          <dt className="opacity-60">Theme</dt>
          <dd>Slate Blue</dd>
          <dt className="opacity-60">Version</dt>
          <dd>
            PRISM v{version?.version ?? "…"}
            {version?.notes && (
              <div className="text-xs opacity-60 mt-1 leading-snug">
                {version.notes}
              </div>
            )}
          </dd>
          <dt className="opacity-60">MCP</dt>
          <dd className="font-mono text-xs">localhost:7777/mcp/?project=…</dd>
        </dl>
      </Card>
    </Page>
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
  name, info, isActive, onActivate, onSaved,
}: {
  name: string;
  info: ProjectInfo | undefined;
  isActive: boolean;
  onActivate: () => void;
  onSaved: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

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
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[color:var(--midground-base)]">
              {name}
            </span>
            {isActive && (
              <span className="text-[9px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-[color:var(--midground-base)]/15">
                active
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
          </div>
        </div>
      </button>
      {expanded && (
        <ProjectEditor
          name={name}
          info={info}
          onActivate={onActivate}
          onSaved={onSaved}
        />
      )}
    </li>
  );
}


function ProjectEditor({
  name, info, onActivate, onSaved,
}: {
  name: string;
  info: ProjectInfo | undefined;
  onActivate: () => void;
  onSaved: () => void;
}) {
  const [remote, setRemote] = useState(info?.remote_url ?? "");
  const [ref, setRef] = useState(info?.tracked_ref ?? "origin/main");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRemote(info?.remote_url ?? "");
    setRef(info?.tracked_ref ?? "origin/main");
  }, [info?.remote_url, info?.tracked_ref]);

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

  return (
    <form
      onSubmit={save}
      className="mt-3 ml-7 rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--midground-base)]/[0.03] p-4 space-y-3"
    >
      <div className="grid grid-cols-[1fr_180px] gap-3">
        <label className="flex flex-col gap-1 min-w-0">
          <span className="text-[10px] uppercase tracking-wider opacity-60">
            Git URL <span className="opacity-50 normal-case">(optional)</span>
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
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onActivate}
          className="text-[11px] uppercase tracking-wider opacity-70 hover:opacity-100"
        >
          Make active
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-xs uppercase tracking-wider disabled:opacity-40"
        >
          {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
          {submitting ? "Saving…" : info?.remote_url ? "Update source" : "Set source"}
        </button>
      </div>
    </form>
  );
}
