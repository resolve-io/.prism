"""Context-pack quality benchmark for PRISM MCP.

This benchmark answers a different question than LongMemEval/SWE-bench:
when an agent asks PRISM for its operating frame via context_bundle, did
the MCP server return the right persona card, rules, template, project
memory, tasks, and Brain context without leaking unrelated role material?

Usage:
    python benchmarks/contextpack/run.py

    # Against the isolated bench service instead of in-process service code:
    python benchmarks/contextpack/run.py --mcp-url http://localhost:18081/mcp/
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
SERVICE_ROOT = REPO_ROOT / "services" / "prism-service"
RESULTS_DIR = BENCH_DIR.parent / "results" / "contextpack"

REQUIRED_RULE_IDS = {
    "rule:mcp-first",
    "rule:deterministic-context",
    "rule:retrieval-led",
    "rule:compatibility",
}


@dataclass(frozen=True)
class Case:
    name: str
    persona: str
    canonical_persona: str
    role_card_id: str
    template_id: str
    brain_tokens: tuple[str, ...]
    memory_tokens: tuple[str, ...]
    task_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...] = ()

    @property
    def expected_tokens(self) -> tuple[str, ...]:
        return self.brain_tokens + self.memory_tokens + self.task_tokens


CASES = [
    Case(
        name="dev",
        persona="dev",
        canonical_persona="dev",
        role_card_id="role-card:dev",
        template_id="template:dev-implementation",
        brain_tokens=("DEV_REFUND_POLICY",),
        memory_tokens=("DEV_MEMORY_MCP_FIRST",),
        task_tokens=("TASK_CONTEXT_BENCH", "NEXT_CONTEXT_TASK"),
        forbidden_tokens=("NOISE_RED_HERRING",),
    ),
    Case(
        name="qa",
        persona="qa",
        canonical_persona="qa",
        role_card_id="role-card:qa",
        template_id="template:qa-gate",
        brain_tokens=("QA_GATE_MATRIX",),
        memory_tokens=("QA_MEMORY_REGRESSION",),
        task_tokens=("TASK_CONTEXT_BENCH", "NEXT_CONTEXT_TASK"),
        forbidden_tokens=("NOISE_RED_HERRING",),
    ),
    Case(
        name="sm",
        persona="sm",
        canonical_persona="sm",
        role_card_id="role-card:sm",
        template_id="template:sm-task",
        brain_tokens=("SM_SCOPE_AC",),
        memory_tokens=("SM_MEMORY_ACCEPTANCE",),
        task_tokens=("TASK_CONTEXT_BENCH", "NEXT_CONTEXT_TASK"),
        forbidden_tokens=("NOISE_RED_HERRING",),
    ),
    Case(
        name="architect-alias",
        persona="winston",
        canonical_persona="architect",
        role_card_id="role-card:architect",
        template_id="template:architect-decision",
        brain_tokens=("ARCH_MCP_BOUNDARY",),
        memory_tokens=("ARCH_MEMORY_SERVICE_OWNED",),
        task_tokens=("TASK_CONTEXT_BENCH", "NEXT_CONTEXT_TASK"),
        forbidden_tokens=("NOISE_RED_HERRING",),
    ),
]


def _role_forbidden_tokens(case: Case) -> tuple[str, ...]:
    tokens: list[str] = list(case.forbidden_tokens)
    for other in CASES:
        if other.name == case.name:
            continue
        tokens.extend(other.brain_tokens)
        tokens.extend(other.memory_tokens)
    return tuple(dict.fromkeys(tokens))


DOCS = [
    {
        "path": "src/billing/payment_policy.py",
        "domain": "py",
        "content": (
            "Developer implementation context for dev persona.\n"
            "DEV_REFUND_POLICY: preserve idempotent refund processing in "
            "PaymentPolicy.process_refund and keep MCP tool contracts stable."
        ),
    },
    {
        "path": "docs/story-prd.md",
        "domain": "md",
        "content": (
            "Story Manager planning context for sm persona.\n"
            "SM_SCOPE_AC: acceptance criteria must name dependencies, risk, "
            "and validation signals before implementation starts."
        ),
    },
    {
        "path": "docs/architecture.md",
        "domain": "md",
        "content": (
            "Architect decision context for architect persona.\n"
            "ARCH_MCP_BOUNDARY: Brain, Memory, Tasks, role cards, rules, and "
            "templates are assembled service-side by the PRISM MCP server."
        ),
    },
    {
        "path": "qa/context-gate.md",
        "domain": "expertise",
        "content": (
            "QA regression context for qa persona.\n"
            "QA_GATE_MATRIX: every context-pack change needs role dispatch, "
            "determinism, recall, and leakage checks."
        ),
    },
    {
        "path": "noise/unrelated.txt",
        "domain": "misc",
        "content": (
            "NOISE_RED_HERRING: unrelated cafeteria scheduling notes that "
            "should never appear in a role-specific context pack."
        ),
    },
]


MEMORIES = [
    {
        "domain": "dev",
        "name": "dev-context-pack-rule",
        "description": (
            "DEV_MEMORY_MCP_FIRST: developers must preserve service-owned "
            "context assembly and keep client adapters thin."
        ),
        "type": "convention",
        "classification": "foundational",
        "importance": 9,
        "memory_type": "semantic",
        "evidence": {"file_paths": ["services/prism-service/app/services/context_builder.py"]},
    },
    {
        "domain": "qa",
        "name": "qa-context-pack-regression",
        "description": (
            "QA_MEMORY_REGRESSION: QA must verify role-card dispatch, rule "
            "presence, and context leakage before approving context changes."
        ),
        "type": "pattern",
        "classification": "foundational",
        "importance": 9,
        "memory_type": "semantic",
        "evidence": {"file_paths": ["services/prism-service/tests/unit/test_context_builder.py"]},
    },
    {
        "domain": "sm",
        "name": "sm-acceptance-context",
        "description": (
            "SM_MEMORY_ACCEPTANCE: story managers must package acceptance "
            "criteria, scope boundaries, dependencies, and risk."
        ),
        "type": "convention",
        "classification": "foundational",
        "importance": 9,
        "memory_type": "semantic",
        "evidence": {"file_paths": ["plugins/prism-devtools/commands/brain.md"]},
    },
    {
        "domain": "architect",
        "name": "architect-service-owned-context",
        "description": (
            "ARCH_MEMORY_SERVICE_OWNED: architects must keep Brain, Memory, "
            "Tasks, personas, and templates in MCP-owned deterministic code."
        ),
        "type": "decision",
        "classification": "foundational",
        "importance": 9,
        "memory_type": "semantic",
        "evidence": {"file_paths": ["services/prism-service/app/services/context_builder.py"]},
    },
]


class Client(Protocol):
    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        ...


class InProcessClient:
    def __init__(self, project_id: str, projects_dir: Path) -> None:
        if str(SERVICE_ROOT) not in sys.path:
            sys.path.insert(0, str(SERVICE_ROOT))

        from app import config as cfg
        from app import project_context as pc

        cfg.PROJECTS_DIR = projects_dir
        cfg.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        pc._contexts.clear()
        self.project_id = project_id

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        from app.mcp.tools import handle_tool

        result = asyncio.run(
            handle_tool(tool, arguments or {}, project_id=self.project_id)
        )
        if not result:
            return None
        text = result[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


class HttpMcpClient:
    def __init__(self, project_id: str, mcp_url: str) -> None:
        self.project_id = project_id
        self.mcp_url = mcp_url if mcp_url.endswith("/") else f"{mcp_url}/"

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        url = f"{self.mcp_url}?project={urllib.parse.quote(self.project_id)}"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments or {}},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8")
            if "text/event-stream" in resp.headers.get("Content-Type", ""):
                for line in raw.splitlines():
                    if line.startswith("data: "):
                        return self._parse_jsonrpc(json.loads(line[6:]))
            return self._parse_jsonrpc(json.loads(raw))

    @staticmethod
    def _parse_jsonrpc(resp: dict[str, Any]) -> Any:
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


def seed_project(client: Client) -> None:
    project_id = getattr(client, "project_id", "bench-contextpack")
    client.call("project_create", {"project_id": project_id})
    for doc in DOCS:
        client.call("brain_index_doc", doc)
    for memory in MEMORIES:
        client.call("memory_store", memory)

    active = client.call(
        "task_create",
        {
            "title": "TASK_CONTEXT_BENCH active context-pack validation",
            "description": (
                "Active work proves context_bundle includes in-progress "
                "task state for every persona."
            ),
            "priority": 100,
            "tags": ["contextpack", "benchmark"],
            "assigned_agent": "dev",
        },
    )
    client.call("task_update", {"id": active["id"], "status": "in_progress"})
    client.call(
        "task_create",
        {
            "title": "NEXT_CONTEXT_TASK follow-up context gate",
            "description": "Pending task proves next-task context is present.",
            "priority": 90,
            "tags": ["contextpack", "benchmark"],
            "assigned_agent": "qa",
        },
    )


def _flatten(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str)


def _stable_pack(pack: dict[str, Any]) -> dict[str, Any]:
    clone = json.loads(json.dumps(pack, sort_keys=True, default=str))
    clone.get("request", {})["request_id"] = ""
    return clone


def score_case(client: Client, case: Case) -> dict[str, Any]:
    args = {"persona": case.persona}
    first = client.call("context_bundle", args)
    second = client.call("context_bundle", args)
    pack = first["context_pack"]
    stable_first = _stable_pack(pack)
    stable_second = _stable_pack(second["context_pack"])

    role_ok = pack["request"]["persona"] == case.canonical_persona
    role_ok = role_ok and first["role_card"]["id"] == case.role_card_id
    role_ok = role_ok and first["template"]["id"] == case.template_id

    rule_ids = {rule["id"] for rule in first["rules"]}
    rules_ok = REQUIRED_RULE_IDS.issubset(rule_ids)
    deterministic_ok = pack["determinism"]["llm_generated"] is False
    deterministic_ok = deterministic_ok and stable_first["asset_versions"] == stable_second["asset_versions"]
    deterministic_ok = deterministic_ok and stable_first["role_card"] == stable_second["role_card"]
    deterministic_ok = deterministic_ok and stable_first["rules"] == stable_second["rules"]
    deterministic_ok = deterministic_ok and stable_first["template"] == stable_second["template"]

    relevant_context = pack["relevant_context"]
    context_text = _flatten(relevant_context)
    brain_text = str(relevant_context.get("brain_context", ""))
    memory_text = _flatten(relevant_context.get("memory", []))
    task_text = _flatten(relevant_context.get("active_tasks", {}))

    brain_hits = [token for token in case.brain_tokens if token in brain_text]
    memory_hits = [token for token in case.memory_tokens if token in memory_text]
    task_hits = [token for token in case.task_tokens if token in task_text]
    hits = brain_hits + memory_hits + task_hits
    forbidden_tokens = _role_forbidden_tokens(case)
    leaks = [token for token in forbidden_tokens if token in context_text]
    missing_by_channel = {
        "brain": [token for token in case.brain_tokens if token not in brain_hits],
        "memory": [token for token in case.memory_tokens if token not in memory_hits],
        "tasks": [token for token in case.task_tokens if token not in task_hits],
    }

    return {
        "case": case.name,
        "persona": case.persona,
        "canonical_persona": pack["request"]["persona"],
        "role_score": 1.0 if role_ok else 0.0,
        "rules_score": 1.0 if rules_ok else 0.0,
        "determinism_score": 1.0 if deterministic_ok else 0.0,
        "context_recall": len(hits) / len(case.expected_tokens),
        "brain_recall": len(brain_hits) / len(case.brain_tokens),
        "memory_recall": len(memory_hits) / len(case.memory_tokens),
        "task_recall": len(task_hits) / len(case.task_tokens),
        "noise_rejection": 1.0 - (len(leaks) / len(forbidden_tokens) if forbidden_tokens else 0.0),
        "expected_hits": hits,
        "brain_hits": brain_hits,
        "memory_hits": memory_hits,
        "task_hits": task_hits,
        "missing_expected": [t for t in case.expected_tokens if t not in hits],
        "missing_by_channel": missing_by_channel,
        "forbidden_hits": leaks,
        "forbidden_checked": list(forbidden_tokens),
        "asset_versions": first["asset_versions"],
    }


def summarize(per_case: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(per_case) or 1
    summary = {
        "persona_accuracy": sum(c["role_score"] for c in per_case) / n,
        "rules_presence": sum(c["rules_score"] for c in per_case) / n,
        "determinism": sum(c["determinism_score"] for c in per_case) / n,
        "context_recall": sum(c["context_recall"] for c in per_case) / n,
        "brain_recall": sum(c["brain_recall"] for c in per_case) / n,
        "memory_recall": sum(c["memory_recall"] for c in per_case) / n,
        "task_recall": sum(c["task_recall"] for c in per_case) / n,
        "noise_rejection": sum(c["noise_rejection"] for c in per_case) / n,
    }
    summary["case_count"] = len(per_case)
    summary["overall"] = (
        summary["persona_accuracy"]
        + summary["rules_presence"]
        + summary["determinism"]
        + summary["brain_recall"]
        + summary["memory_recall"]
        + summary["task_recall"]
        + summary["noise_rejection"]
    ) / 7
    return summary


def failed_thresholds(summary: dict[str, float], per_case: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    hard_thresholds = {
        "persona_accuracy": 1.0,
        "rules_presence": 1.0,
        "determinism": 1.0,
        "context_recall": 1.0,
        "brain_recall": 1.0,
        "memory_recall": 1.0,
        "task_recall": 1.0,
        "noise_rejection": 1.0,
    }
    for metric, threshold in hard_thresholds.items():
        if summary.get(metric, 0.0) < threshold:
            failures.append(f"{metric} {summary.get(metric, 0.0):.3f} < {threshold:.3f}")
    for case in per_case:
        if case["missing_expected"]:
            failures.append(f"{case['case']} missing {case['missing_expected']}")
        if case["forbidden_hits"]:
            failures.append(f"{case['case']} leaked {case['forbidden_hits']}")
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mcp-url",
        default="",
        help="Optional MCP URL, e.g. http://localhost:18081/mcp/",
    )
    ap.add_argument(
        "--project",
        default="",
        help="Project slug. Defaults to a fresh bench-contextpack slug.",
    )
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--no-fail", action="store_true", help="Always exit 0 after writing results.")
    args = ap.parse_args()

    project_id = args.project or f"bench-contextpack-{int(time.time())}"
    if args.mcp_url:
        client: Client = HttpMcpClient(project_id=project_id, mcp_url=args.mcp_url)
        mode = "http"
    else:
        work_dir = RESULTS_DIR / "_work" / project_id
        client = InProcessClient(project_id=project_id, projects_dir=work_dir / "projects")
        mode = "in-process"

    t0 = time.perf_counter()
    seed_project(client)
    per_case = [score_case(client, case) for case in CASES]
    summary = summarize(per_case)
    failures = failed_thresholds(summary, per_case)
    elapsed = round(time.perf_counter() - t0, 3)

    result = {
        "benchmark": "contextpack",
        "schema": "prism.contextpack.benchmark.v1",
        "project": project_id,
        "mode": mode,
        "elapsed_sec": elapsed,
        "summary": summary,
        "failures": failures,
        "per_case": per_case,
    }

    if args.output is None:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        args.output = RESULTS_DIR / f"contextpack_{int(time.time())}.json"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        "RESULT contextpack "
        f"context_recall={summary['context_recall']:.3f} "
        f"brain={summary['brain_recall']:.3f} "
        f"memory={summary['memory_recall']:.3f} "
        f"tasks={summary['task_recall']:.3f} "
        f"persona={summary['persona_accuracy']:.3f} "
        f"rules={summary['rules_presence']:.3f} "
        f"determinism={summary['determinism']:.3f} "
        f"noise={summary['noise_rejection']:.3f} "
        f"elapsed={elapsed:.3f}s",
        file=sys.stderr,
    )
    print(f"Wrote {args.output}", file=sys.stderr)
    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 0 if args.no_fail else 1
    print("PASS contextpack quality gate", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
