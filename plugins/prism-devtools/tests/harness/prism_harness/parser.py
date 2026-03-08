"""JSONL stream-json output parser.

Extracts structured data from claude --output-format stream-json output.
Each line is a JSON object (event) with a 'type' field.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HarnessEvent:
    type: str
    raw: dict


@dataclass
class SubagentSpawn:
    """An Agent tool_use block in an assistant message."""

    tool_use_id: str
    description: str
    subagent_type: str
    prompt: str
    raw: dict


@dataclass
class SubagentLifecycle:
    """Correlated spawn → start → stop chain for a sub-agent invocation."""

    tool_use_id: str
    agent_name: str
    prompt_id: str
    description: str
    subagent_type: str
    prompt: str
    start_event: dict | None
    stop_event: dict | None
    outcome: str  # "success" | "error" | "unknown"


@dataclass
class SfrCertificate:
    """SFR template sections detected in assistant output."""

    sections: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class HookEvent:
    """A hook_progress system message."""

    hook_name: str
    content: str
    raw: dict


def parse_jsonl(path: Path | str) -> list[HarnessEvent]:
    """Parse all valid JSON lines from a stream-json file."""
    events: list[HarnessEvent] = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    events.append(HarnessEvent(type=obj.get("type", ""), raw=obj))
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return events


def extract_tool_calls(events: list[HarnessEvent]) -> list[dict]:
    """Extract all tool_use blocks from assistant messages."""
    tool_calls: list[dict] = []
    for ev in events:
        if ev.type == "assistant":
            content = ev.raw.get("message", {}).get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append(block)
    return tool_calls


def extract_assistant_text(events: list[HarnessEvent]) -> list[str]:
    """Extract all text blocks from assistant messages."""
    texts: list[str] = []
    for ev in events:
        if ev.type == "assistant":
            content = ev.raw.get("message", {}).get("content") or []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block["text"])
    return texts


def extract_hook_messages(events: list[HarnessEvent]) -> list[str]:
    """Extract system/hook injection messages."""
    messages: list[str] = []
    for ev in events:
        if ev.type == "system":
            content = ev.raw.get("message", {}).get("content", "")
            if content:
                messages.append(str(content))
    return messages


def count_turns(events: list[HarnessEvent]) -> int:
    """Count the number of assistant turns."""
    return sum(1 for ev in events if ev.type == "assistant")


def deep_get(obj: Any, path: str) -> Any:
    """Navigate a nested dict/list using dot notation (e.g. 'message.content')."""
    for key in path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return obj


# ---------------------------------------------------------------------------
# Sub-agent lifecycle extractors
# ---------------------------------------------------------------------------

_SFR_SECTIONS = ("PREMISES", "EXECUTION TRACE", "ANALYSIS", "COUNTEREXAMPLE", "CONCLUSION")


def extract_subagent_spawns(events: list[HarnessEvent]) -> list[SubagentSpawn]:
    """Extract Agent tool_use blocks from assistant messages.

    Each block represents a sub-agent being spawned.  The returned list is in
    event order so callers can correlate with SubagentStart/Stop events by index
    or by tool_use_id.
    """
    spawns: list[SubagentSpawn] = []
    for ev in events:
        if ev.type != "assistant":
            continue
        content = ev.raw.get("message", {}).get("content") or []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") != "Agent":
                continue
            inp = block.get("input") or {}
            spawns.append(
                SubagentSpawn(
                    tool_use_id=block.get("id", ""),
                    description=inp.get("description", ""),
                    subagent_type=inp.get("subagent_type", ""),
                    prompt=inp.get("prompt", ""),
                    raw=block,
                )
            )
    return spawns


def extract_hook_events(events: list[HarnessEvent]) -> list[HookEvent]:
    """Extract hook_progress system messages.

    Matches system events whose content starts with 'hook_progress' or whose
    top-level 'subtype' field equals 'hook_progress'.  Both the structured
    (subtype field) and text-embedded formats are handled.
    """
    hook_events: list[HookEvent] = []
    for ev in events:
        if ev.type != "system":
            continue

        # Structured format: {"type": "system", "subtype": "hook_progress", ...}
        if ev.raw.get("subtype") == "hook_progress":
            hook_name = ev.raw.get("hook_name", ev.raw.get("name", ""))
            content = str(ev.raw.get("content", ev.raw.get("message", {}).get("content", "")))
            hook_events.append(HookEvent(hook_name=hook_name, content=content, raw=ev.raw))
            continue

        # Text-embedded format: message.content starts with "hook_progress"
        content_val = ev.raw.get("message", {}).get("content", "")
        if not isinstance(content_val, str):
            continue
        if content_val.startswith("hook_progress"):
            # Try to parse "hook_progress: <name>: <body>"
            parts = content_val.split(":", 2)
            hook_name = parts[1].strip() if len(parts) >= 2 else ""
            body = parts[2].strip() if len(parts) >= 3 else content_val
            hook_events.append(HookEvent(hook_name=hook_name, content=body, raw=ev.raw))

    return hook_events


def extract_sfr_certificates(events: list[HarnessEvent]) -> list[SfrCertificate]:
    """Detect SFR template sections in assistant text output.

    Scans assistant text blocks for the canonical SFR section headers:
    PREMISES, EXECUTION TRACE, ANALYSIS, COUNTEREXAMPLE, CONCLUSION.
    Returns one SfrCertificate per text block that contains at least one
    recognized section header.
    """
    certificates: list[SfrCertificate] = []

    # Build a pattern that matches any section header at the start of a line,
    # optionally surrounded by markdown markers (##, **, ---).
    _header_pat = re.compile(
        r"^\s*(?:#+\s*|[\*_]{0,2})?("
        + "|".join(re.escape(s) for s in _SFR_SECTIONS)
        + r")(?:[\*_]{0,2})?[\s:]*$",
        re.IGNORECASE | re.MULTILINE,
    )

    for ev in events:
        if ev.type != "assistant":
            continue
        content = ev.raw.get("message", {}).get("content") or []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = block.get("text", "")
            headers_found = _header_pat.findall(text)
            if not headers_found:
                continue

            # Extract content under each section header
            sections: dict[str, str] = {}
            lines = text.splitlines()
            current_section: str | None = None
            section_lines: list[str] = []

            for line in lines:
                m = re.match(
                    r"^\s*(?:#+\s*|[\*_]{0,2})?("
                    + "|".join(re.escape(s) for s in _SFR_SECTIONS)
                    + r")(?:[\*_]{0,2})?[\s:]*$",
                    line,
                    re.IGNORECASE,
                )
                if m:
                    if current_section is not None:
                        sections[current_section] = "\n".join(section_lines).strip()
                    current_section = m.group(1).upper()
                    section_lines = []
                elif current_section is not None:
                    section_lines.append(line)

            if current_section is not None:
                sections[current_section] = "\n".join(section_lines).strip()

            if sections:
                certificates.append(SfrCertificate(sections=sections, raw_text=text))

    return certificates


def correlate_subagent_lifecycle(events: list[HarnessEvent]) -> list[SubagentLifecycle]:
    """Map spawn → start → stop chains for each sub-agent invocation.

    Matches Agent tool_use blocks (spawns) with SubagentStart/SubagentStop
    system events by tool_use_id where available, or by positional order when
    IDs are absent.  Each returned SubagentLifecycle record includes the
    prompt_id, agent name, outcome, and references to start/stop raw events.
    """
    spawns = extract_subagent_spawns(events)
    if not spawns:
        return []

    # Collect SubagentStart events indexed by tool_use_id and order
    start_events: dict[str, dict] = {}
    stop_events: dict[str, dict] = {}
    start_ordered: list[dict] = []
    stop_ordered: list[dict] = []

    for ev in events:
        if ev.type != "system":
            continue
        subtype = ev.raw.get("subtype", "")
        content_str = ev.raw.get("message", {}).get("content", "")

        is_start = subtype == "SubagentStart" or (
            isinstance(content_str, str) and "SubagentStart" in content_str
        )
        is_stop = subtype == "SubagentStop" or (
            isinstance(content_str, str) and "SubagentStop" in content_str
        )

        if is_start:
            tid = ev.raw.get("tool_use_id", ev.raw.get("prompt_id", ""))
            if tid:
                start_events[tid] = ev.raw
            start_ordered.append(ev.raw)
        elif is_stop:
            tid = ev.raw.get("tool_use_id", ev.raw.get("prompt_id", ""))
            if tid:
                stop_events[tid] = ev.raw
            stop_ordered.append(ev.raw)

    result: list[SubagentLifecycle] = []
    for idx, spawn in enumerate(spawns):
        tid = spawn.tool_use_id

        start_ev = start_events.get(tid) or (start_ordered[idx] if idx < len(start_ordered) else None)
        stop_ev = stop_events.get(tid) or (stop_ordered[idx] if idx < len(stop_ordered) else None)

        # Derive agent_name and prompt_id from start event or spawn fields
        agent_name = ""
        prompt_id = ""
        outcome = "unknown"

        if start_ev:
            agent_name = start_ev.get("agent_name", start_ev.get("name", ""))
            prompt_id = start_ev.get("prompt_id", "")
        if stop_ev:
            if not agent_name:
                agent_name = stop_ev.get("agent_name", stop_ev.get("name", ""))
            if not prompt_id:
                prompt_id = stop_ev.get("prompt_id", "")
            outcome = stop_ev.get("outcome", "success" if stop_ev else "unknown")

        result.append(
            SubagentLifecycle(
                tool_use_id=tid,
                agent_name=agent_name or spawn.subagent_type,
                prompt_id=prompt_id,
                description=spawn.description,
                subagent_type=spawn.subagent_type,
                prompt=spawn.prompt,
                start_event=start_ev,
                stop_event=stop_ev,
                outcome=outcome,
            )
        )

    return result
