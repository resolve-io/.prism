"""SWE-bench patch-generation harness for PRISM-on/off comparisons.

This script does not score correctness itself. It prepares SWE-bench repos,
runs an external coding agent command, captures the resulting patch, and can
write the official SWE-bench prediction JSONL format.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run import ensure_commit_checkout, iter_source_files, load_dataset, mcp_call, parse_result

BENCH_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCH_DIR.parent / "results" / "swebench_patch"
SEED_CACHE_DIR = RESULTS_DIR / "seed_cache"
BENCH_MCP_URL = "http://localhost:18081/mcp/"
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
MENTIONED_PATH_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+\.(?:py|pyi|rst|md|txt|yaml|yml|json|toml|cfg|ini))"
)
STOPWORDS = {
    "about", "above", "after", "again", "against", "also", "because", "before",
    "being", "between", "cannot", "could", "does", "each", "error", "fails",
    "from", "have", "into", "issue", "make", "method", "module", "must",
    "only", "problem", "return", "should", "some", "than", "that", "their",
    "there", "these", "this", "when", "where", "which", "while", "with",
    "without", "would",
}

AGENT_PRESETS = {
    "codex": (
        'codex exec --cd "{repo}" --sandbox workspace-write '
        '-c approval_policy=never --color never '
        '"You are solving SWE-bench instance {instance_id}. '
        'Read .prism_swebench_problem.md, modify the repository to fix the issue, '
        'and stop after the patch is implemented."'
    ),
    "claude": (
        'type "{agent_prompt_file}" | claude -p --permission-mode bypassPermissions '
        '--add-dir "{repo}"'
    ),
}


def render_agent_command(
    template: str,
    *,
    repo: Path,
    problem_file: Path,
    instance_id: str,
    mode: str,
    mcp_url: str = "",
    mcp_config: Path | None = None,
) -> str:
    """Render a user-supplied agent command template."""
    values = {
        "repo": str(repo),
        "problem_file": str(problem_file),
        "agent_prompt_file": str(repo / ".prism_swebench_agent_prompt.md"),
        "instance_id": instance_id,
        "mode": mode,
        "mcp_url": mcp_url,
        "mcp_config": str(mcp_config or ""),
    }
    return template.format(**values)


def _run_shell(command: str, cwd: Path, timeout_sec: int) -> dict[str, Any]:
    start = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - start, 2),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def _git_bytes(repo: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        check=True,
    )
    return proc.stdout


def _reset_checkout(repo: Path, commit: str) -> None:
    subprocess.run(["git", "reset", "--hard", commit], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "clean", "-fdx", "-e", ".prism_bench_ready"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )


def _capture_model_patch(repo: Path, exclude_paths: set[str]) -> str:
    """Capture staged, unstaged, and new files as a patch against HEAD."""
    untracked_raw = _git_bytes(repo, "ls-files", "--others", "--exclude-standard", "-z")
    untracked = [
        item.decode("utf-8", errors="ignore")
        for item in untracked_raw.split(b"\0")
        if item
    ]
    for rel in untracked:
        if rel in exclude_paths:
            continue
        subprocess.run(
            ["git", "add", "-N", "--", rel],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )

    pathspec = ["."] + [f":(exclude){path}" for path in sorted(exclude_paths)]
    return _git(repo, "diff", "--binary", "HEAD", "--", *pathspec)


def _problem_markdown(inst: dict[str, Any], mode: str, mcp_url: str | None = None) -> str:
    text = (
        f"# SWE-bench instance {inst['instance_id']}\n\n"
        f"Repository: {inst['repo']}\n"
        f"Base commit: {inst['base_commit']}\n"
        f"Mode: {mode}\n\n"
    )
    if mode == "prism_on" and mcp_url:
        text += (
            "## PRISM context\n\n"
            f"PRISM MCP is configured in `.mcp.json` as server `prism` at `{mcp_url}`.\n"
            "Use the PRISM tools for repository search, memory recall, task context, "
            "and call-chain impact before editing.\n\n"
        )
    else:
        text += (
            "## PRISM context\n\n"
            "PRISM is intentionally disabled for this run. Solve using only the "
            "repository checkout and built-in agent context.\n\n"
        )
    text += "## Problem statement\n\n" + f"{inst['problem_statement']}\n"
    return text


def _agent_prompt(inst: dict[str, Any], mode: str, problem_file: Path) -> str:
    prompt = (
        f"You are solving SWE-bench instance {inst['instance_id']}.\n"
        f"Read {problem_file.name}, modify the repository to fix the issue, "
        "and stop after the patch is implemented.\n"
        f"Mode: {mode}.\n"
    )
    if mode == "prism_on":
        prompt += (
            "\nBefore editing, use the PRISM MCP server named `prism` for a "
            "brief grounding pass: search the repository context, recall any "
            "relevant memory, and inspect call-chain or symbol context when it "
            "could affect the patch. Keep the final answer concise.\n"
        )
    return prompt


def _write_prism_mcp_config(repo: Path, project: str) -> tuple[Path, str]:
    """Write per-checkout MCP config for the seeded bench PRISM project."""
    mcp_url = f"{BENCH_MCP_URL}?project={project}&tool_profile=interactive"
    config_path = repo / ".mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "prism": {
                        "type": "http",
                        "url": mcp_url,
                    }
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path, mcp_url


def _project_slug(
    instance_id: str,
    max_files: int | None,
    seed_strategy: str = "lexical",
    skip_graph: bool = False,
    max_total_bytes: int | None = None,
) -> str:
    seed_label = "full" if max_files is None else f"limit-{max_files}"
    strategy_label = "" if max_files is None else f"-{seed_strategy}"
    bytes_label = "" if max_total_bytes is None else f"-kb{max_total_bytes // 1000}"
    graph_label = "-brainonly" if skip_graph else ""
    raw = (
        f"swe-patch-{instance_id}-{seed_label}{strategy_label}"
        f"{bytes_label}{graph_label}"
    ).lower().replace("__", "-")
    return raw[:80]


def _fresh_project_slug(project: str, suffix: str) -> str:
    return f"{project[:80 - len(suffix) - 1]}-{suffix}"


def _seed_cache_path(
    project: str,
    max_files: int | None,
    seed_strategy: str,
    skip_graph: bool,
    max_total_bytes: int | None,
) -> Path:
    limit = "full" if max_files is None else str(max_files)
    graph = "brainonly" if skip_graph else "graph"
    byte_label = "unbounded" if max_total_bytes is None else str(max_total_bytes)
    return SEED_CACHE_DIR / (
        f"{project}__limit-{limit}__strategy-{seed_strategy}"
        f"__bytes-{byte_label}__{graph}.json"
    )


def _token_counts(text: str) -> Counter[str]:
    return Counter(
        token.lower()
        for token in TOKEN_RE.findall(text)
        if token.lower() not in STOPWORDS
    )


def _mentioned_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for match in MENTIONED_PATH_RE.finditer(text):
        path = match.group("path").strip("./`'\"")
        if path.startswith(("a/", "b/")):
            path = path[2:]
        if path:
            paths.add(path.lower())
    return paths


def _score_seed_file(
    rel: str,
    content: str,
    issue_terms: Counter[str],
    issue_paths: set[str],
) -> float:
    rel_lower = rel.lower()
    path_tokens = set(TOKEN_RE.findall(rel_lower))
    score = 0.0

    for issue_path in issue_paths:
        if rel_lower == issue_path or rel_lower.endswith(f"/{issue_path}"):
            score += 10_000.0

    for term, count in issue_terms.most_common(200):
        weight = min(count, 5)
        if term in path_tokens:
            score += 90.0 * weight
        elif term in rel_lower:
            score += 20.0 * weight

    searchable = content[:120_000].lower()
    for term, count in issue_terms.most_common(120):
        occurrences = searchable.count(term)
        if occurrences:
            score += min(occurrences, 20) * min(count, 5)

    if rel_lower.endswith(".py"):
        score += 5.0
    return score


def _collect_seed_files(
    repo: Path,
    max_files: int | None,
    *,
    inst: dict[str, Any],
    seed_strategy: str,
    max_total_bytes: int | None = None,
) -> dict[str, str]:
    candidates = list(iter_source_files(repo))
    if seed_strategy == "ordered" or max_files is None:
        ranked = candidates
    else:
        issue_text = f"{inst.get('instance_id', '')}\n{inst.get('problem_statement', '')}"
        issue_terms = _token_counts(issue_text)
        issue_paths = _mentioned_paths(issue_text)
        ranked = sorted(
            candidates,
            key=lambda item: (
                -_score_seed_file(item[0], item[1], issue_terms, issue_paths),
                item[0],
            ),
        )

    selected: dict[str, str] = {}
    total_bytes = 0
    for rel, content in ranked:
        size = len(content.encode("utf-8", errors="ignore"))
        if max_total_bytes is not None and selected and total_bytes + size > max_total_bytes:
            continue
        selected[rel] = content
        total_bytes += size
        if max_files is not None and len(selected) >= max_files:
            break
    return selected


def _seed_files(
    project: str,
    files: dict[str, str],
    *,
    skip_graph: bool = False,
    require_bulk: bool = False,
) -> dict[str, Any]:
    """Seed Brain with a bulk request, falling back to per-file calls."""
    fallback_reason = ""
    try:
        resp = mcp_call(project, "prism_bulk_refresh", {
            "files": files,
            "domain": "code",
            "chunk_size": 25,
            "skip_graph": skip_graph,
        })
        payload = parse_result(resp) or {}
        if isinstance(payload, dict) and not payload.get("busy"):
            return {
                "method": "prism_bulk_refresh",
                "indexed_files": payload.get("refreshed_files", len(files)),
                "graph_ok": (
                    not skip_graph
                    and not payload.get("cancelled")
                    and not payload.get("graph_skipped")
                ),
                "graph_skipped": skip_graph or bool(payload.get("graph_skipped")),
                "summary": payload,
            }
        fallback_reason = f"prism_bulk_refresh unavailable: {payload!r}"
    except Exception as exc:
        fallback_reason = f"prism_bulk_refresh raised: {exc!r}"

    if require_bulk:
        raise RuntimeError(fallback_reason or "prism_bulk_refresh did not complete")

    indexed = 0
    for rel, content in files.items():
        mcp_call(project, "brain_index_doc", {"path": rel, "content": content, "domain": "code"})
        indexed += 1
    graph_ok = True
    if skip_graph:
        graph_ok = False
    else:
        try:
            mcp_call(project, "graph_rebuild", {})
        except Exception:
            graph_ok = False
    return {
        "method": "brain_index_doc",
        "indexed_files": indexed,
        "graph_ok": graph_ok,
        "graph_skipped": skip_graph,
        "summary": {"fallback_reason": fallback_reason},
    }


def _seed_prism(
    project: str,
    inst: dict[str, Any],
    repo: Path,
    max_files: int | None,
    seed_strategy: str,
    skip_graph: bool,
    require_bulk: bool,
    max_total_bytes: int | None,
    *,
    force_reseed: bool = False,
) -> dict[str, Any]:
    cache_path = _seed_cache_path(project, max_files, seed_strategy, skip_graph, max_total_bytes)
    if cache_path.exists() and not force_reseed:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if not require_bulk or cached.get("seed_method") == "prism_bulk_refresh":
            cached["cache_hit"] = True
            return cached

    start = time.perf_counter()
    mcp_call(project, "project_create", {"project_id": project})
    mcp_call(
        project,
        "memory_store",
        {
            "domain": "swebench",
            "name": inst["instance_id"].lower().replace("__", "-"),
            "description": (
                f"SWE-bench issue for {inst['repo']} at {inst['base_commit']}. "
                "Use Brain search and call-chain context before editing."
            ),
            "type": "decision",
            "classification": "tactical",
            "evidence": {"instance_id": inst["instance_id"], "repo": inst["repo"]},
        },
    )
    files = _collect_seed_files(
        repo,
        max_files,
        inst=inst,
        seed_strategy=seed_strategy,
        max_total_bytes=max_total_bytes,
    )
    total_bytes = sum(len(content.encode("utf-8", errors="ignore")) for content in files.values())
    seed = _seed_files(project, files, skip_graph=skip_graph, require_bulk=require_bulk)
    result = {
        "project": project,
        "instance_id": inst["instance_id"],
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "seed_max_files": max_files,
        "seed_strategy": seed_strategy,
        "seed_skip_graph": skip_graph,
        "seed_require_bulk": require_bulk,
        "seed_max_total_bytes": max_total_bytes,
        "seed_total_bytes": total_bytes,
        "indexed_files": seed["indexed_files"],
        "graph_ok": seed["graph_ok"],
        "graph_skipped": seed["graph_skipped"],
        "seed_method": seed["method"],
        "seed_summary": seed["summary"],
        "elapsed_sec": round(time.perf_counter() - start, 2),
        "cache_hit": False,
    }
    SEED_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_instance(
    inst: dict[str, Any],
    *,
    mode: str,
    agent_command_template: str,
    timeout_sec: int,
    dry_run: bool,
    seed_max_files: int | None,
    seed_strategy: str,
    seed_skip_graph: bool,
    seed_require_bulk: bool,
    seed_max_total_bytes: int | None,
    force_reseed: bool,
) -> dict[str, Any]:
    repo = ensure_commit_checkout(inst["repo"], inst["base_commit"])
    _reset_checkout(repo, inst["base_commit"])

    prism_seed = None
    mcp_config = None
    mcp_url = ""
    project = _project_slug(
        inst["instance_id"],
        seed_max_files,
        seed_strategy,
        seed_skip_graph,
        seed_max_total_bytes,
    )
    if mode == "prism_on" and force_reseed:
        suffix = datetime.now(timezone.utc).strftime("%H%M%S")
        project = _fresh_project_slug(project, suffix)
    if mode == "prism_on":
        prism_seed = _seed_prism(
            project,
            inst,
            repo,
            seed_max_files,
            seed_strategy,
            seed_skip_graph,
            seed_require_bulk,
            seed_max_total_bytes,
            force_reseed=force_reseed,
        )
        mcp_config, mcp_url = _write_prism_mcp_config(repo, project)

    problem_file = repo / ".prism_swebench_problem.md"
    problem_file.write_text(_problem_markdown(inst, mode, mcp_url or None), encoding="utf-8")
    agent_prompt_file = repo / ".prism_swebench_agent_prompt.md"
    agent_prompt_file.write_text(_agent_prompt(inst, mode, problem_file), encoding="utf-8")

    command = render_agent_command(
        agent_command_template,
        repo=repo,
        problem_file=problem_file,
        instance_id=inst["instance_id"],
        mode=mode,
        mcp_url=mcp_url,
        mcp_config=mcp_config,
    )

    if dry_run:
        agent = {"command": command, "returncode": None, "elapsed_sec": 0.0, "dry_run": True}
    else:
        agent = _run_shell(command, repo, timeout_sec)

    patch = _capture_model_patch(repo, {
        ".mcp.json",
        ".prism_swebench_problem.md",
        ".prism_swebench_agent_prompt.md",
        ".prism_bench_ready",
    })
    return {
        "instance_id": inst["instance_id"],
        "repo": inst["repo"],
        "base_commit": inst["base_commit"],
        "mode": mode,
        "problem_file": str(problem_file),
        "mcp_config": str(mcp_config) if mcp_config else None,
        "mcp_url": mcp_url or None,
        "prism_project": project if mode == "prism_on" else None,
        "prism_seed": prism_seed,
        "agent": agent,
        "patch_chars": len(patch),
        "patch_generated": bool(patch.strip()),
        "model_patch": patch,
    }


def _write_predictions(path: Path, rows: list[dict[str, Any]], model_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps({
                "instance_id": row["instance_id"],
                "model_name_or_path": model_name,
                "model_patch": row.get("model_patch", ""),
            }) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=["lite", "verified"], default="lite")
    ap.add_argument("--split", default="test")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--mode", choices=["prism_on", "prism_off"], required=True)
    ap.add_argument("--agent-command", default=None, help="Shell command template. Supports {repo}, {problem_file}, {instance_id}, {mode}.")
    ap.add_argument("--agent-preset", choices=sorted(AGENT_PRESETS), default=None)
    ap.add_argument("--print-agent-command", action="store_true")
    ap.add_argument("--timeout-sec", type=int, default=1800)
    ap.add_argument("--seed-max-files", type=int, default=None, help="Debug cap for PRISM-on indexing.")
    ap.add_argument(
        "--seed-strategy",
        choices=["lexical", "ordered"],
        default="lexical",
        help=(
            "For capped PRISM-on seeding, choose issue-text lexical relevance "
            "or repository iteration order. Full seeding ignores this."
        ),
    )
    ap.add_argument(
        "--seed-skip-graph",
        action="store_true",
        help=(
            "Skip graph_rebuild during PRISM seeding for fast Brain-only patch "
            "experiments. Do not use for full PRISM leaderboard claims."
        ),
    )
    ap.add_argument(
        "--seed-require-bulk",
        action="store_true",
        help=(
            "Fail the instance if prism_bulk_refresh is busy or unavailable "
            "instead of falling back to slow per-file indexing."
        ),
    )
    ap.add_argument(
        "--seed-max-total-bytes",
        type=int,
        default=None,
        help=(
            "Optional cap on total UTF-8 bytes selected for PRISM seeding. "
            "Useful with --seed-max-files to avoid chunk explosion."
        ),
    )
    ap.add_argument("--force-reseed", action="store_true",
                    help="Ignore PRISM seed cache marker and index again.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--predictions-jsonl", type=Path, default=None)
    ap.add_argument("--model-name", default="prism-swebench-agent")
    args = ap.parse_args()

    template = args.agent_command or (AGENT_PRESETS[args.agent_preset] if args.agent_preset else None)
    if not template:
        ap.error("provide --agent-command or --agent-preset")

    if args.print_agent_command:
        rendered = render_agent_command(
            template,
            repo=Path("{repo}"),
            problem_file=Path("{problem_file}"),
            instance_id="{instance_id}",
            mode=args.mode,
            mcp_url="{mcp_url}",
            mcp_config=Path("{mcp_config}") if args.mode == "prism_on" else None,
        )
        print(rendered)
        return 0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.output is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        args.output = RESULTS_DIR / f"{args.dataset}_{args.mode}_{ts}.json"

    ds = load_dataset(args.dataset, args.split)
    instances = list(ds.select(range(args.offset, min(args.offset + args.limit, len(ds)))))
    rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    for inst in instances:
        try:
            rows.append(run_instance(
                dict(inst),
                mode=args.mode,
                agent_command_template=template,
                timeout_sec=args.timeout_sec,
                dry_run=args.dry_run,
                seed_max_files=args.seed_max_files,
                seed_strategy=args.seed_strategy,
                seed_skip_graph=args.seed_skip_graph,
                seed_require_bulk=args.seed_require_bulk,
                seed_max_total_bytes=args.seed_max_total_bytes,
                force_reseed=args.force_reseed,
            ))
        except Exception as exc:
            rows.append({
                "instance_id": inst["instance_id"],
                "repo": inst.get("repo"),
                "mode": args.mode,
                "error": repr(exc),
                "patch_generated": False,
                "model_patch": "",
            })
        args.output.write_text(json.dumps({
            "dataset": args.dataset,
            "split": args.split,
            "mode": args.mode,
            "dry_run": args.dry_run,
            "elapsed_sec": round(time.perf_counter() - start, 2),
            "instances": rows,
        }, indent=2) + "\n", encoding="utf-8")

    if args.predictions_jsonl:
        _write_predictions(args.predictions_jsonl, rows, args.model_name)

    generated = sum(1 for row in rows if row.get("patch_generated"))
    print(json.dumps({
        "output": str(args.output),
        "predictions_jsonl": str(args.predictions_jsonl) if args.predictions_jsonl else None,
        "instances": len(rows),
        "patches_generated": generated,
        "errors": [row for row in rows if "error" in row],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
