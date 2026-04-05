"""Workflow service — reads/writes PRISM workflow state from YAML frontmatter files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from app.models.workflow import WORKFLOW_STEPS, WorkflowState


# Regex for YAML frontmatter delimited by ---
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Simple key: value parser (handles booleans, ints, strings, and lists)
_YAML_LINE_RE = re.compile(r"^(\w[\w_]*):\s*(.*)$")


def _parse_simple_yaml(text: str) -> dict:
    """Parse a flat YAML block without requiring pyyaml.

    Handles scalars, booleans, integers, and inline JSON-style lists.
    """
    result: dict = {}
    for line in text.splitlines():
        line = line.strip()
        m = _YAML_LINE_RE.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()

        # Booleans
        if val.lower() in ("true", "yes"):
            result[key] = True
        elif val.lower() in ("false", "no"):
            result[key] = False
        # Integers
        elif val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
            result[key] = int(val)
        # Quoted strings
        elif (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            result[key] = val[1:-1]
        # Inline list [...] — parse as JSON
        elif val.startswith("["):
            import json
            try:
                result[key] = json.loads(val)
            except Exception:
                result[key] = val
        # Empty
        elif val == "":
            result[key] = ""
        else:
            result[key] = val

    return result


def _dump_simple_yaml(data: dict) -> str:
    """Render a flat dict as YAML-ish frontmatter content."""
    import json

    lines: list[str] = []
    for key, val in data.items():
        if isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        elif isinstance(val, list):
            lines.append(f"{key}: {json.dumps(val)}")
        else:
            lines.append(f"{key}: {val}")
    return "\n".join(lines)


class WorkflowService:
    """Manages workflow state persisted as YAML frontmatter in markdown files."""

    def __init__(self, workflow_dir: str) -> None:
        self._dir = Path(workflow_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def _state_file(self) -> Path:
        return self._dir / "state.md"

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_state(self) -> Optional[WorkflowState]:
        """Read current workflow state from the state file."""
        if not self._state_file.exists():
            return None

        text = self._state_file.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            return None

        data = _parse_simple_yaml(m.group(1))
        return WorkflowState(
            active=data.get("active", False),
            workflow=str(data.get("workflow", "")),
            current_step=str(data.get("current_step", "")),
            current_step_index=int(data.get("current_step_index", 0)),
            total_steps=int(data.get("total_steps", len(WORKFLOW_STEPS))),
            story_file=str(data.get("story_file", "")),
            paused_for_manual=data.get("paused_for_manual", False),
            session_id=str(data.get("session_id", "")),
            model=str(data.get("model", "")),
            total_tokens=int(data.get("total_tokens", 0)),
            step_history=data.get("step_history", []),
        )

    def _write_state(self, state: WorkflowState) -> None:
        """Persist workflow state to the frontmatter file."""
        import json

        data = {
            "active": state.active,
            "workflow": state.workflow,
            "current_step": state.current_step,
            "current_step_index": state.current_step_index,
            "total_steps": state.total_steps,
            "story_file": state.story_file,
            "paused_for_manual": state.paused_for_manual,
            "session_id": state.session_id,
            "model": state.model,
            "total_tokens": state.total_tokens,
            "step_history": state.step_history,
        }

        body = ""
        if self._state_file.exists():
            text = self._state_file.read_text(encoding="utf-8")
            m = _FRONTMATTER_RE.match(text)
            if m:
                body = text[m.end():]

        content = f"---\n{_dump_simple_yaml(data)}\n---\n{body}"
        self._state_file.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Advance
    # ------------------------------------------------------------------

    def advance(
        self,
        validation: Optional[str] = None,
        gate_action: Optional[str] = None,
    ) -> dict:
        """Advance the workflow to the next step.

        Args:
            validation: Validation result for current step (pass/fail).
            gate_action: Action for gate steps ('approve' or 'reject').

        Returns:
            dict with new_step, success, and message.
        """
        state = self.get_state()
        if state is None or not state.active:
            return {
                "new_step": "",
                "success": False,
                "message": "No active workflow.",
            }

        idx = state.current_step_index
        if idx >= len(WORKFLOW_STEPS) - 1:
            state.active = False
            self._write_state(state)
            return {
                "new_step": "",
                "success": True,
                "message": "Workflow complete.",
            }

        current = WORKFLOW_STEPS[idx]

        # Gate steps require explicit approval
        if current["type"] == "gate":
            if gate_action not in ("approve", "reject"):
                return {
                    "new_step": current["id"],
                    "success": False,
                    "message": f"Gate '{current['id']}' requires gate_action='approve' or 'reject'.",
                }
            if gate_action == "reject":
                # Reject loops back — find last agent step before this gate
                prev_idx = idx - 1
                while prev_idx >= 0 and WORKFLOW_STEPS[prev_idx]["type"] != "agent":
                    prev_idx -= 1
                prev_idx = max(prev_idx, 0)
                prev_step = WORKFLOW_STEPS[prev_idx]
                state.current_step = prev_step["id"]
                state.current_step_index = prev_idx
                state.step_history.append(
                    {"step": current["id"], "action": "rejected"}
                )
                self._write_state(state)
                return {
                    "new_step": prev_step["id"],
                    "success": True,
                    "message": f"Gate rejected. Returning to '{prev_step['id']}'.",
                }

        # Advance to next step
        next_idx = idx + 1
        next_step = WORKFLOW_STEPS[next_idx]
        state.current_step = next_step["id"]
        state.current_step_index = next_idx
        state.paused_for_manual = next_step["type"] == "gate"
        state.step_history.append(
            {"step": current["id"], "action": "completed", "validation": validation}
        )
        self._write_state(state)

        return {
            "new_step": next_step["id"],
            "success": True,
            "message": f"Advanced to '{next_step['id']}'.",
        }

    # ------------------------------------------------------------------
    # Step listing
    # ------------------------------------------------------------------

    def get_steps(self) -> list[dict]:
        """Return WORKFLOW_STEPS annotated with current/completed status."""
        state = self.get_state()
        current_idx = state.current_step_index if state and state.active else -1
        completed_ids = set()
        if state:
            for entry in state.step_history:
                if entry.get("action") == "completed":
                    completed_ids.add(entry.get("step"))

        result: list[dict] = []
        for i, step in enumerate(WORKFLOW_STEPS):
            status = "pending"
            if step["id"] in completed_ids:
                status = "completed"
            if i == current_idx:
                status = "current"
            result.append({**step, "status": status})
        return result
