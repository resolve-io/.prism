"""Run one Understand-Anything analyzer via claude_cli.

Single shared executor used by both:
  * `app.cli.understand_cli` — the foreground `prism understand drain` path
  * `app.services.understand_drainer` — the server-side auto-drain loop

Owns the prompt loading, frontmatter strip, runtime-context block,
claude_cli.invoke call, and payload extraction. Returns a structured
dict the callers persist via `understand_artifact_store.put`.

INV-1 is enforced inside `claude_cli.invoke` — this module never
re-enables the stripped env vars.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.inference import claude_cli
from app.services import source_service as ss


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Analyzers walk the source tree (no Brain MCP available in the
# server-side drain context) so they need more turns than the harness
# default. Budget caps still bound aggregate spend.
DEFAULT_MAX_TURNS = 35


def _strip_frontmatter(text: str) -> str:
    """Drop leading YAML frontmatter before sending to claude.

    Claude's CLI arg parser treats a prompt that starts with `---` as
    an unknown flag and exits 1. The frontmatter is metadata for our
    tooling — not instructions for the model.
    """
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            return text[end + len("\n---\n"):].lstrip()
    return text


def _strip_code_fence(text: str, kind: str) -> str:
    pattern = rf"```\s*{kind}?\s*\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text


def _extract_payload(res: claude_cli.ClaudeCliResult, analyzer: str) -> Any:
    """Pull the analyzer's JSON or markdown payload out of stream-json events."""
    text_blocks: list[str] = []
    for evt in res.parsed_events:
        msg = evt.get("message") or evt
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_blocks.append(block.get("text", ""))
    final = (text_blocks[-1] if text_blocks else "").strip()
    if analyzer == "onboarding_writer":
        return _strip_code_fence(final, "markdown")
    cleaned = _strip_code_fence(final, "json")
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw": final, "error": "not_valid_json"}


def _classify(res: claude_cli.ClaudeCliResult, payload: Any) -> str:
    """complete | partial | failed — same rules as the legacy CLI executor."""
    parseable = (
        isinstance(payload, str) and payload.startswith("#")
    ) or (
        isinstance(payload, dict) and "error" not in payload
        and ("schema" in payload or "steps" in payload or "layers" in payload
             or "domains" in payload)
    )
    if res.exit_code == 0 and parseable:
        return "complete"
    return "partial" if parseable else "failed"


def run_analyzer(
    project: str,
    analyzer: str,
    target_sha: str,
    scope_hash: str = "full",
    *,
    plugin_dir: Optional[str] = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_budget_usd: float = 0.0,
) -> dict:
    """Execute one analyzer for `project` at `target_sha`.

    Returns:
        {
            "payload": <analyzer output: dict or markdown str>,
            "tokens_used": int,
            "wall_clock_s": float,
            "status": "complete" | "partial" | "failed",
            "error": str,
        }

    Raises:
        FileNotFoundError: when the `claude` CLI is not on PATH.
        claude_cli.ClaudeNotLoggedInError: when claude reports auth failure.
        FileNotFoundError: when the analyzer prompt file is missing.
    """
    prompt_path = _PROMPTS_DIR / f"{analyzer}.md"
    template = _strip_frontmatter(prompt_path.read_text(encoding="utf-8"))

    source_dir = ss.source_dir_for(project)
    runtime = (
        f"\n\n## Runtime context\n"
        f"- project: {project}\n"
        f"- target_sha: {target_sha}\n"
        f"- scope_hash: {scope_hash}\n"
        f"- source_dir: your cwd — the source tree at the pinned SHA "
        f"is already checked out here; use Read/Glob/Grep to explore.\n"
        f"- output: emit the schema's JSON (or markdown for "
        f"onboarding_writer) as your final assistant message; do NOT "
        f"write files.\n"
    )
    res = claude_cli.invoke(
        template + runtime,
        source_dir,
        plugin_dir=plugin_dir or str(source_dir),
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        parse_events=True,
        project=project,
        purpose=f"{analyzer}@{(target_sha or '')[:10]}",
    )
    payload = _extract_payload(res, analyzer)
    status = _classify(res, payload)
    return {
        "payload": payload,
        "tokens_used": res.usage.get("output_tokens", 0)
                       + res.usage.get("input_tokens", 0),
        "wall_clock_s": 0.0,
        "status": status,
        "error": "" if status != "failed" else f"exit={res.exit_code}",
    }
