import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  AppWindow, BookOpen, Brain, Eye, FolderTree, Info, KeyRound,
  Layers, LayoutDashboard, ListChecks, MessageSquare, Network,
  ScrollText, Search, Settings, Sparkles, Workflow,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
import { useScanActivity } from "@/lib/scan-activity";
import { useVersion } from "@/lib/version";
import { cn } from "@/lib/utils";

type StaleKey = "understand" | "graph" | "brain";

type Item = {
  to: string;
  label: string;
  icon: LucideIcon;
  staleKey?: StaleKey;
};

type Section = { label?: string; items: Item[] };

// Always-visible top item. From inside Settings mode, clicking Dashboard
// is also the way back out, so it never disappears.
const TOP_SECTION: Section = {
  items: [
    { to: "/", label: "Dashboard", icon: LayoutDashboard },
  ],
};

// Default body: Knowledge + Activity, shown on every route that isn't
// /settings/*.
const MAIN_SECTIONS: Section[] = [
  {
    label: "Knowledge",
    items: [
      { to: "/brain", label: "Brain", icon: Brain, staleKey: "brain" },
      { to: "/graph", label: "Graph", icon: Network, staleKey: "graph" },
      { to: "/understand", label: "Understand", icon: Eye, staleKey: "understand" },
    ],
  },
  {
    label: "Activity",
    items: [
      { to: "/memory", label: "Memory", icon: BookOpen },
      { to: "/tasks", label: "Tasks", icon: ListChecks },
      { to: "/conductor", label: "Conductor", icon: Workflow },
      { to: "/sessions", label: "Sessions", icon: MessageSquare },
      { to: "/retrievals", label: "Retrievals", icon: Search },
      { to: "/learning", label: "Learning", icon: Sparkles },
      { to: "/consolidation", label: "Consolidation", icon: Layers },
    ],
  },
];

// Settings-mode body: when pathname starts with /settings, Knowledge +
// Activity collapse and Settings categories take their place. Each
// item routes to /settings/<id>; SettingsPage reads the URL param.
const SETTINGS_SECTIONS: Section[] = [
  {
    label: "Settings",
    items: [
      { to: "/settings/projects", label: "Projects", icon: FolderTree },
      { to: "/settings/auth", label: "Claude auth", icon: KeyRound },
      { to: "/settings/jobs", label: "Jobs", icon: ListChecks },
      { to: "/settings/logs", label: "Logs", icon: ScrollText },
      { to: "/settings/service", label: "Service", icon: Info },
    ],
  },
];


type Staleness = { understand: boolean; graph: boolean; brain: boolean };

function useStaleness(project: string): Staleness {
  const [stale, setStale] = useState<Staleness>({
    understand: false, graph: false, brain: false,
  });
  useEffect(() => {
    let cancel = false;
    const load = () => {
      api
        .get<Staleness>(`/api/staleness?project=${encodeURIComponent(project)}`)
        .then((s) => { if (!cancel) setStale(s); })
        .catch(() => { /* leave last good state */ });
    };
    load();
    const t = setInterval(load, 5000);
    return () => { cancel = true; clearInterval(t); };
  }, [project]);
  return stale;
}


export default function Sidebar() {
  const [project] = useProject();
  const stale = useStaleness(project);
  const scan = useScanActivity();
  const version = useVersion();
  const { pathname } = useLocation();
  const inSettings = pathname.startsWith("/settings");

  // Top item is always Dashboard. Below it: either Knowledge + Activity
  // (default) or the Settings categories (when in /settings/*). The
  // bottom Settings link stays in both modes — it's how you toggle in.
  const sections: Section[] = [
    TOP_SECTION,
    ...(inSettings ? SETTINGS_SECTIONS : MAIN_SECTIONS),
  ];

  return (
    <aside className="w-[240px] shrink-0 flex flex-col border-r border-[color:var(--border-default)] bg-[color:var(--surface-1)]">
      <div className="h-[80px] px-5 flex flex-col justify-center border-b border-[color:var(--border-default)]">
        <div className="font-serif text-2xl leading-none tracking-tight text-[color:var(--text-primary)]">PRISM</div>
        <div className="font-serif text-xl leading-none tracking-tight text-[color:var(--text-secondary)] mt-1">SERVICE</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {sections.map((section, i) => (
          // Match the divider style used between Settings and the version
          // footer below — same border-default line + same py-3 spacing —
          // so all sidebar group breaks read as one consistent pattern.
          <div
            key={i}
            className={cn(
              i > 0 && "mt-3 pt-3 border-t border-[color:var(--border-default)]",
            )}
          >
            {section.label && (
              <div className="px-5 mb-1 text-[10px] uppercase tracking-[0.18em] text-[color:var(--text-label)]">
                {section.label}
              </div>
            )}
            {section.items.map(({ to, label, icon: Icon, staleKey }) => {
              const isStale = staleKey ? stale[staleKey] : false;
              // While the drainer has work in flight, the surfaces it
              // populates (Brain, Graph, Understand — every item with a
              // staleKey) glow slate-blue. Blue takes precedence over the
              // amber stale dot because "actively scanning" implies
              // "stale is being addressed right now."
              const isScanning = staleKey ? scan.isActive : false;
              return (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={
                    isScanning
                      ? `${label} is being updated — drainer is running analyzers`
                      : isStale
                        ? `${label} is stale for project '${project}' — re-index needed`
                        : undefined
                  }
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-5 py-2 text-[13px] uppercase tracking-wider transition-colors relative",
                      "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-2)]",
                      isActive && "text-[color:var(--text-primary)] bg-[color:var(--surface-2)] border-l-2 border-[color:var(--text-primary)]",
                      // Soft slate-blue glow + animated pulse on the
                      // row itself while scanning. Subtle enough to
                      // not fight the active-route indicator, loud
                      // enough that the user knows something is alive.
                      isScanning && "text-sky-200 bg-sky-500/[0.06] animate-pulse",
                    )
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span className="flex-1">{label}</span>
                  {isScanning ? (
                    <span
                      className="w-2 h-2 rounded-full bg-sky-300 shadow-[0_0_8px_3px_rgba(125,211,252,0.6)]"
                      aria-label="scanning"
                    />
                  ) : isStale ? (
                    <span
                      className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_2px_rgba(251,191,36,0.5)]"
                      aria-label="stale"
                    />
                  ) : null}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t border-[color:var(--border-default)]">
        {/* Footer toggle. In default mode it's "Settings" and enters
            the Settings sidebar mode. In Settings mode it flips to
            "Application" with a different icon so the user has a
            clear, single-click way back to the main app. We DON'T
            use NavLink active styling here because the active route
            is already reflected by the items in the Settings nav
            above — keeping this neutral makes it read as a mode
            toggle, not yet-another-link. */}
        {inSettings ? (
          <NavLink
            to="/"
            className={cn(
              "flex items-center gap-3 px-5 py-3 text-[13px] uppercase tracking-wider transition-colors",
              "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-2)]",
            )}
            title="Return to the main application"
          >
            <AppWindow className="w-4 h-4" />
            <span>Application</span>
          </NavLink>
        ) : (
          <NavLink
            to="/settings"
            className={cn(
              "flex items-center gap-3 px-5 py-3 text-[13px] uppercase tracking-wider transition-colors",
              "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-2)]",
            )}
            title="Open application settings"
          >
            <Settings className="w-4 h-4" />
            <span>Settings</span>
          </NavLink>
        )}
        <div
          className="px-5 py-3 text-[10px] uppercase tracking-wider text-[color:var(--text-label)] border-t border-[color:var(--border-default)]"
          title={version?.notes ?? ""}
        >
          Slate Blue · v{version?.version ?? "…"}
        </div>
      </div>
    </aside>
  );
}
