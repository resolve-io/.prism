"""Headless `claude -p` subprocess primitive for the PRISM service.

Promoted from the harness primitive at
`plugins/prism-devtools/tests/harness/prism_harness/claude_session.py:
run_claude` so the service can drive Understand-Anything analyzers
(T8) and the `prism understand` CLI (T11) with the same
env-stripping, no-API-key invocation contract.

INV-1 from story 5.1: `ANTHROPIC_API_KEY`, `CLAUDECODE`, and
`CLAUDE_CODE_ENTRYPOINT` are stripped from the child env. This is
the single enforcement point.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


_STRIP_VARS = frozenset({
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "ANTHROPIC_API_KEY",
})


class ClaudeNotLoggedInError(RuntimeError):
    """Raised when the Claude CLI reports an unauthenticated state.

    Remediation: run `claude login` in the same shell where the
    service is started.
    """

    def __init__(self, stderr_excerpt: str = "") -> None:
        msg = (
            "claude CLI is not logged in. Run `claude login` and retry."
        )
        if stderr_excerpt:
            msg += f"\nstderr excerpt: {stderr_excerpt[:200]}"
        super().__init__(msg)
        self.stderr_excerpt = stderr_excerpt


@dataclass
class ClaudeCliResult:
    """Structured result from a `claude -p` invocation."""

    output_path: Path
    exit_code: int
    parsed_events: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


# Default tool whitelist for batch / background invocations
# (Understand-Anything analyzers, drift sync, etc.). Strictly
# read-only: the model walks the source tree and emits structured
# output, never touches disk or shells out. Interactive call sites
# (e.g. future "ask memory" Q&A) pass their own broader list.
READ_ONLY_TOOLS = ("Read", "Glob", "Grep")


def _build_cmd(
    prompt: str,
    plugin_dir: Path | str,
    model: str,
    max_budget_usd: float,
    max_turns: int,
    allowed_tools: tuple[str, ...] = READ_ONLY_TOOLS,
) -> list[str]:
    """Build the `claude -p` invocation.

    Permission model — v5.1.7 onward:
      Each call site chooses its own tool scope via `allowed_tools`.
      Batch analyzers stay on the READ_ONLY_TOOLS default; an
      interactive "ask memory" path can pass e.g.
      ("Read", "Glob", "Grep", "Bash") to let claude shell out and
      query MCP tools. We never use --dangerously-skip-permissions —
      it bypasses every guard, trips Claude's root/sudo safety check,
      and grants tool access we don't actually need.

      Pass `allowed_tools=()` to omit --allowedTools entirely and use
      Claude's interactive default permission model (useful if a call
      site wants permission prompts to fall through to a wrapping UI).
    """
    cmd = [
        "claude",
        "-p", prompt,
        "--plugin-dir", str(plugin_dir),
        "--output-format", "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--max-turns", str(max_turns),
    ]
    if allowed_tools:
        cmd += ["--allowedTools", *allowed_tools]
    if model:
        cmd += ["--model", model]
    if max_budget_usd > 0:
        cmd += ["--max-budget-usd", str(max_budget_usd)]
    return cmd


def _strip_env(base_env: dict | None = None) -> dict:
    """Return a copy of base_env (or os.environ) with INV-1 vars removed."""
    src = os.environ if base_env is None else base_env
    return {k: v for k, v in src.items() if k not in _STRIP_VARS}


_AUTH_FAIL_MARKERS = (
    "not logged in",
    "claude login",
    "please log in",
    "please run /login",
    "unauthenticated",
)


def _looks_like_not_logged_in(
    stderr_text: str, exit_code: int, final_text: str = "",
) -> bool:
    """Return True when either stderr or the model's final assistant
    text indicates auth failure. Newer claude versions surface
    'Not logged in · Please run /login' through stdout as a normal
    assistant message instead of stderr — final_text catches that case.
    """
    if exit_code == 0:
        return False
    for source in (stderr_text, final_text):
        if not source:
            continue
        lower = source.lower()
        if any(marker in lower for marker in _AUTH_FAIL_MARKERS):
            return True
    return False


def _final_assistant_text(parsed_events: list[dict]) -> str:
    """Pull the last assistant text block out of parsed stream events."""
    text_blocks: list[str] = []
    for evt in parsed_events:
        msg = evt.get("message") or evt
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_blocks.append(block.get("text", ""))
    return (text_blocks[-1] if text_blocks else "").strip()


def _parse_jsonl(out_path: Path) -> tuple[list[dict], dict]:
    parsed: list[dict] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    try:
        for line in out_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            parsed.append(evt)
            u = evt.get("usage") or (evt.get("message") or {}).get("usage")
            if isinstance(u, dict):
                usage["input_tokens"] += int(u.get("input_tokens") or 0)
                usage["output_tokens"] += int(u.get("output_tokens") or 0)
    except OSError:
        pass
    return parsed, usage


def invoke(
    prompt: str,
    work_dir: Path | str,
    plugin_dir: Path | str,
    *,
    model: str = "",
    max_budget_usd: float = 0.0,
    max_turns: int = 3,
    parse_events: bool = True,
    project: str = "",
    purpose: str = "",
    allowed_tools: tuple[str, ...] = READ_ONLY_TOOLS,
) -> ClaudeCliResult:
    """Run `claude -p` headless and capture stream-json output.

    The captured output is moved to /data/claude_runs/<run_id>.jsonl and
    a manifest line is appended so operators can verify executions via
    /api/claude-runs. `project` and `purpose` are stored on the manifest
    line — pass them when you have them (e.g. analyzer_runner does).

    Raises:
        ClaudeNotLoggedInError: when the CLI reports auth failure.
            Remediation: run `docker exec -it prism-service claude login`.
    """
    # Try to land the stream-json directly in the persistent run log
    # dir; fall back to a tempfile if that volume isn't writable (e.g.
    # in unit tests with no /data mount).
    out_path: Path
    run_id: str = ""
    try:
        from app.services import claude_run_log
        run_id, out_path = claude_run_log.new_run()
    except Exception:
        tmp = tempfile.NamedTemporaryFile(
            prefix="prism-claude-", suffix=".jsonl", delete=False,
        )
        tmp.close()
        out_path = Path(tmp.name)

    cmd = _build_cmd(
        prompt, plugin_dir, model, max_budget_usd, max_turns,
        allowed_tools=allowed_tools,
    )
    env = _strip_env()

    ts_start = time.time()
    with open(out_path, "w", encoding="utf-8") as fh:
        result = subprocess.run(
            cmd, cwd=str(work_dir), env=env,
            stdout=fh, stderr=subprocess.PIPE,
        )
    ts_end = time.time()

    stderr_text = (result.stderr or b"").decode("utf-8", errors="replace")

    # Parse the stream first so we can also inspect the assistant's final
    # text — newer claude surfaces "Not logged in · Please run /login"
    # there instead of stderr, and we need to catch both.
    parsed_events, usage = _parse_jsonl(out_path)
    final_text = _final_assistant_text(parsed_events)

    if _looks_like_not_logged_in(stderr_text, result.returncode, final_text):
        # Still record the failed-auth attempt so operators can see it
        # from the UI without trawling docker logs.
        _safe_record_run(
            run_id=run_id, stream_path=out_path,
            ts_start=ts_start, ts_end=ts_end,
            project=project, purpose=purpose,
            exit_code=result.returncode, usage=usage,
            stderr_text=stderr_text or final_text,
        )
        raise ClaudeNotLoggedInError(stderr_text or final_text)

    if not parse_events:
        parsed_events, usage = [], {"input_tokens": 0, "output_tokens": 0}

    _safe_record_run(
        run_id=run_id, stream_path=out_path,
        ts_start=ts_start, ts_end=ts_end,
        project=project, purpose=purpose,
        exit_code=result.returncode, usage=usage,
        stderr_text=stderr_text,
    )

    return ClaudeCliResult(
        output_path=out_path, exit_code=result.returncode,
        parsed_events=parsed_events, usage=usage,
    )


def _safe_record_run(**kw) -> None:
    """Append to /data/claude_runs/manifest.jsonl. Best-effort: any
    failure (no /data mount in tests, manifest unwritable, etc.) is
    swallowed so the caller sees an unaltered ClaudeCliResult."""
    if not kw.get("run_id"):
        return  # tempfile fallback — nothing to record
    try:
        from app.services import claude_run_log
        claude_run_log.record_run(**kw)
    except Exception:
        pass


def run_claude(
    prompt: str,
    work_dir: Path | str,
    plugin_dir: Path | str,
    *,
    model: str = "",
    max_budget_usd: float = 0.0,
    max_turns: int = 3,
) -> tuple[Path, int]:
    """Back-compat tuple-return API.

    Mirrors the original harness signature so the 11 harness tests
    under `plugins/prism-devtools/tests/harness/prism_harness/tests/`
    keep working unchanged. New callers should prefer `invoke()`
    which returns a structured ClaudeCliResult.
    """
    res = invoke(
        prompt, work_dir, plugin_dir,
        model=model,
        max_budget_usd=max_budget_usd,
        max_turns=max_turns,
        parse_events=False,
    )
    return res.output_path, res.exit_code
