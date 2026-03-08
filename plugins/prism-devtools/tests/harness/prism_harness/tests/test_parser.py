"""Unit tests for prism_harness.parser sub-agent extractor functions.

TC-1: extract_subagent_spawns returns Agent tool_use blocks
TC-2: extract_subagent_spawns ignores non-Agent tool_use blocks
TC-3: extract_hook_events handles structured subtype format
TC-4: extract_hook_events handles text-embedded format
TC-5: extract_hook_events ignores non-hook system events
TC-6: extract_sfr_certificates detects SFR section headers
TC-7: extract_sfr_certificates ignores text with no SFR headers
TC-8: extract_sfr_certificates extracts section body content
TC-9: correlate_subagent_lifecycle with no spawns returns empty list
TC-10: correlate_subagent_lifecycle matches start/stop events by tool_use_id
TC-11: correlate_subagent_lifecycle falls back to positional matching
TC-12: correlate_subagent_lifecycle sets outcome from stop event
"""

from __future__ import annotations

import pytest

from ..parser import (
    HarnessEvent,
    correlate_subagent_lifecycle,
    extract_hook_events,
    extract_sfr_certificates,
    extract_subagent_spawns,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ev(type: str, raw: dict) -> HarnessEvent:
    return HarnessEvent(type=type, raw=raw)


def _assistant_agent_event(tool_use_id: str, subagent_type: str, description: str, prompt: str) -> HarnessEvent:
    return _ev(
        "assistant",
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": "Agent",
                        "input": {
                            "subagent_type": subagent_type,
                            "description": description,
                            "prompt": prompt,
                        },
                    }
                ],
            },
        },
    )


def _assistant_other_tool_event(name: str) -> HarnessEvent:
    return _ev(
        "assistant",
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "t-other", "name": name, "input": {}}],
            },
        },
    )


def _assistant_text_event(text: str) -> HarnessEvent:
    return _ev(
        "assistant",
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
            },
        },
    )


def _system_hook_structured(hook_name: str, content: str) -> HarnessEvent:
    return _ev(
        "system",
        {"type": "system", "subtype": "hook_progress", "hook_name": hook_name, "content": content},
    )


def _system_hook_text(hook_name: str, body: str) -> HarnessEvent:
    return _ev(
        "system",
        {"type": "system", "message": {"content": f"hook_progress: {hook_name}: {body}"}},
    )


def _system_event(content: str) -> HarnessEvent:
    return _ev("system", {"type": "system", "message": {"content": content}})


# ---------------------------------------------------------------------------
# TC-1 / TC-2: extract_subagent_spawns
# ---------------------------------------------------------------------------


def test_tc1_extract_subagent_spawns_returns_agent_blocks():
    events = [
        _assistant_agent_event("tu-1", "general-purpose", "Explore codebase", "Find all tests"),
    ]
    spawns = extract_subagent_spawns(events)
    assert len(spawns) == 1
    assert spawns[0].tool_use_id == "tu-1"
    assert spawns[0].subagent_type == "general-purpose"
    assert spawns[0].description == "Explore codebase"
    assert spawns[0].prompt == "Find all tests"


def test_tc2_extract_subagent_spawns_ignores_non_agent_tools():
    events = [
        _assistant_other_tool_event("Bash"),
        _assistant_other_tool_event("Read"),
        _assistant_agent_event("tu-2", "Explore", "desc", "prompt"),
    ]
    spawns = extract_subagent_spawns(events)
    assert len(spawns) == 1
    assert spawns[0].tool_use_id == "tu-2"


def test_tc1_extract_subagent_spawns_multiple():
    events = [
        _assistant_agent_event("tu-a", "Explore", "A", "prompt A"),
        _assistant_agent_event("tu-b", "Plan", "B", "prompt B"),
    ]
    spawns = extract_subagent_spawns(events)
    assert len(spawns) == 2
    assert spawns[0].tool_use_id == "tu-a"
    assert spawns[1].tool_use_id == "tu-b"


def test_tc1_extract_subagent_spawns_empty_events():
    assert extract_subagent_spawns([]) == []


# ---------------------------------------------------------------------------
# TC-3 / TC-4 / TC-5: extract_hook_events
# ---------------------------------------------------------------------------


def test_tc3_extract_hook_events_structured_format():
    events = [_system_hook_structured("session-start", "Brain reindexed")]
    hooks = extract_hook_events(events)
    assert len(hooks) == 1
    assert hooks[0].hook_name == "session-start"
    assert hooks[0].content == "Brain reindexed"


def test_tc4_extract_hook_events_text_embedded_format():
    events = [_system_hook_text("pre-commit", "lint passed")]
    hooks = extract_hook_events(events)
    assert len(hooks) == 1
    assert hooks[0].hook_name == "pre-commit"
    assert hooks[0].content == "lint passed"


def test_tc5_extract_hook_events_ignores_non_hook_system_events():
    events = [
        _system_event("SessionStart hook complete."),
        _system_hook_structured("my-hook", "done"),
        _system_event("Some other system message"),
    ]
    hooks = extract_hook_events(events)
    assert len(hooks) == 1
    assert hooks[0].hook_name == "my-hook"


def test_tc5_extract_hook_events_empty():
    assert extract_hook_events([]) == []


# ---------------------------------------------------------------------------
# TC-6 / TC-7 / TC-8: extract_sfr_certificates
# ---------------------------------------------------------------------------

_SFR_TEXT = """\
PREMISES
The function receives a list argument.
ANALYSIS
The list may be empty.
CONCLUSION
Return early if empty.
"""

_SFR_TEXT_MARKDOWN = """\
## PREMISES
Some premise here.
## EXECUTION TRACE
Step 1 ran.
## CONCLUSION
All good.
"""


def test_tc6_extract_sfr_certificates_detects_headers():
    events = [_assistant_text_event(_SFR_TEXT)]
    certs = extract_sfr_certificates(events)
    assert len(certs) == 1
    assert "PREMISES" in certs[0].sections
    assert "ANALYSIS" in certs[0].sections
    assert "CONCLUSION" in certs[0].sections


def test_tc7_extract_sfr_certificates_ignores_no_headers():
    events = [_assistant_text_event("This is just normal text with no SFR sections.")]
    certs = extract_sfr_certificates(events)
    assert certs == []


def test_tc8_extract_sfr_certificates_extracts_body():
    events = [_assistant_text_event(_SFR_TEXT)]
    certs = extract_sfr_certificates(events)
    assert certs[0].sections["PREMISES"] == "The function receives a list argument."
    assert "The list may be empty." in certs[0].sections["ANALYSIS"]
    assert "Return early if empty." in certs[0].sections["CONCLUSION"]


def test_tc8_extract_sfr_certificates_markdown_headers():
    events = [_assistant_text_event(_SFR_TEXT_MARKDOWN)]
    certs = extract_sfr_certificates(events)
    assert len(certs) == 1
    assert "PREMISES" in certs[0].sections
    assert "EXECUTION TRACE" in certs[0].sections
    assert "CONCLUSION" in certs[0].sections


def test_tc6_extract_sfr_certificates_raw_text_preserved():
    events = [_assistant_text_event(_SFR_TEXT)]
    certs = extract_sfr_certificates(events)
    assert certs[0].raw_text == _SFR_TEXT


# ---------------------------------------------------------------------------
# TC-9 / TC-10 / TC-11 / TC-12: correlate_subagent_lifecycle
# ---------------------------------------------------------------------------


def test_tc9_correlate_no_spawns_returns_empty():
    events = [_system_event("no spawns here")]
    result = correlate_subagent_lifecycle(events)
    assert result == []


def test_tc10_correlate_matches_by_tool_use_id():
    tid = "tu-xyz"
    start_ev = _ev(
        "system",
        {
            "type": "system",
            "subtype": "SubagentStart",
            "tool_use_id": tid,
            "agent_name": "my-agent",
            "prompt_id": "p-123",
        },
    )
    stop_ev = _ev(
        "system",
        {
            "type": "system",
            "subtype": "SubagentStop",
            "tool_use_id": tid,
            "agent_name": "my-agent",
            "prompt_id": "p-123",
            "outcome": "success",
        },
    )
    events = [
        _assistant_agent_event(tid, "general-purpose", "Do something", "Some prompt"),
        start_ev,
        stop_ev,
    ]
    result = correlate_subagent_lifecycle(events)
    assert len(result) == 1
    lc = result[0]
    assert lc.tool_use_id == tid
    assert lc.agent_name == "my-agent"
    assert lc.prompt_id == "p-123"
    assert lc.outcome == "success"
    assert lc.start_event is not None
    assert lc.stop_event is not None


def test_tc11_correlate_positional_fallback():
    """When no tool_use_id in start/stop events, falls back to positional matching."""
    events = [
        _assistant_agent_event("tu-1", "Explore", "Desc", "Prompt"),
        _ev("system", {"type": "system", "subtype": "SubagentStart", "agent_name": "explore-agent"}),
        _ev(
            "system",
            {"type": "system", "subtype": "SubagentStop", "agent_name": "explore-agent", "outcome": "error"},
        ),
    ]
    result = correlate_subagent_lifecycle(events)
    assert len(result) == 1
    lc = result[0]
    assert lc.agent_name == "explore-agent"
    assert lc.outcome == "error"


def test_tc12_correlate_outcome_from_stop_event():
    tid = "tu-abc"
    events = [
        _assistant_agent_event(tid, "Plan", "Planning task", "Plan this"),
        _ev(
            "system",
            {
                "type": "system",
                "subtype": "SubagentStop",
                "tool_use_id": tid,
                "outcome": "error",
            },
        ),
    ]
    result = correlate_subagent_lifecycle(events)
    assert len(result) == 1
    assert result[0].outcome == "error"


def test_tc10_correlate_no_start_stop_events():
    """Spawns without matching start/stop produce lifecycle records with None events."""
    events = [
        _assistant_agent_event("tu-only", "Explore", "Solo agent", "Do stuff"),
    ]
    result = correlate_subagent_lifecycle(events)
    assert len(result) == 1
    assert result[0].start_event is None
    assert result[0].stop_event is None
    assert result[0].outcome == "unknown"
