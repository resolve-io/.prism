"""Diagnostic analysis of prism session transcripts.

Analyzes a JSONL transcript and produces structured PASS/FAIL/WARN results.

Diagnostic checks
-----------------
- subagent-lifecycle  — sub-agent spawn/stop completeness
- sfr-certificates    — SFR certificate injection
- hook-chain          — hook_progress events, failure indicators
- event-summary       — basic transcript health

Uses parser extractor functions when available; gracefully degrades if
the sibling parser-extractor-builder has not yet merged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .assertions import _c, _C_GREEN, _C_RED, _C_YELLOW
from .parser import HarnessEvent, count_turns


# ---------------------------------------------------------------------------
# Graceful imports from parser (sibling builder may not have merged yet)
# ---------------------------------------------------------------------------

try:
    from .parser import correlate_subagent_lifecycle  # type: ignore[attr-defined]
except ImportError:
    correlate_subagent_lifecycle = None  # type: ignore[assignment]

try:
    from .parser import extract_sfr_certificates  # type: ignore[attr-defined]
except ImportError:
    extract_sfr_certificates = None  # type: ignore[assignment]

try:
    from .parser import extract_hook_events  # type: ignore[attr-defined]
except ImportError:
    extract_hook_events = None  # type: ignore[assignment]

try:
    from .parser import extract_subagent_spawns  # type: ignore[attr-defined]
except ImportError:
    extract_subagent_spawns = None  # type: ignore[assignment]

try:
    from .parser import extract_subagent_system_events  # type: ignore[attr-defined]
except ImportError:
    extract_subagent_system_events = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# DiagnosticResult
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticResult:
    name: str           # e.g. "subagent-lifecycle"
    status: str         # "PASS" | "WARN" | "FAIL"
    detail: str         # human-readable explanation
    data: dict | None = None  # optional structured data


# ---------------------------------------------------------------------------
# Fallback helpers (used when parser extractor functions are not available)
# ---------------------------------------------------------------------------

def _all_text_blobs(events: list[HarnessEvent]) -> list[str]:
    """Collect all text content from every event."""
    texts: list[str] = []
    for ev in events:
        msg = ev.raw.get("message", {})
        content = msg.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        inner = block.get("content", "")
                        if isinstance(inner, str):
                            texts.append(inner)
                        elif isinstance(inner, list):
                            for ib in inner:
                                if isinstance(ib, dict) and ib.get("type") == "text":
                                    texts.append(ib.get("text", ""))
    return texts


def _contains_any(texts: list[str], *keywords: str) -> bool:
    lower = [t.lower() for t in texts]
    return any(any(kw.lower() in t for kw in keywords) for t in lower)


# ---------------------------------------------------------------------------
# Diagnostic checks
# ---------------------------------------------------------------------------

def _check_subagent_lifecycle(events: list[HarnessEvent]) -> DiagnosticResult:
    """Check 1: sub-agent lifecycle completeness."""
    if correlate_subagent_lifecycle is not None:
        lifecycle_data = correlate_subagent_lifecycle(events)
    else:
        # Fallback: look for Agent tool calls in assistant messages
        from .parser import extract_tool_calls
        tool_calls = extract_tool_calls(events)
        agent_calls = [tc for tc in tool_calls if tc.get("name") == "Agent"]
        if not agent_calls:
            return DiagnosticResult(
                name="subagent-lifecycle",
                status="PASS",
                detail="No sub-agent events found",
            )
        lifecycle_data = [{"type": "spawn", "complete": False} for _ in agent_calls]

    if not lifecycle_data:
        return DiagnosticResult(
            name="subagent-lifecycle",
            status="PASS",
            detail="No sub-agent events found",
        )

    complete = [e for e in lifecycle_data if e.get("complete", False)]
    total = len(lifecycle_data)

    if len(complete) == total:
        return DiagnosticResult(
            name="subagent-lifecycle",
            status="PASS",
            detail=f"All {total} spawn(s) have complete lifecycle (started+stopped)",
            data={"total": total, "complete": len(complete)},
        )
    if complete:
        return DiagnosticResult(
            name="subagent-lifecycle",
            status="WARN",
            detail=f"{len(complete)}/{total} spawns completed; some only started but did not stop",
            data={"total": total, "complete": len(complete)},
        )
    return DiagnosticResult(
        name="subagent-lifecycle",
        status="FAIL",
        detail=f"{total} spawn(s) found but none completed lifecycle",
        data={"total": total, "complete": 0},
    )


def _check_sfr_certificates(events: list[HarnessEvent]) -> DiagnosticResult:
    """Check 2: SFR certificate injection."""
    # Check if there are any text-bearing events at all
    texts = _all_text_blobs(events)
    if not texts:
        return DiagnosticResult(
            name="sfr-certificates",
            status="PASS",
            detail="No SFR content expected",
        )

    if extract_sfr_certificates is not None:
        certs = extract_sfr_certificates(events)
        complete_certs = [c for c in certs if c.get("complete", False)]
        if complete_certs:
            return DiagnosticResult(
                name="sfr-certificates",
                status="PASS",
                detail=f"{len(complete_certs)} complete SFR certificate(s) found",
                data={"total": len(certs), "complete": len(complete_certs)},
            )
        if certs:
            return DiagnosticResult(
                name="sfr-certificates",
                status="WARN",
                detail=f"{len(certs)} partial SFR section(s) found but none complete",
                data={"total": len(certs), "complete": 0},
            )
        return DiagnosticResult(
            name="sfr-certificates",
            status="FAIL",
            detail="No SFR sections detected",
        )

    # Fallback: keyword scan
    sfr_present = _contains_any(texts, "SFR", "sfr", "certificate", "CERTIFICATE")
    if sfr_present:
        return DiagnosticResult(
            name="sfr-certificates",
            status="PASS",
            detail="SFR/certificate keywords found in transcript (fallback check)",
        )
    return DiagnosticResult(
        name="sfr-certificates",
        status="WARN",
        detail="No SFR/certificate keywords found (parser extractor unavailable)",
    )


def _check_hook_chain(events: list[HarnessEvent]) -> DiagnosticResult:
    """Check 3: hook chain health."""
    # Check if any system events exist
    system_events = [ev for ev in events if ev.type == "system"]
    if not system_events:
        return DiagnosticResult(
            name="hook-chain",
            status="PASS",
            detail="No hook events expected",
        )

    if extract_hook_events is not None:
        hook_evs = extract_hook_events(events)
        if not hook_evs:
            return DiagnosticResult(
                name="hook-chain",
                status="FAIL",
                detail="System events present but no hook events found (hooks expected but missing)",
                data={"system_events": len(system_events), "hook_events": 0},
            )
        error_evs = [
            e for e in hook_evs
            if "error" in str(e.get("content", "")).lower()
            or "fail" in str(e.get("content", "")).lower()
        ]
        if error_evs:
            return DiagnosticResult(
                name="hook-chain",
                status="WARN",
                detail=f"{len(hook_evs)} hook event(s), {len(error_evs)} contain(s) error/fail indicators",
                data={"hook_events": len(hook_evs), "error_events": len(error_evs)},
            )
        return DiagnosticResult(
            name="hook-chain",
            status="PASS",
            detail=f"{len(hook_evs)} hook_progress event(s) found with no failure indicators",
            data={"hook_events": len(hook_evs)},
        )

    # Fallback: look for hook_progress in text
    texts = _all_text_blobs(events)
    failure_keywords = ["hook failed", "hook error", "exit code 1", "traceback"]
    has_progress = _contains_any(texts, "hook_progress")
    has_failure = _contains_any(texts, *failure_keywords)

    if not has_progress:
        return DiagnosticResult(
            name="hook-chain",
            status="FAIL",
            detail="System events found but no hook_progress events detected (hooks expected but missing)",
        )
    if has_failure:
        return DiagnosticResult(
            name="hook-chain",
            status="WARN",
            detail="hook_progress events found but failure indicators present",
        )
    return DiagnosticResult(
        name="hook-chain",
        status="PASS",
        detail="hook_progress events found with no failure indicators (fallback check)",
    )


def _check_event_summary(events: list[HarnessEvent]) -> DiagnosticResult:
    """Check 4: basic transcript health."""
    if not events:
        return DiagnosticResult(
            name="event-summary",
            status="FAIL",
            detail="No events at all",
        )

    turns = count_turns(events)
    has_result = any(ev.type == "result" for ev in events)

    if turns >= 1 and has_result:
        return DiagnosticResult(
            name="event-summary",
            status="PASS",
            detail=f"{turns} assistant turn(s), result event present",
            data={"turns": turns, "total_events": len(events), "has_result": True},
        )
    if turns >= 1:
        return DiagnosticResult(
            name="event-summary",
            status="WARN",
            detail=f"{turns} assistant turn(s) but no result event",
            data={"turns": turns, "total_events": len(events), "has_result": False},
        )
    return DiagnosticResult(
        name="event-summary",
        status="WARN",
        detail=f"Events present ({len(events)}) but no assistant turns",
        data={"turns": 0, "total_events": len(events), "has_result": has_result},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_diagnostics(events: list[HarnessEvent]) -> list[DiagnosticResult]:
    """Run all diagnostic checks against parsed events.

    Returns a list of DiagnosticResult, one per check.
    """
    return [
        _check_subagent_lifecycle(events),
        _check_sfr_certificates(events),
        _check_hook_chain(events),
        _check_event_summary(events),
    ]


def format_report(results: list[DiagnosticResult], use_color: bool = False) -> str:
    """Format diagnostic results as a human-readable report string.

    Format:
        PASS  subagent-lifecycle: No sub-agent events found
        WARN  hook-chain: 2 hook events, 1 contains error indicators
    """
    lines: list[str] = []
    for r in results:
        if r.status == "PASS":
            status_str = _c(_C_GREEN, "PASS", use_color)
        elif r.status == "FAIL":
            status_str = _c(_C_RED, "FAIL", use_color)
        else:
            status_str = _c(_C_YELLOW, "WARN", use_color)
        lines.append(f"  {status_str}  {r.name}: {r.detail}")
    return "\n".join(lines)
