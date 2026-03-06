"""Claude headless session runner.

Invokes `claude -p` with --output-format stream-json and captures output
to a temporary JSONL file. Strips CLAUDECODE from env to prevent nested
session errors (per harness-run-claude-headless pattern).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


def run_claude(
    prompt: str,
    work_dir: Path | str,
    plugin_dir: Path | str,
    *,
    model: str = "sonnet",
    max_budget_usd: float = 0.50,
    max_turns: int = 3,
) -> tuple[Path, int]:
    """Invoke `claude -p` headless and capture stream-json output to a temp file.

    Args:
        prompt: The prompt to pass to claude -p.
        work_dir: Working directory for the claude invocation.
        plugin_dir: Path to the prism-devtools plugin (passed as --plugin-dir).
        model: Claude model shorthand (default: 'sonnet').
        max_budget_usd: Budget cap in USD (default: 0.50).
        max_turns: Maximum conversation turns (default: 3).

    Returns:
        (output_path, exit_code) — output_path is a temp .jsonl file with
        the full stream-json output. Caller is responsible for cleanup.
    """
    tmp = tempfile.NamedTemporaryFile(
        prefix="claude-harness-", suffix=".jsonl", delete=False
    )
    tmp.close()
    out_path = Path(tmp.name)

    cmd = [
        "claude",
        "-p", prompt,
        "--plugin-dir", str(plugin_dir),
        "--output-format", "stream-json",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--model", model,
        "--max-budget-usd", str(max_budget_usd),
        "--max-turns", str(max_turns),
    ]

    # Strip CLAUDECODE to prevent nested session errors
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    with open(out_path, "w") as fh:
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            env=env,
            stdout=fh,
            stderr=subprocess.DEVNULL,
        )

    return out_path, result.returncode
