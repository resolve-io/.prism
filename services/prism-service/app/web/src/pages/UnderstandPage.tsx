import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { Card, Empty, ErrorBanner, Kpi, Page, Pill, SectionLabel } from "@/components/ui";
import TourView from "@/components/understand/TourView";
import LayersView from "@/components/understand/LayersView";
import DomainsView from "@/components/understand/DomainsView";
import OnboardingView from "@/components/understand/OnboardingView";

type Status = {
  project: string;
  tracked_ref: string;
  current_sha: string | null;
  last_analyzed_sha: string | null;
  in_session_drain_enabled: boolean;
  cached_shas: string[];
  queue: {
    pending: number; in_progress: number;
    completed: number; failed: number;
  };
};

type ArtifactKind = "tour" | "layers" | "domains" | "onboarding";

type ArtifactResponse = {
  data: unknown;
  sha: string | null;
  miss_reason?: string;
};


export default function UnderstandPage() {
  const [project] = useProject();
  const [status, setStatus] = useState<Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [tab, setTab] = useState<ArtifactKind>("tour");
  const [artifact, setArtifact] = useState<ArtifactResponse | null>(null);

  const loadStatus = useCallback(() => {
    api
      .get<Status>(`/api/understand?project=${encodeURIComponent(project)}`)
      .then((s) => {
        setStatus(s);
        setError(null);
      })
      .catch((e) => setError(String(e.message ?? e)));
  }, [project]);

  const loadArtifact = useCallback(() => {
    api
      .get<ArtifactResponse>(
        `/api/understand/${tab}?project=${encodeURIComponent(project)}`,
      )
      .then(setArtifact)
      .catch(() => setArtifact(null));
  }, [project, tab]);

  useEffect(() => {
    loadStatus();
    const t = setInterval(loadStatus, 3000);
    return () => clearInterval(t);
  }, [loadStatus]);

  useEffect(() => { loadArtifact(); }, [loadArtifact]);


  const [notice, setNotice] = useState<string | null>(null);

  // Auto-dismiss the notice after 6 s so it doesn't haunt the screen.
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 6000);
    return () => clearTimeout(t);
  }, [notice]);

  const triggerRefresh = async () => {
    setSubmitting(true);
    setNotice(null);
    try {
      const res = await api.post<{
        status: string;
        queued: string[];
        cached_hits: string[];
        target_sha: string;
        budget_used?: number;
        budget_limit?: number;
      }>(`/api/understand/refresh?project=${encodeURIComponent(project)}`, {});
      setError(null);
      if (res.status === "no_source") {
        setNotice("This project has no git source configured. Open Settings to add one.");
      } else if (res.status === "complete") {
        setNotice(
          `All ${res.cached_hits.length} analyzers up to date at ${res.target_sha.slice(0, 10)} — nothing to do.`,
        );
      } else if (res.status === "queued") {
        setNotice(
          `Queued ${res.queued.length} analyzer${res.queued.length === 1 ? "" : "s"}: ${res.queued.join(", ")}. ` +
          `Run \`python -m app.cli.understand_cli drain --project ${project} --budget-usd 2.0\` on the host to execute.`,
        );
      } else if (res.status === "budget_exceeded") {
        setNotice(`Refused: estimated ${res.budget_used} tokens exceeds ${res.budget_limit} budget cap.`);
      } else {
        setNotice(`Refresh: ${res.status}`);
      }
      loadStatus();
    } catch (e) {
      setError(String((e as Error).message ?? e));
    } finally {
      setSubmitting(false);
    }
  };

  const shortSha = (sha: string | null | undefined): string =>
    sha ? sha.slice(0, 10) : "—";


  return (
    <Page>
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl tracking-tight">Understand</h1>
          <p className="text-sm opacity-60 mt-1">
            Point a project at a git remote and generate tour, architecture,
            domain glossary, and onboarding doc from its pinned source.
          </p>
        </div>
        <button
          onClick={triggerRefresh}
          disabled={submitting || !status?.current_sha}
          className="px-4 py-2 rounded-md bg-[color:var(--midground-base)] text-[color:var(--background-base)] text-xs uppercase tracking-wider disabled:opacity-40"
        >
          {submitting ? "Working…" : "Refresh"}
        </button>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}

      {notice && (
        <div className="fixed bottom-6 right-6 z-40 max-w-[420px] rounded-md border border-[color:var(--midground-base)]/20 bg-[color:var(--background-base)]/95 backdrop-blur-sm shadow-lg px-4 py-3 text-[12px] flex items-start gap-3">
          <span className="flex-1 opacity-90 leading-relaxed">{notice}</span>
          <button
            onClick={() => setNotice(null)}
            className="text-[10px] uppercase tracking-wider opacity-60 hover:opacity-100 shrink-0"
          >
            dismiss
          </button>
        </div>
      )}

      <div className="flex gap-3 flex-wrap">
        <Kpi label="Tracked ref" value={status?.tracked_ref ?? "—"} />
        <Kpi label="Current SHA" value={shortSha(status?.current_sha)} />
        <Kpi label="Last analyzed" value={shortSha(status?.last_analyzed_sha)} />
        <Kpi
          label="Queue"
          value={status?.queue?.pending ?? 0}
          hint={`${status?.queue?.in_progress ?? 0} running · ${status?.queue?.completed ?? 0} done · ${status?.queue?.failed ?? 0} failed`}
        />
        <Kpi label="Cached SHAs" value={status?.cached_shas?.length ?? 0} />
      </div>

      {!status?.current_sha && (
        <Card>
          <SectionLabel>No source configured</SectionLabel>
          <p className="text-sm opacity-70">
            Use <span className="font-semibold">Add project</span> in the
            top bar to create a project pointed at a git remote.
          </p>
        </Card>
      )}

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <SectionLabel>Artifact</SectionLabel>
          <div className="flex gap-2 ml-2">
            {(["tour", "layers", "domains", "onboarding"] as ArtifactKind[]).map((k) => (
              <Pill key={k} active={tab === k} onClick={() => setTab(k)}>
                {k}
              </Pill>
            ))}
          </div>
        </div>
        <ArtifactView tab={tab} artifact={artifact} />
      </Card>
    </Page>
  );
}


function ArtifactView({
  tab, artifact,
}: { tab: ArtifactKind; artifact: ArtifactResponse | null }) {
  if (!artifact) {
    return <Empty>Loading…</Empty>;
  }
  if (artifact.data == null) {
    return (
      <Empty>
        No {tab} artifact yet.{" "}
        {artifact.miss_reason ?? "Run a refresh and drain the queue to populate."}
      </Empty>
    );
  }
  // Unparseable payload (claude emitted non-JSON for a JSON analyzer)
  if (typeof artifact.data === "object" && artifact.data !== null
      && "error" in (artifact.data as Record<string, unknown>)
      && "raw" in (artifact.data as Record<string, unknown>)) {
    const raw = (artifact.data as { raw: string }).raw;
    return (
      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wider text-rose-300/80">
          Analyzer output didn't parse as JSON — showing raw text
        </div>
        <pre className="text-[12px] font-mono whitespace-pre-wrap leading-relaxed opacity-80 max-h-[60vh] overflow-auto">
          {raw}
        </pre>
      </div>
    );
  }
  if (tab === "onboarding" && typeof artifact.data === "string") {
    return <OnboardingView text={artifact.data} />;
  }
  if (tab === "tour") {
    return <TourView data={artifact.data as Parameters<typeof TourView>[0]["data"]} />;
  }
  if (tab === "layers") {
    return <LayersView data={artifact.data as Parameters<typeof LayersView>[0]["data"]} />;
  }
  if (tab === "domains") {
    return <DomainsView data={artifact.data as Parameters<typeof DomainsView>[0]["data"]} />;
  }
  return null;
}
