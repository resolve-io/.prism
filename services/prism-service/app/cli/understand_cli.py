"""`prism understand bootstrap | drain | status` (T11).

Invoke as: `python -m app.cli.understand_cli <subcommand> [...]`.

This is the canonical "use the user's Claude Code subscription to do
the work" path. INV-1: every analyzer invocation goes through
`app.inference.claude_cli.invoke` (env-strip enforced).

The CLI talks to the MCP service over plain HTTP — it does NOT
import the engine directly. This keeps the contract observable
(every action is also reproducible via the MCP tools) and lets the
CLI run against a remote service if needed.

Three subcommands:

* `status [--project NAME]` — pretty-print understand_status.
* `drain [--project NAME] --budget-usd N` — pop pending jobs and
  execute them (claude -p) one at a time.
* `bootstrap [--project NAME] --budget-usd N` — refresh first, then
  drain. 3-second pause-to-cancel banner before any work runs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from dataclasses import dataclass
from typing import Optional


# Rough conversion factor for the "this may cost ~$X" banner. The
# real spend is metered by the user's subscription bucket; this is
# only an order-of-magnitude estimate for the warning text.
_USD_PER_KTOKEN_OUTPUT = 0.015  # ~$15 per million output tokens


@dataclass
class CliConfig:
    project: str
    mcp_url: str = "http://localhost:7777/mcp"
    plugin_dir: str = ""


class McpClient:
    """Tiny synchronous JSON-RPC client over HTTP for the PRISM MCP."""

    def __init__(self, base: str, project: str, timeout: float = 30.0) -> None:
        self._url = f"{base.rstrip('/')}/?project={project}&tool_profile=interactive"
        self._timeout = timeout

    def call(self, tool: str, args: dict) -> dict:
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }).encode()
        req = urllib.request.Request(
            self._url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            }, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            raw = resp.read().decode()
        return _unwrap(raw)


def _unwrap(raw: str) -> dict:
    """Parse the JSON-RPC + optional SSE envelope; return the inner data dict."""
    payload_text = raw
    if "text/event-stream" in raw[:200] or raw.startswith("event:"):
        for line in raw.splitlines():
            if line.startswith("data: "):
                payload_text = line[6:]
                break
    body = json.loads(payload_text)
    content = (body.get("result") or {}).get("content") or []
    inner = content[0].get("text", "{}") if content else "{}"
    return json.loads(inner)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prism understand",
        description="Drive the PRISM Understand-Anything analyzers.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default="prism",
                        help="Project id (default: prism)")
    common.add_argument("--mcp-url", default="http://localhost:7777/mcp",
                        help="PRISM service MCP base URL")

    s_status = sub.add_parser("status", parents=[common],
                              help="Show queue + cache state")

    s_drain = sub.add_parser("drain", parents=[common],
                             help="Drain pending jobs (foreground)")
    s_drain.add_argument("--budget-usd", type=float, required=True,
                         help="Hard cap on spend (required)")
    s_drain.add_argument("--max-jobs", type=int, default=10)
    s_drain.add_argument("--plugin-dir", default="",
                         help="--plugin-dir passed to claude -p")
    s_drain.add_argument("--source-dir", default="",
                         help="Host path to project source/ "
                              "(auto-discovers data-v51/projects/<name>/source if absent)")

    s_boot = sub.add_parser("bootstrap", parents=[common],
                            help="Refresh then drain (cold-start, foreground)")
    s_boot.add_argument("--budget-usd", type=float, required=True)
    s_boot.add_argument("--max-jobs", type=int, default=10)
    s_boot.add_argument("--plugin-dir", default="")
    s_boot.add_argument("--source-dir", default="")
    s_boot.add_argument("--no-pause", action="store_true",
                        help="Skip the 3-second cancel pause (tests)")

    return p


def _print_status(env: dict, *, out=sys.stdout) -> None:
    data = env.get("data") or env  # tolerate both envelope and raw
    out.write("PRISM Understand-Anything — status\n")
    out.write(f"  project              : {data.get('project')}\n")
    out.write(f"  tracked_ref          : {data.get('tracked_ref')}\n")
    out.write(f"  current_sha          : {data.get('current_sha') or '—'}\n")
    out.write(f"  last_analyzed_sha    : {data.get('last_analyzed_sha') or '—'}\n")
    out.write(f"  cached_shas          : {len(data.get('cached_shas') or [])}\n")
    q = data.get("queue") or {}
    out.write(
        f"  queue                : pending={q.get('pending', 0)}  "
        f"in_progress={q.get('in_progress', 0)}  "
        f"completed={q.get('completed', 0)}  "
        f"failed={q.get('failed', 0)}\n"
    )
    out.write(
        f"  in_session_drain     : "
        f"{'enabled' if data.get('in_session_drain_enabled') else 'disabled'}\n"
    )


def _budget_banner(budget_usd: float, *, out=sys.stdout) -> None:
    est_ktokens = int(budget_usd / _USD_PER_KTOKEN_OUTPUT) if budget_usd > 0 else 0
    out.write(
        f"This run is capped at ${budget_usd:.2f} (~{est_ktokens}k output "
        f"tokens) from your Claude Code subscription bucket.\n"
    )


def cmd_status(args, *, client: Optional[McpClient] = None, out=sys.stdout) -> int:
    client = client or McpClient(args.mcp_url, args.project)
    env = client.call("understand_status", {"project": args.project})
    _print_status(env, out=out)
    return 0


def cmd_drain(args, *, client: Optional[McpClient] = None,
              executor=None, out=sys.stdout) -> int:
    if args.budget_usd <= 0:
        out.write("refused: --budget-usd must be > 0\n")
        return 2
    client = client or McpClient(args.mcp_url, args.project)
    _budget_banner(args.budget_usd, out=out)
    return _drain_loop(client, args, executor=executor, out=out)


def cmd_bootstrap(args, *, client: Optional[McpClient] = None,
                  executor=None, out=sys.stdout) -> int:
    if args.budget_usd <= 0:
        out.write("refused: --budget-usd must be > 0\n")
        return 2
    client = client or McpClient(args.mcp_url, args.project)
    _budget_banner(args.budget_usd, out=out)
    if not getattr(args, "no_pause", False):
        out.write("Starting in 3 seconds — Ctrl-C to cancel.\n")
        out.flush()
        time.sleep(3)
    client.call("understand_refresh", {"project": args.project})
    return _drain_loop(client, args, executor=executor, out=out)


def _drain_loop(client: McpClient, args, *,
                executor=None, out=sys.stdout) -> int:
    """Pop jobs from the queue and execute them serially.

    `executor` is an injection seam for tests — a callable
    `(job: dict, args) -> dict` returning the analyzer payload. Real
    runs use `_default_executor` which shells out via claude_cli.
    """
    runner = executor or _default_executor
    total_spent_ktokens = 0
    spent_cap_ktokens = max(1, int(args.budget_usd / _USD_PER_KTOKEN_OUTPUT))
    drained = 0
    while drained < args.max_jobs:
        env = client.call("understand_drain_queue", {
            "project": args.project, "max_jobs": 1,
        })
        jobs = (env.get("data") or {}).get("jobs") or []
        if not jobs:
            out.write("queue empty — nothing more to do.\n")
            break
        job = jobs[0]
        out.write(
            f"running {job['analyzer']} @ {job['target_sha'][:10]} "
            f"(scope={job['scope_hash']}) …\n"
        )
        out.flush()
        result = runner(job, args)
        client.call("understand_store_result", {
            "project": args.project,
            "job_id": job["job_id"],
            "analyzer": job["analyzer"],
            "target_sha": job["target_sha"],
            "payload": result.get("payload"),
            "tokens_used": int(result.get("tokens_used") or 0),
            "wall_clock_s": float(result.get("wall_clock_s") or 0.0),
            "status": result.get("status") or "complete",
            "error": result.get("error") or "",
        })
        total_spent_ktokens += int(result.get("tokens_used") or 0) // 1000
        drained += 1
        if total_spent_ktokens >= spent_cap_ktokens:
            out.write(
                f"budget cap reached (~{total_spent_ktokens}k tokens); stopping.\n"
            )
            break
    return 0


def _resolve_source_dir(args, job: dict) -> Path:
    """Locate the host-side path to data/projects/<name>/source/.

    Order: explicit --source-dir, then common host volume locations.
    Falls back to cwd so the executor still runs (with reduced context)
    when no source clone is reachable.
    """
    from pathlib import Path
    if getattr(args, "source_dir", ""):
        return Path(args.source_dir).resolve()
    candidates = [
        Path.cwd() / "data" / "projects" / args.project / "source",
        Path.cwd() / "data-v51" / "projects" / args.project / "source",
        Path.cwd() / "services" / "prism-service" / "data-v51"
            / "projects" / args.project / "source",
        Path.cwd() / "services" / "prism-service" / "data"
            / "projects" / args.project / "source",
    ]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    return Path.cwd()


def _default_executor(job: dict, args) -> dict:
    """Foreground CLI executor — delegates to the shared analyzer_runner.

    The shared module (`app.inference.analyzer_runner`) is also used by
    the server-side auto-drainer (`app.services.understand_drainer`).
    Behavior is identical; only the trigger differs.
    """
    from app.inference import analyzer_runner

    source_dir = _resolve_source_dir(args, job)
    plugin_dir = args.plugin_dir or str(source_dir)
    return analyzer_runner.run_analyzer(
        args.project,
        job["analyzer"],
        job["target_sha"],
        job.get("scope_hash") or "full",
        plugin_dir=plugin_dir,
    )


_CMD_TABLE = {
    "status": cmd_status,
    "drain": cmd_drain,
    "bootstrap": cmd_bootstrap,
}


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = _CMD_TABLE[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
