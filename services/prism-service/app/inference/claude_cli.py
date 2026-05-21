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


def _build_cmd(
    prompt: str,
    plugin_dir: Path | str,
    model: str,
    max_budget_usd: float,
    max_turns: int,
) -> list[str]:
    cmd = [
        "claude",
        "-p", prompt,
        "--plugin-dir", str(plugin_dir),
        "--output-format", "stream-json",
        "--verbose",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--max-turns", str(max_turns),
    ]
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
    "unauthenticated",
)


def _looks_like_not_logged_in(stderr_text: str, exit_code: int) -> bool:
    if exit_code == 0 or not stderr_text:
        return False
    lower = stderr_text.lower()
    return any(marker in lower for marker in _AUTH_FAIL_MARKERS)


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
) -> ClaudeCliResult:
    """Run `claude -p` headless and capture stream-json output.

    Raises:
        ClaudeNotLoggedInError: when the CLI reports auth failure.
            Remediation: run `claude login`.
    """
    tmp = tempfile.NamedTemporaryFile(
        prefix="prism-claude-", suffix=".jsonl", delete=False
    )
    tmp.close()
    out_path = Path(tmp.name)

    cmd = _build_cmd(prompt, plugin_dir, model, max_budget_usd, max_turns)
    env = _strip_env()

    with open(out_path, "w", encoding="utf-8") as fh:
        result = subprocess.run(
            cmd, cwd=str(work_dir), env=env,
            stdout=fh, stderr=subprocess.PIPE,
        )

    stderr_text = (result.stderr or b"").decode("utf-8", errors="replace")
    if _looks_like_not_logged_in(stderr_text, result.returncode):
        raise ClaudeNotLoggedInError(stderr_text)

    parsed_events, usage = ([], {"input_tokens": 0, "output_tokens": 0})
    if parse_events:
        parsed_events, usage = _parse_jsonl(out_path)

    return ClaudeCliResult(
        output_path=out_path, exit_code=result.returncode,
        parsed_events=parsed_events, usage=usage,
    )


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
