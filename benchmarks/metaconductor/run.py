"""Meta-Conductor promotion-policy benchmark.

This benchmark does not ask an LLM to generate prompts. It verifies the
server-side part of the AutoAgent-style loop: PRISM accepts candidate prompt
text as data, applies deterministic promotion gates, promotes only holdout
winners, and rejects regressions.

Usage:
    python benchmarks/metaconductor/run.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
SERVICE_ROOT = REPO_ROOT / "services" / "prism-service"
RESULTS_DIR = BENCH_DIR.parent / "results" / "metaconductor"

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@dataclass(frozen=True)
class Case:
    name: str
    metrics: dict[str, Any]
    expect_promoted: bool


CASES = [
    Case(
        name="holdout-win",
        expect_promoted=True,
        metrics={
            "baseline_score": 0.70,
            "holdout_score": 0.76,
            "train_score": 0.79,
            "contextpack_score": 1.0,
            "tests_passed": True,
            "token_ratio": 1.05,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    ),
    Case(
        name="small-holdout-delta",
        expect_promoted=False,
        metrics={
            "baseline_score": 0.70,
            "holdout_score": 0.71,
            "contextpack_score": 1.0,
            "tests_passed": True,
            "token_ratio": 1.02,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    ),
    Case(
        name="contextpack-regression",
        expect_promoted=False,
        metrics={
            "baseline_score": 0.70,
            "holdout_score": 0.78,
            "contextpack_score": 0.99,
            "tests_passed": True,
            "token_ratio": 1.02,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    ),
    Case(
        name="token-cost-regression",
        expect_promoted=False,
        metrics={
            "baseline_score": 0.70,
            "holdout_score": 0.78,
            "contextpack_score": 1.0,
            "tests_passed": True,
            "token_ratio": 1.25,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 8,
        },
    ),
    Case(
        name="too-few-samples",
        expect_promoted=False,
        metrics={
            "baseline_score": 0.70,
            "holdout_score": 0.78,
            "contextpack_score": 1.0,
            "tests_passed": True,
            "token_ratio": 1.02,
            "retry_delta": 0.0,
            "followup_delta": 0.0,
            "revert_delta": 0.0,
            "sample_n": 2,
        },
    ),
]


def run_cases(work_dir: Path) -> list[dict[str, Any]]:
    from app.services.conductor_service import ConductorService

    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    svc = ConductorService(str(work_dir / "scores.db"), enable_engine=False)
    _seed_auto_trace(work_dir / "scores.db")

    results = []
    auto = svc.auto_meta_candidate(persona="dev", step_id="green")
    auto_content = auto.get("candidate", {}).get("content", "")
    results.append(
        {
            "case": "auto-no-llm-proposal",
            "expected_promoted": False,
            "actual_promoted": False,
            "correct": bool(auto.get("created"))
            and auto.get("candidate", {}).get("generator") == "prism-rule-meta-conductor"
            and "These deterministic adjustments were generated" in auto_content
            and "narrowest relevant verification command" in auto_content,
            "reason": auto.get("reason", "created"),
            "score_delta": 0.0,
            "auto_created": bool(auto.get("created")),
        }
    )
    for case in CASES:
        proposed = svc.propose_meta_candidate(
            persona="dev",
            step_id="green",
            content=f"Candidate prompt for {case.name}: keep context MCP-owned.",
            parent_prompt_id="dev/default",
            rationale="Synthetic benchmark candidate.",
            generator="metaconductor-benchmark",
        )
        candidate_id = proposed["candidate"]["candidate_id"]
        evaluated = svc.evaluate_meta_candidate(candidate_id, case.metrics)
        actual = bool(evaluated["promoted"])
        results.append(
            {
                "case": case.name,
                "expected_promoted": case.expect_promoted,
                "actual_promoted": actual,
                "correct": actual == case.expect_promoted,
                "reason": evaluated["decision"]["reason"],
                "score_delta": evaluated["decision"]["score_delta"],
            }
        )
    return results


def _seed_auto_trace(scores_db: Path) -> None:
    conn = sqlite3.connect(scores_db)
    conn.execute(
        "INSERT INTO prompt_scores "
        "(prompt_id, persona, step_id, score, tokens_used, retries, "
        " tests_passed, gate_passed, coverage_pct, traceability_pct, timestamp) "
        "VALUES ('dev/default', 'dev', 'green', 0.42, 7200, 2, 0, 0, 0.4, 0.5, "
        " '2026-04-25T00:00:00Z')"
    )
    conn.commit()
    conn.close()


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(results) or 1
    correct = sum(1 for r in results if r["correct"])
    false_promotions = [
        r["case"] for r in results
        if r["actual_promoted"] and not r["expected_promoted"]
    ]
    missed_promotions = [
        r["case"] for r in results
        if r["expected_promoted"] and not r["actual_promoted"]
    ]
    return {
        "case_count": len(results),
        "decision_accuracy": correct / n,
        "auto_created": any(r.get("auto_created") for r in results),
        "false_promotions": false_promotions,
        "missed_promotions": missed_promotions,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--no-fail", action="store_true")
    args = ap.parse_args()

    project = f"metaconductor-{int(time.time())}"
    work_dir = RESULTS_DIR / "_work" / project
    t0 = time.perf_counter()
    per_case = run_cases(work_dir)
    summary = summarize(per_case)
    elapsed = round(time.perf_counter() - t0, 3)
    failures = []
    if summary["decision_accuracy"] < 1.0:
        failures.append(
            f"decision_accuracy {summary['decision_accuracy']:.3f} < 1.000"
        )
    if not summary["auto_created"]:
        failures.append("auto_created false")
    if summary["false_promotions"]:
        failures.append(f"false_promotions {summary['false_promotions']}")
    if summary["missed_promotions"]:
        failures.append(f"missed_promotions {summary['missed_promotions']}")

    result = {
        "benchmark": "metaconductor",
        "schema": "prism.metaconductor.benchmark.v1",
        "project": project,
        "elapsed_sec": elapsed,
        "summary": summary,
        "failures": failures,
        "per_case": per_case,
    }

    if args.output is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        args.output = RESULTS_DIR / f"metaconductor_{int(time.time())}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        "RESULT metaconductor "
        f"decision_accuracy={summary['decision_accuracy']:.3f} "
        f"auto_created={int(summary['auto_created'])} "
        f"false_promotions={len(summary['false_promotions'])} "
        f"missed_promotions={len(summary['missed_promotions'])} "
        f"elapsed={elapsed:.3f}s",
        file=sys.stderr,
    )
    print(f"Wrote {args.output}", file=sys.stderr)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 0 if args.no_fail else 1
    print("PASS metaconductor promotion gate", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
