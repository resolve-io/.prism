import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Brain, Network, BookOpen, ListChecks,
  Workflow, MessageSquare, Search, Sparkles, Layers,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

type Item = { to: string; label: string; icon: LucideIcon };

const NAV: Item[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/brain", label: "Brain", icon: Brain },
  { to: "/graph", label: "Graph", icon: Network },
  { to: "/memory", label: "Memory", icon: BookOpen },
  { to: "/tasks", label: "Tasks", icon: ListChecks },
  { to: "/conductor", label: "Conductor", icon: Workflow },
  { to: "/sessions", label: "Sessions", icon: MessageSquare },
  { to: "/retrievals", label: "Retrievals", icon: Search },
  { to: "/learning", label: "Learning", icon: Sparkles },
  { to: "/consolidation", label: "Consolidation", icon: Layers },
];

export default function Sidebar() {
  return (
    <aside className="w-[240px] shrink-0 flex flex-col border-r border-[color:var(--midground-base)]/10 bg-[color:var(--background-base)]/60 backdrop-blur-sm">
      <div className="h-[80px] px-5 flex flex-col justify-center border-b border-[color:var(--midground-base)]/10">
        <div className="font-serif text-2xl leading-none tracking-tight text-[color:var(--midground-base)]">PRISM</div>
        <div className="font-serif text-xl leading-none tracking-tight opacity-70 text-[color:var(--midground-base)] mt-1">SERVICE</div>
      </div>
      <nav className="flex-1 overflow-y-auto py-3">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-5 py-2 text-[13px] uppercase tracking-wider transition-colors",
                "text-[color:var(--midground-base)]/70 hover:text-[color:var(--midground-base)] hover:bg-[color:var(--midground-base)]/5",
                isActive && "text-[color:var(--midground-base)] bg-[color:var(--midground-base)]/10 border-l-2 border-[color:var(--midground-base)]",
              )
            }
          >
            <Icon className="w-4 h-4 opacity-80" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-[color:var(--midground-base)]/10 text-[10px] uppercase tracking-wider text-[color:var(--midground-base)]/50">
        <div>Hermes Teal</div>
        <div className="mt-1 opacity-70">PRISM v5.0.0</div>
      </div>
    </aside>
  );
}
