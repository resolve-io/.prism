"""SWE-bench file-localization benchmark for PRISM Brain.

For each SWE-bench instance:
  1. Clone the repo at its `base_commit` (the state before the fix).
  2. Index every source file via the bench MCP service at port 18081.
  3. Query Brain with the issue `problem_statement`, request top-K results.
  4. Extract the set of files modified by the gold `patch`.
  5. Hit@K = did any of those files appear in the top-K retrieved?

Report R@1 / R@5 / R@10.

Runs against the isolated bench service (services/bench-service/), NOT the
real PRISM service. Each instance gets its own project slug so per-instance
indexes never bleed into each other.

Usage:
    cd benchmarks
    python -m venv .venv && .venv/Scripts/pip install -r requirements.txt
    cd ../services/bench-service && docker compose up -d --build
    cd ../../benchmarks/swebench
    python run.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

MCP_URL = "http://localhost:18081/mcp/"
BENCH_DIR = Path(__file__).resolve().parent
REPOS_DIR = BENCH_DIR.parent / "repos"
RESULTS_DIR = BENCH_DIR.parent / "results" / "swebench"

SOURCE_EXTS = {".py", ".md", ".rst", ".txt", ".yaml", ".yml",
               ".json", ".toml", ".cfg", ".ini"}
SKIP_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv",
              "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
              ".eggs", "site-packages"}
MAX_FILE_BYTES = 200_000


# ---------------------------------------------------------------------------
# MCP client (stateless HTTP POST, no session tracking)
# ---------------------------------------------------------------------------

def mcp_call(project: str, tool: str, arguments: dict[str, Any]) -> dict:
    url = f"{MCP_URL}?project={project}"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": tool, "arguments": arguments}}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        raw = r.read().decode()
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            for line in raw.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
        return json.loads(raw)


def parse_result(resp: dict) -> Any:
    if "error" in resp:
        raise RuntimeError(f"MCP error: {resp['error']}")
    content = resp.get("result", {}).get("content", [])
    if not content:
        return None
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# ---------------------------------------------------------------------------
# Repo checkout (shallow, per-commit)
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                   check=True, capture_output=True)


def ensure_commit_checkout(repo: str, commit: str) -> Path:
    """Shallow-fetch `repo` at `commit` into repos/<repo-slug>__<sha[:8]>/.
    Returns the checkout path. Cached across runs."""
    slug = repo.replace("/", "__")
    dest = REPOS_DIR / f"{slug}__{commit[:8]}"
    marker = dest / ".prism_bench_ready"
    if marker.exists():
        return dest
    dest.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q"], cwd=dest)
    _run(["git", "remote", "add", "origin", f"https://github.com/{repo}.git"],
         cwd=dest)
    # Try shallow fetch of the exact commit; fall back to full fetch if the
    # server disallows by-SHA (some older GitHub configs).
    try:
        _run(["git", "fetch", "--depth=1", "origin", commit], cwd=dest)
    except subprocess.CalledProcessError:
        _run(["git", "fetch", "origin"], cwd=dest)
    _run(["git", "checkout", "-q", commit], cwd=dest)
    marker.touch()
    return dest


# ---------------------------------------------------------------------------
# Corpus + patch extraction
# ---------------------------------------------------------------------------

def iter_source_files(root: Path) -> Iterable[tuple[str, str]]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in SOURCE_EXTS:
            continue
        rel_parts = p.relative_to(root).parts
        if any(part in SKIP_PARTS for part in rel_parts):
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size == 0 or size > MAX_FILE_BYTES:
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            continue
        yield p.relative_to(root).as_posix(), content


_PATCH_FILE_RE = re.compile(r"^(?:\+\+\+|---) [ab]/(?P<path>.+?)\s*$", re.M)


def files_from_patch(patch: str) -> set[str]:
    """Extract the set of file paths touched by a unified diff."""
    files: set[str] = set()
    for m in _PATCH_FILE_RE.finditer(patch):
        path = m.group("path").strip()
        if path and path != "/dev/null":
            files.add(path)
    return files


# ---------------------------------------------------------------------------
# Per-instance runner
# ---------------------------------------------------------------------------

def run_instance(inst: dict, k_max: int = 10, reset: bool = False) -> dict:
    iid = inst["instance_id"]
    project = f"bench-swe-{iid}".lower()
    project = re.sub(r"[^a-z0-9_-]", "-", project)[:60]

    t0 = time.perf_counter()
    checkout = ensure_commit_checkout(inst["repo"], inst["base_commit"])
    checkout_sec = time.perf_counter() - t0

    mcp_call(project, "project_create", {"project_id": project})

    # Ingest
    t1 = time.perf_counter()
    n_indexed = 0
    for rel, content in iter_source_files(checkout):
        mcp_call(project, "brain_index_doc",
                 {"path": rel, "content": content, "domain": "code"})
        n_indexed += 1
    ingest_sec = time.perf_counter() - t1

    # Build the graphify-backed code graph for this instance.
    # Cheap for a single repo at a single commit; runs tree-sitter + Leiden.
    t_g = time.perf_counter()
    try:
        mcp_call(project, "graph_rebuild", {})
    except Exception as e:
        print(f"graph_rebuild failed: {e!r}", file=sys.stderr)
    graph_sec = time.perf_counter() - t_g

    # Query
    t2 = time.perf_counter()
    query = inst["problem_statement"][:4000]  # cap; some statements are huge
    resp = mcp_call(project, "brain_search",
                    {"query": query, "limit": k_max})
    payload = parse_result(resp) or []
    if isinstance(payload, dict):
        payload = payload.get("results") or payload.get("matches") or []
    retrieved = []
    for item in payload:
        did = item.get("doc_id", "").removesuffix("::main")
        if did:
            retrieved.append(did)
    query_sec = time.perf_counter() - t2

    gold = files_from_patch(inst.get("patch", ""))
    hits = {}
    for k in (1, 5, 10):
        topk = set(retrieved[:k])
        hits[f"hit@{k}"] = bool(topk & gold) if gold else None

    return {
        "instance_id": iid,
        "repo": inst["repo"],
        "base_commit": inst["base_commit"][:12],
        "n_indexed": n_indexed,
        "gold_files": sorted(gold),
        "retrieved": retrieved,
        **hits,
        "checkout_sec": round(checkout_sec, 2),
        "ingest_sec": round(ingest_sec, 2),
        "graph_sec": round(graph_sec, 2),
        "query_sec": round(query_sec, 3),
        "total_sec": round(time.perf_counter() - t0, 2),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_dataset(name: str, split: str):
    from datasets import load_dataset as _ld  # type: ignore
    dataset_id = {
        "lite": "princeton-nlp/SWE-bench_Lite",
        "verified": "princeton-nlp/SWE-bench_Verified",
    }[name]
    return _ld(dataset_id, split=split)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["lite", "verified"], default="lite")
    ap.add_argument("--split", default="test",
                    help="'test' for lite, 'test' for verified")
    ap.add_argument("--limit", type=int, default=20,
                    help="Process first N instances (default 20 for a quick signal)")
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--resume", action="store_true",
                    help="Skip instances whose results already exist in --output")
    args = ap.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    if args.output is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        args.output = RESULTS_DIR / f"{args.dataset}_{ts}.json"

    # Probe bench MCP service is up
    try:
        mcp_call("bench-probe", "project_list", {})
    except Exception as e:
        print(f"ERROR: bench MCP service not reachable at {MCP_URL} ({e})",
              file=sys.stderr)
        print("Start it with: cd services/bench-service && docker compose up -d --build",
              file=sys.stderr)
        return 2

    print(f"Loading {args.dataset} dataset...", file=sys.stderr)
    ds = load_dataset(args.dataset, args.split)
    instances = list(ds.select(range(args.offset,
                                     min(args.offset + args.limit, len(ds)))))
    print(f"  {len(instances)} instances selected "
          f"(offset={args.offset}, limit={args.limit}, total={len(ds)})",
          file=sys.stderr)

    done_ids: set[str] = set()
    existing: list[dict] = []
    if args.resume and args.output.exists():
        with open(args.output, encoding="utf-8") as f:
            existing = json.load(f).get("per_instance", [])
        done_ids = {r["instance_id"] for r in existing}
        print(f"  resume: skipping {len(done_ids)} already-done",
              file=sys.stderr)

    results: list[dict] = list(existing)
    t_start = time.perf_counter()

    for n, inst in enumerate(instances, 1):
        if inst["instance_id"] in done_ids:
            continue
        try:
            r = run_instance(inst)
        except Exception as e:
            r = {"instance_id": inst["instance_id"],
                 "repo": inst["repo"],
                 "error": repr(e)}
        results.append(r)

        # Running tallies
        scored = [x for x in results if "hit@5" in x and x["hit@5"] is not None]
        r1 = sum(1 for x in scored if x["hit@1"]) / len(scored) if scored else 0
        r5 = sum(1 for x in scored if x["hit@5"]) / len(scored) if scored else 0
        r10 = sum(1 for x in scored if x["hit@10"]) / len(scored) if scored else 0
        elapsed = time.perf_counter() - t_start
        print(f"  [{n}/{len(instances)}] {inst['instance_id']:<40} "
              f"R@1={r1:.3f} R@5={r5:.3f} R@10={r10:.3f}  "
              f"elapsed={elapsed:.0f}s", file=sys.stderr)

        # Checkpoint every instance
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"per_instance": results}, f, indent=2)

    # Final summary
    scored = [x for x in results if "hit@5" in x and x["hit@5"] is not None]
    n = len(scored)
    summary = {
        "dataset": args.dataset,
        "split": args.split,
        "total_instances": len(results),
        "scored_instances": n,
        "recall@1": sum(1 for x in scored if x["hit@1"]) / n if n else 0,
        "recall@5": sum(1 for x in scored if x["hit@5"]) / n if n else 0,
        "recall@10": sum(1 for x in scored if x["hit@10"]) / n if n else 0,
        "errors": [x for x in results if "error" in x],
        "elapsed_sec": round(time.perf_counter() - t_start, 1),
        "per_instance": results,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(file=sys.stderr)
    print(f"RESULT ({args.dataset}, n={n}):", file=sys.stderr)
    print(f"  R@1  = {summary['recall@1']:.4f}", file=sys.stderr)
    print(f"  R@5  = {summary['recall@5']:.4f}", file=sys.stderr)
    print(f"  R@10 = {summary['recall@10']:.4f}", file=sys.stderr)
    if summary["errors"]:
        print(f"  errors: {len(summary['errors'])}", file=sys.stderr)
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
