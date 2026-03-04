"""ASCII snapshot renderer for the PRISM Dashboard.

Outputs a non-interactive text snapshot of the workflow state
suitable for embedding in Claude sessions or piping to other tools.

Usage:
    python prism-cli --snapshot
    python prism-cli --snapshot --path /your/project
"""

from __future__ import annotations

import glob as _glob
import json as _json
from datetime import datetime
from pathlib import Path

from models import WORKFLOW_STEPS, WorkflowState, StoryInfo
from parsing import check_plugin_cache_stale, parse_state_file, parse_story_file


def _read_plugin_version() -> str:
    """Read version from plugin.json; returns empty string on failure."""
    import os
    try:
        root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if root:
            plugin_json = Path(root) / ".claude-plugin" / "plugin.json"
        else:
            plugin_json = Path(__file__).resolve().parent.parent.parent / ".claude-plugin" / "plugin.json"
        data = _json.loads(plugin_json.read_text(encoding="utf-8"))
        return str(data.get("version", ""))
    except Exception:
        return ""


_PLUGIN_VERSION: str = _read_plugin_version()


def _inject_live_tokens(state: WorkflowState) -> None:
    """Parse the session transcript to get live token totals.

    Fixes step_tokens_start when it's 0 but step_history has data.
    Mutates state in-place for display only.
    """
    if not state.session_id:
        return
    pattern = str(
        Path.home() / ".claude" / "projects" / "*" / f"{state.session_id}.jsonl"
    )
    matches = _glob.glob(pattern)
    if not matches:
        return
    tp = Path(matches[0])
    if not tp.exists():
        return

    total = 0
    model = ""
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    entry = _json.loads(stripped)
                except _json.JSONDecodeError:
                    continue
                usage = entry.get("usage")
                if not usage and isinstance(entry.get("message"), dict):
                    usage = entry["message"].get("usage")
                if usage and isinstance(usage, dict):
                    total += usage.get("input_tokens", 0)
                    total += usage.get("cache_creation_input_tokens", 0)
                    total += usage.get("cache_read_input_tokens", 0)
                    total += usage.get("output_tokens", 0)
                m = entry.get("model")
                if not m and isinstance(entry.get("message"), dict):
                    m = entry["message"].get("model")
                if m:
                    model = m
    except (IOError, OSError):
        return

    state.total_tokens = max(state.total_tokens, total)
    if model and not state.model:
        state.model = model
    if state.step_tokens_start == 0 and state.step_history_parsed:
        computed = sum(int(e.get("t", 0)) for e in state.step_history_parsed)
        if computed > 0:
            state.step_tokens_start = computed


# Agent definitions (mirrors agent_roster.py)
AGENTS = [
    ("SM", "Sam", "Story Planning", [0, 1, 2]),
    ("QA", "Quinn", "Test Architect", [3, 6]),
    ("DEV", "Prism", "Developer", [5]),
]


def _parse_step_history(raw: str) -> list[dict]:
    """Parse step_history JSON with fallback for double-escaped values.

    update_state_file in prism_stop_hook.py wraps the JSON in quotes and
    escapes inner double-quotes, producing e.g. step_history: "[{\"i\": 0}]".
    parse_state_file strips outer quotes, leaving backslash-quote pairs that
    json.loads rejects.  This function tries a second pass after unescaping.
    """
    if not raw:
        return []
    try:
        return _json.loads(raw)
    except (_json.JSONDecodeError, ValueError, TypeError):
        pass
    try:
        return _json.loads(raw.replace('\\"', '"'))
    except (_json.JSONDecodeError, ValueError, TypeError):
        return []


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m"


def _fmt_tokens(count: int) -> str:
    """Format token count compactly: 1234 -> 1.2k, 1234567 -> 1.2M."""
    if count < 1000:
        return str(count)
    if count < 1_000_000:
        return f"{count / 1000:.1f}k"
    return f"{count / 1_000_000:.1f}M"


def _fmt_bar(value: int, total: int, width: int = 10) -> str:
    """Proportional block bar: '██░░░░░░░░' means value/total fraction filled."""
    if total <= 0 or value <= 0:
        return ""
    filled = min(width, round(value / total * width))
    return "█" * filled + "░" * (width - filled)


def _render_activity_feed(state: "WorkflowState", lines: list[str], max_entries: int = 10) -> None:
    """Append ACTIVITY FEED section lines: recent tool calls from transcript."""
    if not state.session_id:
        lines.append("  No session ID — cannot read transcript")
        lines.append("")
        return
    pattern = str(
        Path.home() / ".claude" / "projects" / "*" / f"{state.session_id}.jsonl"
    )
    matches = _glob.glob(pattern)
    if not matches:
        lines.append("  No transcript found")
        lines.append("")
        return
    tp = Path(matches[0])
    entries: list[str] = []
    try:
        with open(tp, encoding="utf-8", errors="replace") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    entry = _json.loads(stripped)
                except _json.JSONDecodeError:
                    continue
                # Extract tool_use items from message content arrays
                content = None
                if isinstance(entry.get("message"), dict):
                    content = entry["message"].get("content")
                elif isinstance(entry.get("content"), list):
                    content = entry["content"]
                if not isinstance(content, list):
                    continue
                ts_raw = entry.get("timestamp") or entry.get("message", {}).get("timestamp", "")
                if ts_raw:
                    try:
                        ts_dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                        ts_str = ts_dt.strftime("%H:%M:%S")
                    except (ValueError, AttributeError):
                        ts_str = ts_raw[:8] if len(ts_raw) >= 8 else ts_raw
                else:
                    ts_str = "--:--:--"
                for item in content:
                    if not isinstance(item, dict) or item.get("type") != "tool_use":
                        continue
                    tool_name = item.get("name", "?")
                    inp = item.get("input") or {}
                    # Build compact args string
                    if isinstance(inp, dict):
                        parts = []
                        for k, v in list(inp.items())[:2]:
                            v_str = str(v).replace("\n", " ")
                            if len(v_str) > 30:
                                v_str = v_str[:27] + "..."
                            parts.append(f"{k}={v_str}")
                        args_str = ", ".join(parts)
                    else:
                        args_str = str(inp)[:40]
                    entries.append(f"  {ts_str} TOOL {tool_name:<18} {args_str}")
    except (IOError, OSError):
        lines.append("  Error reading transcript")
        lines.append("")
        return
    recent = entries[-max_entries:] if len(entries) > max_entries else entries
    if recent:
        lines.extend(recent)
    else:
        lines.append("  No tool calls in transcript")
    lines.append("")


def render_snapshot(work_dir: Path) -> str:
    """Render a full ASCII snapshot of the PRISM dashboard state."""
    state_file = work_dir / ".claude" / "prism-loop.local.md"
    state = parse_state_file(state_file)

    lines: list[str] = []
    now = datetime.now()

    if state and state.active:
        _inject_live_tokens(state)

    cache = check_plugin_cache_stale(work_dir)

    # Header
    lines.append("=" * 64)
    _version_suffix = f" v{_PLUGIN_VERSION}" if _PLUGIN_VERSION else ""
    lines.append(f"  PRISM Dashboard Snapshot{_version_suffix}")
    lines.append(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    if state and state.active and state.current_step:
        lines.append(f"  Step: {state.current_step}")
    if cache["linked"]:
        lines.append("  [*] CACHE LIVE — junction active, edits apply instantly")
    elif cache["stale"]:
        lines.append("  [!] CACHE STALE — source newer than ~/.claude/plugins/cache")
    lines.append("=" * 64)
    lines.append("")

    if not state or not state.active:
        lines.append("  No active workflow.")
        lines.append("")
        lines.append(f"  State file: {state_file}")
        lines.append(f"  Exists: {state_file.exists()}")
        return "\n".join(lines)

    # Timing
    elapsed_secs = 0
    step_elapsed_secs = 0
    pre_step_secs = 0
    is_stale = False
    if state.started_at_dt:
        elapsed_secs = max(0, int((now - state.started_at_dt).total_seconds()))
        step_ref = state.step_started_at_dt or state.started_at_dt
        step_elapsed_secs = max(0, int((now - step_ref).total_seconds()))
        if state.step_started_at_dt:
            pre_step_secs = max(0, int(
                (state.step_started_at_dt - state.started_at_dt).total_seconds()
            ))
        if state.last_activity_dt:
            stale_secs = int((now - state.last_activity_dt).total_seconds())
            is_stale = stale_secs > 600
        elif elapsed_secs > 300:
            is_stale = True

    current_idx = state.current_step_index

    # Parse step_history once for agent token lookups
    step_hist_index: dict[int, dict] = {}
    for entry in _parse_step_history(state.step_history):
        try:
            step_hist_index[int(entry["i"])] = entry
        except (KeyError, TypeError, ValueError):
            pass

    # --- Agent Roster ---
    lines.append("AGENTS")
    lines.append("-" * 64)
    lines.append(
        f"{'St':<4} {'Agent':<14} {'Role':<18} {'Phase':<12} "
        f"{'State':<10} {'Duration':<10} {'Tokens':<8} {'Tok/min':<8}"
    )
    for agent_id, name, role, step_indices in AGENTS:
        active_step = None
        all_done = True
        for si in step_indices:
            if si == current_idx:
                active_step = WORKFLOW_STEPS[si]
            if si >= current_idx:
                all_done = False

        if active_step is not None:
            if is_stale:
                dot, agent_state = "!", "STALE"
            elif state.paused_for_manual:
                dot, agent_state = "*", "waiting"
            else:
                dot, agent_state = "*", "working"
            phase = active_step.phase
            agent_dur = _fmt_duration(step_elapsed_secs)  # ticks up: current step only
        elif all_done:
            dot, agent_state, phase = "v", "done", "done"
            agent_dur = _fmt_duration(pre_step_secs)  # frozen: time before current step
        else:
            dot, agent_state = "o", "idle"
            next_si = next((si for si in step_indices if si > current_idx), step_indices[0])
            phase = WORKFLOW_STEPS[next_si].phase
            agent_dur = "-"

        # Token stats — per-step for working agent, pre-step for done
        tokens_str = "-"
        tpm_str = "-"
        if state.total_tokens > 0:
            if active_step is not None:
                step_toks = state.step_tokens
                tokens_str = _fmt_tokens(step_toks)
                if step_elapsed_secs > 0 and step_toks > 0:
                    tpm = step_toks / (step_elapsed_secs / 60)
                    tpm_str = _fmt_tokens(int(tpm))
            elif all_done:
                agent_toks = sum(
                    int(step_hist_index[si].get("t", 0))
                    for si in step_indices
                    if si in step_hist_index
                )
                tokens_str = _fmt_tokens(agent_toks)

        display = f"{name} ({agent_id})"
        lines.append(
            f"{dot:<4} {display:<14} {role:<18} {phase:<12} "
            f"{agent_state:<10} {agent_dur:<10} {tokens_str:<8} {tpm_str:<8}"
        )

    lines.append("")

    # --- Workflow Steps ---
    # Live timing for current step
    step_ref = state.step_started_at_dt or state.started_at_dt
    step_elapsed_live = max(0, int((now - step_ref).total_seconds())) if step_ref else 0
    step_dur_str = _fmt_duration(step_elapsed_live) if step_ref else "-"

    # History lookup: step_index -> {i, d, t}
    history: dict[int, dict] = {}
    for entry in _parse_step_history(state.step_history):
        try:
            history[int(entry["i"])] = entry
        except (KeyError, TypeError, ValueError):
            pass

    # Totals for proportional bar scaling
    # Exclude current step if it's a gate or stale — avoids gate duration dominating bars
    total_dur = sum(int(h.get("d", 0)) for h in history.values())
    total_toks = sum(int(h.get("t", 0)) for h in history.values())
    _cur_step_snap = WORKFLOW_STEPS[current_idx] if 0 <= current_idx < len(WORKFLOW_STEPS) else None
    _is_cur_gate = _cur_step_snap is not None and _cur_step_snap.step_type == "gate"
    if not _is_cur_gate and not is_stale:
        total_dur += step_elapsed_live
        total_toks += state.step_tokens if state else 0

    lines.append("WORKFLOW")
    lines.append("-" * 80)
    lines.append(
        f"{'#':<4} {'Step':<24} {'Agent':<6} {'Phase':<12} "
        f"{'Duration':<10} {'DurBar':<8} {'Tokens':<8} {'TokBar':<8} {'Tok/min':<8} {'Skills':<8} {'Status'}"
    )
    for step in WORKFLOW_STEPS:
        if step.index < current_idx:
            hist = history.get(step.index)
            if hist:
                d_secs = int(hist.get("d", 0))
                t_toks = int(hist.get("t", 0))
                s_calls = int(hist.get("s", 0))
                tc_calls = int(hist.get("tc", 0))
                dur = _fmt_duration(d_secs)
                tok = _fmt_tokens(t_toks)
                tpm_val = t_toks / (d_secs / 60) if d_secs > 0 and t_toks > 0 else 0
                tpm = _fmt_tokens(int(tpm_val)) if tpm_val > 0 else "-"
                skills = f"{s_calls}/{tc_calls}" if tc_calls > 0 else "-"
                dur_bar = _fmt_bar(d_secs, total_dur)
                tok_bar = _fmt_bar(t_toks, total_toks)
            else:
                dur, tok, tpm, skills = "-", "-", "-", "-"
                dur_bar, tok_bar = "", ""
            status = "DONE"
        elif step.index == current_idx:
            dur = step_dur_str
            step_toks = state.step_tokens
            tok = _fmt_tokens(step_toks) if step_toks > 0 else "0"
            if step_elapsed_live > 0 and step_toks > 0:
                tpm = _fmt_tokens(int(step_toks / (step_elapsed_live / 60)))
            else:
                tpm = "-"
            skills = "live"
            if step.step_type == "gate":
                dur_bar = ""
                tok_bar = ""
            else:
                dur_bar = _fmt_bar(step_elapsed_live, total_dur)
                tok_bar = _fmt_bar(step_toks, total_toks)
            if is_stale:
                status = "STALE"
            elif state.paused_for_manual and step.step_type == "gate":
                status = ">> GATE"
            else:
                status = ">> RUNNING"
        else:
            dur, tok, tpm, skills, status = "", "", "", "", "."
            dur_bar, tok_bar = "", ""

        lines.append(
            f"{step.index + 1:<4} {step.id:<24} {step.agent:<6} {step.phase:<12} "
            f"{dur:<10} {dur_bar:<8} {tok:<8} {tok_bar:<8} {tpm:<8} {skills:<8} {status}"
        )

    lines.append("")

    # --- Gate Alert ---
    if state.paused_for_manual:
        gate_id = state.current_step
        lines.append("!" * 64)
        lines.append("  ACTION REQUIRED")
        if gate_id == "red_gate":
            lines.append(
                "  RED GATE - Tests failing with assertions. "
                "Review before GREEN."
            )
        elif gate_id == "green_gate":
            lines.append(
                "  GREEN GATE - All tests passing. "
                "Review before completing."
            )
        else:
            lines.append(f"  Paused at {gate_id}")
        lines.append("  /prism-approve -> Continue")
        lines.append("  /prism-reject  -> Loop back to Planning")
        lines.append("!" * 64)
        lines.append("")

    # --- Story Panel ---
    story: StoryInfo | None = None
    if state.story_file:
        story_path = Path(state.story_file)
        if not story_path.is_absolute():
            story_path = work_dir / story_path
        story = parse_story_file(story_path, work_dir)

    lines.append("STORY")
    lines.append("-" * 64)
    if story and story.exists:
        lines.append(f"  File: {story.path}")
        # Green test progress bar (ASCII, no Rich markup)
        p, t = story.green_tests_passing, story.green_tests_total
        if t > 0:
            width = 20
            filled = round((p / t) * width)
            progress = "#" * filled + "." * (width - filled)
            lines.append(f"  Green: [{progress}] {p}/{t} ({int(p/t*100)}%)")
        else:
            lines.append("  Green: [....................] no tests yet")
        lines.append(f"  ACs:  {len(story.acceptance_criteria)} found")
        for ac in story.acceptance_criteria[:6]:
            display = ac if len(ac) <= 55 else ac[:52] + "..."
            lines.append(f"    {display}")
        if len(story.acceptance_criteria) > 6:
            lines.append(
                f"    ... and {len(story.acceptance_criteria) - 6} more"
            )
        if story.has_plan_coverage:
            lines.append(
                f"  Coverage: {story.covered_count} covered, "
                f"{story.missing_count} missing"
            )
    elif state.story_file:
        lines.append(f"  File: {state.story_file} (not found)")
    else:
        lines.append("  No story file")

    lines.append("")

    # --- Activity Feed ---
    lines.append("ACTIVITY FEED")
    lines.append("-" * 64)
    _render_activity_feed(state, lines, max_entries=10)

    # --- Step Detail ---
    lines.append("STEP DETAIL")
    lines.append("-" * 64)
    idx = state.current_step_index
    if 0 <= idx < len(WORKFLOW_STEPS):
        step = WORKFLOW_STEPS[idx]
        type_desc = "gate (manual review)" if step.step_type == "gate" else "agent (auto)"
        validation = step.validation or "none"
        lines.append(f"  Step {step.index + 1}: {step.id}")
        lines.append(f"  Phase: {step.phase}")
        lines.append(f"  Type:  {type_desc}")
        lines.append(f"  Agent: {step.agent}")
        lines.append(f"  Validation: {validation}")
    else:
        lines.append(f"  Step index {idx} out of range")

    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)
