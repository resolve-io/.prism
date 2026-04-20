"""Autonomous experiment driver for PRISM Brain improvements.

Runs the full experiment chain end-to-end without operator intervention:
  1. Waits for any in-flight LongMemEval run to finish.
  2. For each experiment, restarts the bench service with new env vars,
     runs a stratified smoke, and promotes to full if the smoke clears
     baseline + NOISE_FLOOR.
  3. Appends each outcome to EXPERIMENTS.md.
  4. Writes a final summary JSON.

Usage (from E:\\.prism\\benchmarks):
    .venv/Scripts/python run_experiments.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
COMPOSE_FILE = REPO_ROOT / "services" / "bench-service" / "docker-compose.yml"
RESULTS_DIR = BENCH_DIR / "results" / "longmemeval"
EXPERIMENTS_MD = BENCH_DIR / "results" / "EXPERIMENTS.md"
RUNNER = BENCH_DIR / "longmemeval" / "run.py"
PYTHON = BENCH_DIR / ".venv" / "Scripts" / "python.exe"

BASELINE_R5 = 0.524                 # from baseline-potion full run
NOISE_FLOOR = 0.05                  # smoke must exceed baseline by this to run full
SMOKE_N = 50
WORKERS = 6
MCP_URL = "http://localhost:18081/mcp/"

# Experiment queue. nomic-code removed: its torch.compile cache corrupted the
# overlay2 fs and took Docker Desktop out. Replaced with jina-code (known good
# via sentence-transformers, no torch.compile JIT path).
EXPERIMENTS = [
    # (tag, env_vars)
    ("jina-code",          {"PRISM_EMBEDDER": "jina-code",  "PRISM_SEARCH_MODE": "hybrid"}),
    ("bge-small",          {"PRISM_EMBEDDER": "bge-small",  "PRISM_SEARCH_MODE": "hybrid"}),
    ("minilm-vector-only", {"PRISM_EMBEDDER": "minilm",     "PRISM_SEARCH_MODE": "vector"}),
]


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def append_experiments_md(row: dict) -> None:
    """Append a single markdown row + log entry to EXPERIMENTS.md."""
    n = row["n"]
    tag = row["tag"]
    change = row["change"]
    smoke = f"{row['smoke']:.3f}" if row.get("smoke") is not None else "—"
    full = f"**{row['full']:.3f}**" if row.get("full") is not None else "—"
    delta = row.get("delta", "—")
    delta_str = f"{delta:+.3f}" if isinstance(delta, float) else "—"
    kept = row.get("kept", "—")
    notes = row.get("notes", "")
    table_row = f"| {n} | `{tag}` | {change} | {smoke} | {full} | {delta_str} | {kept} | {notes} |\n"

    md = EXPERIMENTS_MD.read_text(encoding="utf-8")
    # Insert before the "## Log entries" header
    md = md.replace("## Log entries", table_row + "\n## Log entries", 1)

    # Also append a dated log entry
    date = time.strftime("%Y-%m-%d")
    entry = f"\n### {date} — {tag}\n- {change}\n- Smoke R@5 = {smoke}, Full R@5 = {full} (Δ {delta_str})\n- {notes}\n"
    md = md.rstrip() + entry + "\n<!-- Append new entries below; keep human-readable and dated. -->\n"
    md = md.replace("<!-- Append new entries below; keep human-readable and dated. -->\n<!-- Append new entries below; keep human-readable and dated. -->", "<!-- Append new entries below; keep human-readable and dated. -->")
    EXPERIMENTS_MD.write_text(md, encoding="utf-8")


def compose_down() -> None:
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "down"],
                   check=False, capture_output=True)


def compose_up(env_overrides: dict[str, str]) -> None:
    env = os.environ.copy()
    env.update(env_overrides)
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d"],
                   env=env, check=True, capture_output=True)


def wait_for_mcp(timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                f"{MCP_URL}?project=probe",
                data=json.dumps({"jsonrpc": "2.0", "id": 1,
                                 "method": "tools/call",
                                 "params": {"name": "project_list", "arguments": {}}}).encode(),
                headers={"Content-Type": "application/json",
                         "Accept": "application/json, text/event-stream"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("MCP service did not become ready")


def warm_model(project: str) -> None:
    """Trigger model load via a dummy index+search so the first benchmark
    call doesn't eat the download latency."""
    u = f"{MCP_URL}?project={project}"
    for tool, args in [
        ("project_create", {"project_id": project}),
        ("brain_index_doc", {"path": "warm/a", "content": "warm up the embedder",
                             "domain": "warm"}),
        ("brain_search", {"query": "warm", "limit": 1, "domain": "warm"}),
    ]:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": tool, "arguments": args}}
        req = urllib.request.Request(
            u, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Accept": "application/json, text/event-stream"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=600).read()
        except Exception as e:
            log(f"warmup step {tool} failed: {e!r} (continuing)")


def run_benchmark(tag: str, stratify: int | None) -> float | None:
    """Run LongMemEval and return R@5, or None on failure."""
    project = f"bench-lme-{tag}-{'smoke' if stratify else 'full'}"
    out = RESULTS_DIR / f"{tag}_{'smoke' if stratify else 'full'}.json"
    args = [str(PYTHON), str(RUNNER),
            "--project", project,
            "--workers", str(WORKERS),
            "--tag", tag + ("-smoke" if stratify else "-full"),
            "--output", str(out)]
    if stratify:
        args += ["--stratify", str(stratify)]
    log(f"running {tag} ({'smoke' if stratify else 'full'}, project={project})")
    t0 = time.time()
    proc = subprocess.run(args, cwd=str(BENCH_DIR))
    elapsed = time.time() - t0
    if proc.returncode != 0:
        log(f"  FAILED (exit {proc.returncode})")
        return None
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        r5 = float(data["recall@5"])
        log(f"  R@5 = {r5:.4f}  ({data['hits@5']}/{data['total_scored']})  "
            f"elapsed={elapsed:.0f}s")
        return r5
    except Exception as e:
        log(f"  result parse failed: {e!r}")
        return None


def wait_for_other_python() -> None:
    """Poll until no *other* python processes from benchmarks/ are running.
    Distinguishes the driver (us) from benchmark runners by command args:
    benchmark runners have 'longmemeval/run.py' in argv."""
    log("waiting for any in-flight benchmark to finish...")
    while True:
        try:
            out = subprocess.run(["ps", "-ef"], capture_output=True, text=True).stdout
        except FileNotFoundError:
            return
        runners = [ln for ln in out.splitlines()
                   if "longmemeval/run.py" in ln or "longmemeval\\run.py" in ln]
        if not runners:
            log("  no in-flight run detected")
            return
        time.sleep(30)


def record_minilm_full() -> float | None:
    """Read minilm-full result and append to EXPERIMENTS.md (once)."""
    path = RESULTS_DIR / "minilm_full.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        r5 = float(data["recall@5"])
    except Exception as e:
        log(f"cannot read minilm_full.json: {e!r}")
        return None

    # Skip if already recorded
    md = EXPERIMENTS_MD.read_text(encoding="utf-8")
    if "`minilm-full`" in md:
        log(f"minilm-full already in EXPERIMENTS.md (R@5={r5:.4f}), skipping record")
        return r5

    by_type = {k: f"{v['r@5']:.3f}" for k, v in data.get("by_type", {}).items()}
    notes = ", ".join(f"{k}:{v}" for k, v in sorted(by_type.items()))
    append_experiments_md({
        "n": 1,
        "tag": "minilm-full",
        "change": "swap embedder: potion → all-MiniLM-L6-v2 (full 500 Q)",
        "smoke": 0.800,
        "full": r5,
        "delta": r5 - BASELINE_R5,
        "kept": "✅" if r5 > BASELINE_R5 + NOISE_FLOOR else "↔️",
        "notes": notes,
    })
    return r5


def run_experiment(n: int, tag: str, env: dict[str, str]) -> dict:
    """Run one experiment: restart container, smoke, promote to full if good."""
    log(f"=== experiment {n}: {tag} — env={env} ===")
    compose_down()
    compose_up(env)
    wait_for_mcp()
    warm_model(f"bench-lme-{tag}-warm")

    smoke = run_benchmark(tag, stratify=SMOKE_N)
    full = None
    kept = "❌"
    if smoke is None:
        notes = "smoke failed"
    elif smoke > BASELINE_R5 + NOISE_FLOOR:
        log(f"  smoke beat baseline+{NOISE_FLOOR:.2f}; promoting to full")
        full = run_benchmark(tag, stratify=None)
        if full is not None and full > BASELINE_R5 + NOISE_FLOOR:
            kept = "✅"
        notes = f"env={env}"
    else:
        log(f"  smoke did not beat baseline+{NOISE_FLOOR:.2f}; skip full")
        notes = f"env={env}; smoke below promotion threshold"

    delta = (full - BASELINE_R5) if full is not None else (
        (smoke - BASELINE_R5) if smoke is not None else None)

    row = {
        "n": n,
        "tag": tag,
        "change": f"{env.get('PRISM_EMBEDDER','?')}, search={env.get('PRISM_SEARCH_MODE','?')}",
        "smoke": smoke,
        "full": full,
        "delta": delta,
        "kept": kept,
        "notes": notes,
    }
    append_experiments_md(row)
    return row


def main() -> int:
    wait_for_other_python()

    results: list[dict] = []

    r = record_minilm_full()
    if r is not None:
        log(f"minilm-full recorded: R@5={r:.4f}")
        results.append({"tag": "minilm-full", "full": r, "delta": r - BASELINE_R5})

    for n, (tag, env) in enumerate(EXPERIMENTS, start=2):
        try:
            row = run_experiment(n, tag, env)
            results.append(row)
        except Exception as e:
            log(f"experiment {n} ({tag}) crashed: {e!r}")

    summary = {
        "baseline_r5": BASELINE_R5,
        "noise_floor": NOISE_FLOOR,
        "experiments": results,
    }
    (BENCH_DIR / "results" / "chain_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    log("=== all experiments complete ===")
    log(f"summary -> {BENCH_DIR / 'results' / 'chain_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
