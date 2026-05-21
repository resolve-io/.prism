import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Brain, Network, BookOpen, ListChecks,
  Workflow, MessageSquare, Search, Sparkles, Layers, Eye, Settings,
  type LucideIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import { useProject } from "@/lib/project";
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

const SECTIONS: Section[] = [
  {
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard },
    ],
  },
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
  const version = useVersion();

  return (
    <aside className="w-[240px] shrink-0 flex flex-col border-r border-[color:var(--border-default)] bg-[color:var(--surface-1)]">
      <div className="h-[80px] px-5 flex flex-col justify-center border-b border-[color:var(--border-default)]">
        <div className="font-serif text-2xl leading-none tracking-tight text-[color:var(--text-primary)]">PRISM</div>
        <div className="font-serif text-xl leading-none tracking-tight text-[color:var(--text-secondary)] mt-1">SERVICE</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {SECTIONS.map((section, i) => (
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
              return (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  title={isStale ? `${label} is stale for project '${project}' — re-index needed` : undefined}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-5 py-2 text-[13px] uppercase tracking-wider transition-colors",
                      "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-2)]",
                      isActive && "text-[color:var(--text-primary)] bg-[color:var(--surface-2)] border-l-2 border-[color:var(--text-primary)]",
                    )
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span className="flex-1">{label}</span>
                  {isStale && (
                    <span
                      className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_6px_2px_rgba(251,191,36,0.5)]"
                      aria-label="stale"
                    />
                  )}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="border-t border-[color:var(--border-default)]">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-5 py-3 text-[13px] uppercase tracking-wider transition-colors",
              "text-[color:var(--text-secondary)] hover:text-[color:var(--text-primary)] hover:bg-[color:var(--surface-2)]",
              isActive && "text-[color:var(--text-primary)] bg-[color:var(--surface-2)] border-l-2 border-[color:var(--text-primary)]",
            )
          }
        >
          <Settings className="w-4 h-4" />
          <span>Settings</span>
        </NavLink>
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
