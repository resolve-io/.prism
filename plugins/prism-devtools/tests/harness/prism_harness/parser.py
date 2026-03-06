"""JSONL stream-json output parser.

Extracts structured data from claude --output-format stream-json output.
Each line is a JSON object (event) with a 'type' field.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HarnessEvent:
    type: str
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
