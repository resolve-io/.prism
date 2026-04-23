#!/usr/bin/env python3
"""
PRISM SubagentStop hook — certificate enforcement and outcome recording.

Fires when a sub-agent finishes. For SFR variants:
  - Checks certificate completeness (sections ### 1. through ### 6.)
  - Blocks (exit 2) up to 2 times if fewer than 5/6 sections are present
  - Records outcome to subagent_outcomes table in scores.db

State files (written by SubagentStart hook):
  .prism/brain/subagent_variants/{safe_name} — which variant was selected (per-agent)
  .prism/brain/sfr_block_count_{agent_name}  — per-agent block counter
"""

import json
import re
import sys
from pathlib import Path


# Certificate section markers that SFR variants must complete.
_CERT_MARKERS = [
    "### 1.",
    "### 2.",
    "### 3.",
    "### 4.",
    "### 5.",
    "### 6.",
]

# Minimum sections required to pass certificate check.
_CERT_MIN_SECTIONS = 5

# Maximum times the hook will block before allowing stop.
_MAX_BLOCKS = 2


def _git_root() -> Path:
    """Find git root from cwd. Returns cwd on failure."""
    import subprocess
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return Path(r.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def _read_prompt_id(prism_dir: Path, agent_name: str) -> str:
    """Read prompt_id from per-agent variant file written by SubagentStart hook.

    Reads from '.prism/brain/subagent_variants/{safe_name}' where safe_name
    mirrors the path written by conductor._save_subagent_prompt_id().
    Returns '' if missing.
    """
    safe_name = agent_name.replace("/", "_").replace("\\", "_")
    state_file = prism_dir / "brain" / "subagent_variants" / safe_name
    try:
        return state_file.read_text(encoding="utf-8").strip()
    except (IOError, OSError):
        return ""


def _read_block_count(prism_dir: Path, agent_name: str) -> int:
    """Read per-agent block counter. Returns 0 if missing."""
    counter_file = prism_dir / "brain" / f"sfr_block_count_{agent_name}"
    try:
        return int(counter_file.read_text(encoding="utf-8").strip())
    except (IOError, OSError, ValueError):
        return 0


def _write_block_count(prism_dir: Path, agent_name: str, count: int) -> None:
    """Write per-agent block counter."""
    try:
        counter_file = prism_dir / "brain" / f"sfr_block_count_{agent_name}"
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        counter_file.write_text(str(count), encoding="utf-8")
    except (IOError, OSError):
        pass


def _cleanup_block_counter(prism_dir: Path, agent_name: str) -> None:
    """Remove per-agent block counter file."""
    try:
        counter_file = prism_dir / "brain" / f"sfr_block_count_{agent_name}"
        if counter_file.exists():
            counter_file.unlink()
    except (IOError, OSError):
        pass


def _count_cert_sections(text: str) -> list:
    """Return list of missing section markers from _CERT_MARKERS."""
    missing = []
    for marker in _CERT_MARKERS:
        if marker not in text:
            missing.append(marker)
    return missing


def _parse_recommendation(text: str) -> str:
    """Extract APPROVE/REVISE/PASS/FAIL from sub-agent output."""
    m = re.search(r'\b(APPROVE|REVISE|PASS|FAIL)\b', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return ""


def _count_evidence(text: str) -> int:
    """Count file:line citations (e.g. src/foo.py:42)."""
    return len(re.findall(r'[\w./\\]+:\d+', text))


def _record_outcome(
    prompt_id: str,
    agent_name: str,
    recommendation: str,
    evidence_count: int,
    certificate_complete: int,
    certificate_blocked: int,
    timed_out: int,
    tokens_used: int,
    duration_s: float,
) -> None:
    """Write one subagent_outcomes row via MCP. Best-effort."""
    try:
        from prism_mcp_client import call as _mcp_call
        _mcp_call("record_subagent_outcome", {
            "prompt_id": prompt_id,
            "validator": agent_name,
            "recommendation": recommendation,
            "evidence_count": evidence_count,
            "certificate_complete": certificate_complete,
            "certificate_blocked": certificate_blocked,
            "timed_out": timed_out,
            "tokens_used": tokens_used,
            "duration_s": duration_s,
        })
    except Exception:
        pass


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    agent_name = input_data.get("agent_name", "")
    last_message = input_data.get("last_assistant_message", "")
    tokens_used = int(input_data.get("tokens_used", 0) or 0)
    duration_s = float(input_data.get("duration_s", 0.0) or 0.0)

    prism_dir = _git_root() / ".prism"
    prompt_id = _read_prompt_id(prism_dir, agent_name)

    is_sfr = "/sfr" in prompt_id

    certificate_blocked = _read_block_count(prism_dir, agent_name)
    certificate_complete = 0

    if is_sfr and last_message:
        missing = _count_cert_sections(last_message)
        certificate_complete = len(_CERT_MARKERS) - len(missing)

        if len(missing) > (len(_CERT_MARKERS) - _CERT_MIN_SECTIONS):
            # Certificate incomplete
            if certificate_blocked < _MAX_BLOCKS:
                certificate_blocked += 1
                _write_block_count(prism_dir, agent_name, certificate_blocked)
                missing_labels = ", ".join(missing)
                print(
                    f"Your SFR certificate is incomplete — sections "
                    f"{missing_labels} are missing. Complete all 6 sections "
                    f"before concluding."
                )
                sys.exit(2)
            # Exceeded max blocks — allow stop with timed_out flag
            _cleanup_block_counter(prism_dir, agent_name)
            _record_outcome(
                prompt_id=prompt_id,
                agent_name=agent_name,
                recommendation=_parse_recommendation(last_message),
                evidence_count=_count_evidence(last_message),
                certificate_complete=certificate_complete,
                certificate_blocked=certificate_blocked,
                timed_out=1,
                tokens_used=tokens_used,
                duration_s=duration_s,
            )
            sys.exit(0)

    # Certificate passed (or freeform variant) — record outcome
    _cleanup_block_counter(prism_dir, agent_name)
    _record_outcome(
        prompt_id=prompt_id,
        agent_name=agent_name,
        recommendation=_parse_recommendation(last_message),
        evidence_count=_count_evidence(last_message),
        certificate_complete=certificate_complete,
        certificate_blocked=certificate_blocked,
        timed_out=0,
        tokens_used=tokens_used,
        duration_s=duration_s,
    )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
