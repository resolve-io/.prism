"""LongMemEval R@5 benchmark for PRISM Brain.

Mirrors MemPalace's benchmark methodology: one haystack session = one document,
queried with the question, check if any ground-truth session appears in top-5.

Runs against the *isolated bench service* at port 18081 — never touches
the real PRISM service at 8081.

Usage:
    # Quick stratified smoke (fast iteration during an experiment loop)
    python run.py --stratify 50 --output ../results/longmemeval/smoke.json

    # Full 500-question run
    python run.py --output ../results/longmemeval/full.json

    # Label the run so EXPERIMENTS.md can pick it up
    python run.py --stratify 50 --tag miniLM-swap --output ../results/longmemeval/miniLM_smoke.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

MCP_BASE = "http://localhost:18081/mcp/"


# ---------------------------------------------------------------------------
# MCP client (stateless)
# ---------------------------------------------------------------------------

def mcp_call(project: str, tool: str, arguments: dict[str, Any]) -> dict:
    url = f"{MCP_BASE}?project={project}"
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": tool, "arguments": arguments}}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
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
# Per-question runner (domain-based isolation inside one project)
# ---------------------------------------------------------------------------

def format_session(turns: list[dict]) -> str:
    return "\n\n".join(f"{t.get('role','user')}: {t.get('content','')}"
                       for t in turns)


def run_one(project: str, q_idx: int, entry: dict, k: int = 5) -> dict:
    domain = f"lme_q{q_idx:03d}"
    t0 = time.perf_counter()

    # Ingest haystack
    for sid, turns in zip(entry["haystack_session_ids"],
                           entry["haystack_sessions"]):
        path = f"lme/q{q_idx:03d}/{sid}"
        mcp_call(project, "brain_index_doc", {
            "path": path, "content": format_session(turns), "domain": domain,
        })
    ingest_sec = time.perf_counter() - t0

    # Query
    t1 = time.perf_counter()
    resp = mcp_call(project, "brain_search",
                    {"query": entry["question"], "domain": domain, "limit": k})
    payload = parse_result(resp) or []
    if isinstance(payload, dict):
        payload = payload.get("results") or payload.get("matches") or []
    retrieved = []
    for item in payload:
        did = item.get("doc_id", "")
        # Strip any chunk suffix (::main legacy, ::win_N sliding window,
        # ::__file__, ::__module__, ::EntityName from multi-granular chunking).
        if "::" in did:
            did = did.split("::", 1)[0]
        if did:
            retrieved.append(did.rsplit("/", 1)[-1])
    query_sec = time.perf_counter() - t1

    gold = set(entry["answer_session_ids"])
    hit = any(sid in gold for sid in retrieved)

    return {
        "q_idx": q_idx,
        "question_id": entry["question_id"],
        "question_type": entry["question_type"],
        "hit@5": hit,
        "retrieved_session_ids": retrieved,
        "gold_session_ids": list(gold),
        "ingest_sec": round(ingest_sec, 2),
        "query_sec": round(query_sec, 3),
    }


# ---------------------------------------------------------------------------
# Dataset loading & stratification
# ---------------------------------------------------------------------------

def stratified_sample(data: list[dict], n: int, seed: int = 42) -> list[tuple[int, dict]]:
    """Pick N indices balanced across question_type. Returns list of (orig_idx, entry)."""
    rng = random.Random(seed)
    by_type: dict[str, list[int]] = {}
    for i, entry in enumerate(data):
        by_type.setdefault(entry["question_type"], []).append(i)

    types = sorted(by_type.keys())
    base = n // len(types)
    rem = n - base * len(types)

    picked: list[int] = []
    for i, t in enumerate(types):
        take = base + (1 if i < rem else 0)
        take = min(take, len(by_type[t]))
        picked.extend(rng.sample(by_type[t], take))
    picked.sort()
    return [(i, data[i]) for i in picked]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", type=Path,
                    default=Path(__file__).resolve().parent.parent
                    / "data" / "longmemeval_s_cleaned.json")
    ap.add_argument("--project", default="bench-lme")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=None,
                    help="Take first N questions (no stratification)")
    ap.add_argument("--stratify", type=int, default=None,
                    help="Pick N questions balanced across question types")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tag", default=None,
                    help="Label stored in summary for EXPERIMENTS.md")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    with open(args.dataset, encoding="utf-8") as f:
        data = json.load(f)

    if args.stratify:
        sample = stratified_sample(data, args.stratify, seed=args.seed)
    elif args.limit:
        sample = [(i, data[i]) for i in range(min(args.limit, len(data)))]
    else:
        sample = [(i, entry) for i, entry in enumerate(data)]

    # Probe service
    try:
        mcp_call(args.project, "project_list", {})
    except Exception as e:
        print(f"ERROR: bench MCP not reachable at {MCP_BASE} ({e})", file=sys.stderr)
        return 2
    mcp_call(args.project, "project_create", {"project_id": args.project})

    args.output.parent.mkdir(parents=True, exist_ok=True)

    done_qids: set[str] = set()
    existing: list[dict] = []
    if args.resume and args.output.exists():
        try:
            with open(args.output, encoding="utf-8") as f:
                existing = json.load(f).get("per_question", [])
            done_qids = {r["question_id"] for r in existing}
            print(f"Resume: skipping {len(done_qids)} done", file=sys.stderr)
        except Exception:
            pass

    todo = [(i, entry) for i, entry in sample
            if entry["question_id"] not in done_qids]
    print(f"Running {len(todo)} / {len(sample)} questions "
          f"(workers={args.workers}, tag={args.tag})", file=sys.stderr)

    results: list[dict] = list(existing)
    hits = sum(1 for r in existing if r.get("hit@5"))
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(run_one, args.project, i, entry): (i, entry["question_id"])
                   for i, entry in todo}
        for n, fut in enumerate(as_completed(futures), 1):
            i, qid = futures[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"q_idx": i, "question_id": qid, "error": repr(e),
                     "hit@5": False}
            results.append(r)
            if r.get("hit@5"):
                hits += 1
            if n % 10 == 0 or n == len(todo):
                elapsed = time.perf_counter() - t0
                total = len(results)
                print(f"  [{total}/{len(sample)}] R@5={hits/total:.3f} "
                      f"elapsed={elapsed:.0f}s", file=sys.stderr)
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump({"tag": args.tag, "per_question": results}, f, indent=2)

    total = len(results)
    r5 = hits / total if total else 0.0
    by_type: dict[str, dict] = {}
    for r in results:
        t = r.get("question_type", "unknown")
        b = by_type.setdefault(t, {"n": 0, "hits": 0})
        b["n"] += 1
        if r.get("hit@5"):
            b["hits"] += 1
    for _, b in by_type.items():
        b["r@5"] = b["hits"] / b["n"] if b["n"] else 0.0

    summary = {
        "tag": args.tag,
        "dataset": str(args.dataset),
        "mode": "stratified" if args.stratify else ("limited" if args.limit else "full"),
        "sample_size": len(sample),
        "total_scored": total,
        "hits@5": hits,
        "recall@5": r5,
        "by_type": by_type,
        "elapsed_sec": round(time.perf_counter() - t0, 1),
        "per_question": results,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(file=sys.stderr)
    print(f"RESULT [{args.tag or 'untagged'}]: R@5 = {r5:.4f}  ({hits}/{total})",
          file=sys.stderr)
    for t, b in sorted(by_type.items()):
        print(f"  {t:<30} {b['r@5']:.3f}  ({b['hits']}/{b['n']})", file=sys.stderr)
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
