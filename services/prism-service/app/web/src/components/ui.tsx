/**
 * Shared PRISM v5 primitives — Hermes-themed cards, KPIs, labels, pills, tables.
 * Lightweight wrappers; pages compose these for consistency.
 */
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export const Card = ({ children, className, ...rest }: { children: ReactNode; className?: string }) => (
  <div className={cn("rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 p-5", className)} {...rest}>
    {children}
  </div>
);

export const SectionLabel = ({ children }: { children: ReactNode }) => (
  <div className="text-[10px] uppercase tracking-wider opacity-60 mb-3">{children}</div>
);

export const Kpi = ({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) => (
  <div className="flex-1 min-w-[150px] rounded-md border border-[color:var(--midground-base)]/15 bg-[color:var(--background-base)]/40 p-4">
    <div className="text-[10px] uppercase tracking-wider opacity-60 mb-2">{label}</div>
    <div className="text-2xl font-semibold leading-none">{value}</div>
    {hint && <div className="text-[10px] uppercase tracking-wider opacity-50 mt-2">{hint}</div>}
  </div>
);

export const Pill = ({ children, active, onClick }: { children: ReactNode; active?: boolean; onClick?: () => void }) => (
  <button
    onClick={onClick}
    className={cn(
      "px-3 py-1 rounded-full text-[11px] uppercase tracking-wider transition-colors",
      active
        ? "bg-[color:var(--midground-base)] text-[color:var(--background-base)]"
        : "bg-[color:var(--midground-base)]/10 text-[color:var(--midground-base)]/70 hover:bg-[color:var(--midground-base)]/20",
    )}
  >{children}</button>
);

export const Empty = ({ children }: { children: ReactNode }) => (
  <div className="rounded-md border border-dashed border-[color:var(--midground-base)]/15 px-5 py-8 text-center text-sm opacity-60">
    {children}
  </div>
);

export const Page = ({ children }: { children: ReactNode }) => (
  <div className="p-8 space-y-6 max-w-[1400px]">{children}</div>
);

export const ErrorBanner = ({ children }: { children: ReactNode }) => (
  <div className="rounded-md border border-rose-500/30 bg-rose-500/10 text-rose-200 px-4 py-3 text-sm">
    {children}
  </div>
);
