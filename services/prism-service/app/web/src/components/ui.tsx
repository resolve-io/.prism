/**
 * Shared PRISM v5 primitives — Slate-Blue Hermes cards, KPIs, labels,
 * pills, tables.
 *
 * Author against the semantic tokens defined in index.css (--surface-*,
 * --text-*, --border-*) rather than --midground-base/N opacity sleeves.
 * The token tiers are what give the design its hierarchy: cards stand
 * out from page (surface-0 → surface-1), nested cards stand out from
 * their parent (surface-1 → surface-2), and every text tier is WCAG
 * AA on both surfaces.
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const Card = ({
  children, className, nested, raised,
}: {
  children: ReactNode;
  className?: string;
  /** Use when the card sits INSIDE another Card — lifts to surface-2. */
  nested?: boolean;
  /** Use for the dominant card on a page — lifts to surface-2 + strong border. */
  raised?: boolean;
}) => {
  const surfaceClass = nested || raised
    ? "bg-[color:var(--surface-2)]"
    : "bg-[color:var(--surface-1)]";
  const borderClass = raised
    ? "border-[color:var(--border-strong)]"
    : "border-[color:var(--border-default)]";
  return (
    <div className={cn("rounded-md border p-5", surfaceClass, borderClass, className)}>
      {children}
    </div>
  );
};

export const SectionLabel = ({ children }: { children: ReactNode }) => (
  <div className="text-[10px] uppercase tracking-wider text-[color:var(--text-label)] mb-3">
    {children}
  </div>
);

export const Kpi = ({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) => (
  <div className="flex-1 min-w-[150px] rounded-md border border-[color:var(--border-default)] bg-[color:var(--surface-1)] p-4">
    <div className="text-[10px] uppercase tracking-wider text-[color:var(--text-label)] mb-2">{label}</div>
    <div className="text-2xl font-semibold leading-none text-[color:var(--text-primary)]">{value}</div>
    {hint && <div className="text-[10px] uppercase tracking-wider text-[color:var(--text-muted)] mt-2">{hint}</div>}
  </div>
);

export const Pill = ({ children, active, onClick }: { children: ReactNode; active?: boolean; onClick?: () => void }) => (
  <button
    onClick={onClick}
    className={cn(
      "px-3 py-1 rounded-full text-[11px] uppercase tracking-wider transition-colors",
      active
        ? "bg-[color:var(--text-primary)] text-[color:var(--surface-0)]"
        : "bg-[color:var(--surface-2)] text-[color:var(--text-secondary)] hover:bg-[color:var(--surface-3)] hover:text-[color:var(--text-primary)]",
    )}
  >{children}</button>
);

export const Empty = ({ children }: { children: ReactNode }) => (
  <div className="rounded-md border border-dashed border-[color:var(--border-default)] px-5 py-8 text-center text-sm text-[color:var(--text-muted)]">
    {children}
  </div>
);

export const Page = ({ children }: { children: ReactNode }) => (
  // Full-width: page fills the available content column; minimum is
  // whatever the children require. (Was capped at 1400px previously,
  // which left big empty gutters on wider monitors.)
  <div className="p-8 space-y-6 w-full min-w-[720px]">{children}</div>
);

export const ErrorBanner = ({ children }: { children: ReactNode }) => (
  <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-4 py-3 text-sm">
    {children}
  </div>
);
