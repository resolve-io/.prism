import { CheckCircle2, Lock, Circle, CircleDot } from "lucide-react";
import { cn } from "@/lib/utils";

export type Step = {
  id: string;
  type: string;
  agent?: string | null;
  status?: string;
};

export type Workflow = {
  active: boolean;
  current_step?: string | null;
  model?: string | null;
  total_tokens: number;
};

const LANES: { key: string; label: string }[] = [
  { key: "sm", label: "SM" },
  { key: "qa", label: "QA" },
  { key: "dev", label: "DEV" },
  { key: "gate", label: "Gates" },
];

function laneFor(step: Step): string {
  if (step.type === "gate") return "gate";
  return step.agent ?? "gate";
}

function humanize(id: string) {
  return id.replace(/_/g, " ");
}

function StepCard({ step, isCurrent }: { step: Step; isCurrent: boolean }) {
  const status = step.status ?? "pending";
  const done = status === "completed";
  const isGate = step.type === "gate";

  let dot, cls;
  if (done) {
    dot = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
    cls = "border-[color:var(--midground-base)]/10 opacity-60";
  } else if (isCurrent) {
    dot = <CircleDot className="w-3.5 h-3.5 text-cyan-300" />;
    cls = "border-cyan-400/60 bg-cyan-400/10 shadow-[0_0_12px_-4px_rgba(34,211,238,0.4)]";
  } else if (isGate) {
    dot = <Lock className="w-3.5 h-3.5 text-amber-300/70" />;
    cls = "border-amber-400/20 bg-amber-400/5";
  } else {
    dot = <Circle className="w-3.5 h-3.5 opacity-30" />;
    cls = "border-[color:var(--midground-base)]/10 opacity-60";
  }

  return (
    <div className={cn("px-2.5 py-2 rounded-md border text-xs flex items-center gap-2", cls)}>
      {dot}
      <span className={cn("truncate capitalize", isCurrent && "font-medium")}>{humanize(step.id)}</span>
    </div>
  );
}

export default function WorkflowLanes({ steps, workflow }: { steps: Step[]; workflow?: Workflow }) {
  const completed = steps.filter((s) => s.status === "completed").length;
  const currentId = workflow?.current_step ?? null;
  const currentStep = currentId ? steps.find((s) => s.id === currentId) : undefined;
  const grouped = LANES.map((l) => ({ ...l, steps: steps.filter((s) => laneFor(s) === l.key) }));

  return (
    <div className="space-y-4">
      {workflow?.active && currentStep ? (
        <div className="rounded-md border border-cyan-400/30 bg-cyan-400/[0.04] px-4 py-3">
          <div className="text-[10px] uppercase tracking-wider opacity-70 mb-1">Now running</div>
          <div className="flex flex-wrap items-baseline gap-3 text-sm">
            <span className="font-medium capitalize">{humanize(currentStep.id)}</span>
            {currentStep.agent && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-[color:var(--midground-base)]/10 opacity-70">{currentStep.agent}</span>
            )}
            {workflow.model && <span className="text-xs opacity-60 font-mono">{workflow.model}</span>}
            {workflow.total_tokens > 0 && (
              <span className="text-xs opacity-60 font-mono">{workflow.total_tokens.toLocaleString()} tok</span>
            )}
          </div>
          <div className="mt-2.5 h-1 rounded-full bg-[color:var(--midground-base)]/10 overflow-hidden">
            <div className="h-full bg-cyan-400/70 transition-[width]" style={{ width: `${steps.length ? (completed / steps.length) * 100 : 0}%` }} />
          </div>
          <div className="text-[10px] uppercase tracking-wider opacity-50 mt-1.5">
            {completed} of {steps.length} steps complete
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-[color:var(--midground-base)]/15 px-4 py-3 text-xs opacity-60">
          No workflow active. Pipeline below shows the default PRISM SM→QA→DEV cycle.
        </div>
      )}

      <div className="grid grid-cols-4 gap-3">
        {grouped.map((lane) => (
          <div key={lane.key}>
            <div className="text-[10px] uppercase tracking-wider opacity-50 mb-2 pb-2 border-b border-[color:var(--midground-base)]/10">{lane.label}</div>
            <div className="space-y-1.5">
              {lane.steps.length === 0
                ? <div className="text-[11px] opacity-30 italic px-2">empty</div>
                : lane.steps.map((s) => <StepCard key={s.id} step={s} isCurrent={s.id === currentId} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
