from __future__ import annotations

import json
from argparse import Namespace
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_patch_run_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import patch_run  # type: ignore

    return patch_run


def _load_preflight_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import preflight  # type: ignore

    return preflight


def _load_eval_bundle_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import make_eval_bundle  # type: ignore

    return make_eval_bundle


def _load_compare_evaluations_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import compare_evaluations  # type: ignore

    return compare_evaluations


def _load_paired_campaign_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import paired_campaign  # type: ignore

    return paired_campaign


def _load_aggregate_evaluation_comparisons_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import aggregate_evaluation_comparisons  # type: ignore

    return aggregate_evaluation_comparisons


def _load_wsl_eval_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import evaluate_predictions_wsl  # type: ignore

    return evaluate_predictions_wsl


def _load_swebench_run_module():
    sys.path.insert(0, str(ROOT / "benchmarks" / "swebench"))
    import run  # type: ignore

    return run


def test_patch_run_prints_codex_preset_without_dataset_load():
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/patch_run.py",
            "--mode",
            "prism_on",
            "--agent-preset",
            "codex",
            "--print-agent-command",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "codex exec" in proc.stdout
    assert "approval_policy=never" in proc.stdout
    assert "--ask-for-approval" not in proc.stdout
    assert "{repo}" in proc.stdout
    assert "{instance_id}" in proc.stdout


def test_patch_run_prints_claude_preset_with_stdin_prompt():
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/patch_run.py",
            "--mode",
            "prism_off",
            "--agent-preset",
            "claude",
            "--print-agent-command",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "claude -p" in proc.stdout
    assert "type " in proc.stdout
    assert ".prism_swebench_agent_prompt.md" in proc.stdout
    assert "--mcp-config" not in proc.stdout


def test_patch_run_prints_claude_prism_on_preset_uses_project_mcp_discovery():
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/patch_run.py",
            "--mode",
            "prism_on",
            "--agent-preset",
            "claude",
            "--print-agent-command",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "claude -p" in proc.stdout
    assert "--mcp-config" not in proc.stdout
    assert "--strict-mcp-config" not in proc.stdout


def test_render_claude_command_uses_project_mcp_discovery_for_prism_on(tmp_path):
    patch_run = _load_patch_run_module()
    repo = tmp_path / "repo"
    repo.mkdir()
    mcp_config = repo / ".mcp.json"
    mcp_config.write_text("{}\n", encoding="utf-8")

    command = patch_run.render_agent_command(
        patch_run.AGENT_PRESETS["claude"],
        repo=repo,
        problem_file=repo / ".prism_swebench_problem.md",
        instance_id="demo__repo-1",
        mode="prism_on",
        mcp_url="http://localhost:18081/mcp/?project=demo",
        mcp_config=mcp_config,
    )

    assert "--mcp-config" not in command
    assert str(mcp_config) not in command
    assert "--strict-mcp-config" not in command


def test_render_claude_command_leaves_prism_off_without_mcp_config(tmp_path):
    patch_run = _load_patch_run_module()
    repo = tmp_path / "repo"
    repo.mkdir()

    command = patch_run.render_agent_command(
        patch_run.AGENT_PRESETS["claude"],
        repo=repo,
        problem_file=repo / ".prism_swebench_problem.md",
        instance_id="demo__repo-1",
        mode="prism_off",
    )

    assert "--mcp-config" not in command
    assert "--strict-mcp-config" not in command


def test_evaluate_predictions_dry_run_prints_official_command(tmp_path):
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        json.dumps({
            "instance_id": "demo__repo-1",
            "model_name_or_path": "demo",
            "model_patch": "",
        }) + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/evaluate_predictions.py",
            "--dataset",
            "lite",
            "--predictions-path",
            str(predictions),
            "--run-id",
            "dry",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "swebench.harness.run_evaluation" in proc.stdout
    assert "princeton-nlp/SWE-bench_Lite" in proc.stdout


def test_evaluate_predictions_wsl_prints_setup_command(tmp_path, monkeypatch):
    wsl_eval = _load_wsl_eval_module()
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        json.dumps({
            "instance_id": "demo__repo-1",
            "model_name_or_path": "demo",
            "model_patch": "",
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(wsl_eval, "_wsl_path", lambda path: "/mnt/e/.prism" if path == wsl_eval.ROOT else "/tmp/predictions.jsonl")

    command = wsl_eval.build_wsl_command(
        Namespace(
            dataset="lite",
            split="test",
            predictions_path=predictions,
            run_id="dry",
            max_workers=1,
            timeout=1800,
            setup=True,
            evaluator_dry_run=True,
            use_system_python=False,
        )
    )
    rendered = " ".join(command)

    assert command[:3] == ["wsl", "bash", "-lc"]
    assert "benchmarks/.venv-wsl/bin/pip" in rendered
    assert "evaluate_predictions.py" in rendered
    assert "--dry-run" in rendered


def test_evaluate_predictions_wsl_can_use_system_python(tmp_path, monkeypatch):
    wsl_eval = _load_wsl_eval_module()
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(wsl_eval, "_wsl_path", lambda path: "/mnt/e/.prism" if path == wsl_eval.ROOT else "/tmp/predictions.jsonl")

    command = wsl_eval.build_wsl_command(
        Namespace(
            dataset="lite",
            split="test",
            predictions_path=predictions,
            run_id="dry",
            max_workers=1,
            timeout=1800,
            setup=True,
            evaluator_dry_run=True,
            use_system_python=True,
        )
    )
    rendered = " ".join(command)

    assert "python3 -m pip install --user" in rendered
    assert "python3 benchmarks/swebench/evaluate_predictions.py" in rendered
    assert "benchmarks/.venv-wsl" not in rendered


def test_wsl_path_normalizes_windows_backslashes(monkeypatch):
    wsl_eval = _load_wsl_eval_module()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="/mnt/e/.prism\n", stderr="")

    monkeypatch.setattr(wsl_eval.subprocess, "run", fake_run)

    assert wsl_eval._wsl_path(Path("E:/foo/bar")) == "/mnt/e/.prism"
    assert "\\" not in calls[0][-1]


def test_compare_patch_runs_reports_generation_counts(tmp_path):
    on = tmp_path / "on.json"
    off = tmp_path / "off.json"
    on.write_text(json.dumps({
        "instances": [
            {"instance_id": "a", "patch_generated": True, "patch_chars": 10},
            {"instance_id": "b", "patch_generated": False, "error": "boom"},
        ]
    }), encoding="utf-8")
    off.write_text(json.dumps({
        "instances": [
            {"instance_id": "a", "patch_generated": False, "patch_chars": 0},
            {"instance_id": "b", "patch_generated": True, "patch_chars": 5},
        ]
    }), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/compare_patch_runs.py",
            "--prism-on",
            str(on),
            "--prism-off",
            str(off),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["instances"] == 2
    assert result["prism_on_generated"] == 1
    assert result["prism_off_generated"] == 1
    assert result["prism_on_errors"] == 1


def test_compare_evaluations_reports_helped_and_hurt(tmp_path):
    on = tmp_path / "on.json"
    off = tmp_path / "off.json"
    on.write_text(json.dumps({
        "submitted_ids": ["a", "b", "c"],
        "resolved_ids": ["a", "b"],
        "unresolved_ids": ["c"],
        "empty_patch_ids": [],
        "error_ids": [],
    }), encoding="utf-8")
    off.write_text(json.dumps({
        "submitted_ids": ["a", "b", "c"],
        "resolved_ids": ["a", "c"],
        "unresolved_ids": ["b"],
        "empty_patch_ids": [],
        "error_ids": [],
    }), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/compare_evaluations.py",
            "--prism-on-report",
            str(on),
            "--prism-off-report",
            str(off),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["prism_on_resolved_rate"] == 2 / 3
    assert result["prism_off_resolved_rate"] == 2 / 3
    assert result["delta_resolved_rate"] == 0
    assert result["prism_helped"] == 1
    assert result["prism_hurt"] == 1
    assert result["same_resolved"] == 1
    assert result["not_comparable_reason"] == "sample_size_below_30"


def test_aggregate_evaluation_comparisons_sums_pair_outcomes(tmp_path):
    c1 = tmp_path / "c1.json"
    c2 = tmp_path / "c2.json"
    c1.write_text(json.dumps({
        "per_instance": [
            {
                "instance_id": "a",
                "prism_on_status": "resolved",
                "prism_off_status": "unresolved",
                "outcome": "prism_helped",
            }
        ]
    }), encoding="utf-8")
    c2.write_text(json.dumps({
        "per_instance": [
            {
                "instance_id": "b",
                "prism_on_status": "unresolved",
                "prism_off_status": "resolved",
                "outcome": "prism_hurt",
            },
            {
                "instance_id": "c",
                "prism_on_status": "resolved",
                "prism_off_status": "resolved",
                "outcome": "same_resolved",
            },
        ]
    }), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/aggregate_evaluation_comparisons.py",
            "--comparison",
            str(c1),
            "--comparison",
            str(c2),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["instances"] == 3
    assert result["prism_on_resolved_rate"] == 2 / 3
    assert result["prism_off_resolved_rate"] == 2 / 3
    assert result["prism_helped"] == 1
    assert result["prism_hurt"] == 1
    assert result["same_resolved"] == 1


def test_paired_campaign_manifest_plans_resumable_offsets(tmp_path):
    manifest = tmp_path / "manifest.json"
    output_dir = tmp_path / "campaign"

    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "3",
            "--limit",
            "2",
            "--agent-preset",
            "claude",
            "--run-id-prefix",
            "test-campaign",
            "--output-dir",
            str(output_dir),
            "--manifest",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["benchmark"] == "swebench_paired_campaign"
    assert result["limit"] == 2
    assert len(result["pairs"]) == 2
    assert result["pairs"][0]["offset"] == 3
    assert "patch_run.py" in result["pairs"][0]["commands"]["generate_prism_on"]
    assert "--seed-max-total-bytes 500000" in result["pairs"][0]["commands"]["generate_prism_on"]
    assert "--seed-skip-graph" not in result["pairs"][0]["commands"]["generate_prism_on"]
    assert result["seed_label"] == "seed100-kb500"
    assert "evaluate_predictions_wsl.py" in result["pairs"][0]["commands"]["evaluate_prism_on"]
    assert "aggregate_evaluation_comparisons.py" in result["aggregate_command"]
    assert "_commands" not in result["pairs"][0]
    assert manifest.exists()


def test_paired_campaign_requires_confirmation_for_large_execution(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/paired_campaign.py",
            "--dataset",
            "lite",
            "--offset",
            "0",
            "--limit",
            "30",
            "--agent-preset",
            "claude",
            "--output-dir",
            str(tmp_path / "campaign"),
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--run-generation",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert proc.returncode != 0
    assert "--confirm-expensive-run is required" in proc.stderr


def test_prism_on_writes_mcp_config_and_problem_instruction(tmp_path):
    patch_run = _load_patch_run_module()

    config_path, mcp_url = patch_run._write_prism_mcp_config(tmp_path, "swe-patch-demo")
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["mcpServers"]["prism"]["type"] == "http"
    assert "project=swe-patch-demo" in config["mcpServers"]["prism"]["url"]
    assert "tool_profile=interactive" in config["mcpServers"]["prism"]["url"]

    problem = patch_run._problem_markdown(
        {
            "instance_id": "demo__repo-1",
            "repo": "demo/repo",
            "base_commit": "abc123",
            "problem_statement": "Fix it.",
        },
        "prism_on",
        mcp_url,
    )
    assert ".mcp.json" in problem
    assert mcp_url in problem
    assert "Use the PRISM tools" in problem

    prompt = patch_run._agent_prompt(
        {"instance_id": "demo__repo-1"},
        "prism_on",
        tmp_path / ".prism_swebench_problem.md",
    )
    assert "PRISM MCP server named `prism`" in prompt
    assert "Before editing" in prompt


def test_project_slug_separates_seed_limits():
    patch_run = _load_patch_run_module()

    assert patch_run._project_slug("astropy__astropy-12907", None).endswith("-full")
    assert patch_run._project_slug("astropy__astropy-12907", 25).endswith("-limit-25-lexical")
    assert patch_run._project_slug("astropy__astropy-12907", 25, "ordered").endswith("-limit-25-ordered")
    assert patch_run._project_slug("astropy__astropy-12907", 25, "lexical", True).endswith(
        "-limit-25-lexical-brainonly"
    )
    assert patch_run._project_slug(
        "astropy__astropy-12907", 25, "lexical", True, 500_000
    ).endswith("-limit-25-lexical-kb500-brainonly")
    assert (
        patch_run._project_slug("astropy__astropy-12907", None)
        != patch_run._project_slug("astropy__astropy-12907", 25)
    )
    assert (
        patch_run._project_slug("astropy__astropy-12907", 25)
        != patch_run._project_slug("astropy__astropy-12907", 25, "ordered")
    )
    assert (
        patch_run._project_slug("astropy__astropy-12907", 25)
        != patch_run._project_slug("astropy__astropy-12907", 25, "lexical", True)
    )


def test_fresh_project_slug_preserves_suffix_under_limit():
    patch_run = _load_patch_run_module()
    project = "swe-patch-" + ("very-long-" * 10)

    fresh = patch_run._fresh_project_slug(project, "123456")

    assert len(fresh) <= 80
    assert fresh.endswith("-123456")


def test_collect_seed_files_lexical_prioritizes_issue_terms(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    monkeypatch.setattr(
        patch_run,
        "iter_source_files",
        lambda repo: [
            ("docs/unrelated.rst", "generic documentation\n"),
            ("astropy/io/fits/connect.py", "fits table connect identifier\n"),
            ("astropy/table/table.py", "table serialization fits connect\n"),
        ],
    )

    files = patch_run._collect_seed_files(
        tmp_path,
        2,
        inst={
            "instance_id": "astropy__astropy-12907",
            "problem_statement": "FITS table serialization fails in astropy/io/fits/connect.py",
        },
        seed_strategy="lexical",
    )

    assert list(files) == ["astropy/io/fits/connect.py", "astropy/table/table.py"]


def test_collect_seed_files_respects_total_byte_budget(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    monkeypatch.setattr(
        patch_run,
        "iter_source_files",
        lambda repo: [
            ("target.py", "target " * 100),
            ("large.py", "target " * 10_000),
            ("small.py", "target\n"),
        ],
    )

    files = patch_run._collect_seed_files(
        tmp_path,
        3,
        inst={"instance_id": "demo__repo-1", "problem_statement": "target"},
        seed_strategy="lexical",
        max_total_bytes=1_000,
    )

    assert list(files) == ["target.py", "small.py"]


def test_seed_prism_cache_reuses_existing_marker(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    monkeypatch.setattr(patch_run, "SEED_CACHE_DIR", tmp_path / "seed_cache")
    calls = []

    def fake_mcp_call(project, tool, arguments):
        calls.append((project, tool, arguments))
        return {"result": {"content": [{"text": json.dumps({"refreshed_files": 1})}]}}

    monkeypatch.setattr(patch_run, "mcp_call", fake_mcp_call)
    monkeypatch.setattr(
        patch_run,
        "iter_source_files",
        lambda repo: [("a.py", "print(1)\n"), ("b.py", "print(2)\n")],
    )
    inst = {
        "instance_id": "demo__repo-1",
        "repo": "demo/repo",
        "base_commit": "abc123",
    }

    first = patch_run._seed_prism("swe-patch-demo", inst, tmp_path, 1, "lexical", False, False, None)
    second = patch_run._seed_prism("swe-patch-demo", inst, tmp_path, 1, "lexical", False, False, None)

    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["indexed_files"] == 1
    assert second["seed_strategy"] == "lexical"
    assert second["seed_skip_graph"] is False
    assert second["seed_require_bulk"] is False
    assert second["seed_max_total_bytes"] is None
    assert first["seed_method"] == "prism_bulk_refresh"
    assert [call[1] for call in calls].count("prism_bulk_refresh") == 1


def test_seed_prism_require_bulk_ignores_fallback_cache(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    monkeypatch.setattr(patch_run, "SEED_CACHE_DIR", tmp_path / "seed_cache")
    project = "swe-patch-demo"
    cache_dir = tmp_path / "seed_cache"
    cache_dir.mkdir(parents=True)
    cache_path = patch_run._seed_cache_path(project, 1, "lexical", True, None)
    cache_path.write_text(
        json.dumps({
            "seed_method": "brain_index_doc",
            "indexed_files": 1,
        }),
        encoding="utf-8",
    )
    calls = []

    def fake_mcp_call(project, tool, arguments):
        calls.append((project, tool, arguments))
        return {"result": {"content": [{"text": json.dumps({"busy": True})}]}}

    monkeypatch.setattr(patch_run, "mcp_call", fake_mcp_call)
    monkeypatch.setattr(patch_run, "iter_source_files", lambda repo: [("a.py", "print(1)\n")])

    try:
        patch_run._seed_prism(
            project,
            {"instance_id": "demo__repo-1", "repo": "demo/repo", "base_commit": "abc123"},
            tmp_path,
            1,
            "lexical",
            True,
            True,
            None,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected require_bulk to ignore fallback cache and fail")

    assert [call[1] for call in calls][:2] == ["project_create", "memory_store"]
    assert "prism_bulk_refresh" in [call[1] for call in calls]


def test_seed_files_falls_back_when_bulk_refresh_is_busy(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    calls = []

    def fake_mcp_call(project, tool, arguments):
        calls.append((project, tool, arguments))
        if tool == "prism_bulk_refresh":
            return {"result": {"content": [{"text": json.dumps({"busy": True})}]}}
        return {"result": {"content": [{"text": "{}"}]}}

    monkeypatch.setattr(patch_run, "mcp_call", fake_mcp_call)

    result = patch_run._seed_files("swe-patch-demo", {"a.py": "print(1)\n"})

    assert result["method"] == "brain_index_doc"
    assert result["indexed_files"] == 1
    assert "fallback_reason" in result["summary"]
    assert [call[1] for call in calls] == ["prism_bulk_refresh", "brain_index_doc", "graph_rebuild"]


def test_seed_files_can_skip_graph_rebuild(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    calls = []

    def fake_mcp_call(project, tool, arguments):
        calls.append((project, tool, arguments))
        if tool == "prism_bulk_refresh":
            return {"result": {"content": [{"text": json.dumps({"busy": True})}]}}
        return {"result": {"content": [{"text": "{}"}]}}

    monkeypatch.setattr(patch_run, "mcp_call", fake_mcp_call)

    result = patch_run._seed_files(
        "swe-patch-demo",
        {"a.py": "print(1)\n"},
        skip_graph=True,
    )

    assert result["method"] == "brain_index_doc"
    assert result["indexed_files"] == 1
    assert result["graph_ok"] is False
    assert result["graph_skipped"] is True
    assert [call[1] for call in calls] == ["prism_bulk_refresh", "brain_index_doc"]


def test_seed_files_can_require_bulk_refresh(tmp_path, monkeypatch):
    patch_run = _load_patch_run_module()
    calls = []

    def fake_mcp_call(project, tool, arguments):
        calls.append((project, tool, arguments))
        return {"result": {"content": [{"text": json.dumps({"busy": True})}]}}

    monkeypatch.setattr(patch_run, "mcp_call", fake_mcp_call)

    try:
        patch_run._seed_files(
            "swe-patch-demo",
            {"a.py": "print(1)\n"},
            require_bulk=True,
        )
    except RuntimeError as exc:
        assert "prism_bulk_refresh unavailable" in str(exc)
    else:
        raise AssertionError("expected require_bulk to fail on busy bulk refresh")

    assert [call[1] for call in calls] == ["prism_bulk_refresh"]


def test_ensure_commit_checkout_reuses_existing_repo_without_marker(tmp_path, monkeypatch):
    swe_run = _load_swebench_run_module()
    monkeypatch.setattr(swe_run, "REPOS_DIR", tmp_path)

    calls = []
    repo_dir = tmp_path / "demo__repo__abc12345"
    (repo_dir / ".git").mkdir(parents=True)

    def fake_run(cmd, cwd=None, **kwargs):
        calls.append((cmd, cwd))
        if cmd[:3] == ["git", "remote", "get-url"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/demo/repo.git\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(swe_run.subprocess, "run", fake_run)

    checkout = swe_run.ensure_commit_checkout("demo/repo", "abc123456789")

    assert checkout == repo_dir
    assert (repo_dir / ".prism_bench_ready").exists()
    assert not any(call[0][:4] == ["git", "remote", "add", "origin"] for call in calls)


def test_capture_model_patch_includes_staged_unstaged_and_new_files(tmp_path):
    patch_run = _load_patch_run_module()

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.txt").write_text("base\n", encoding="utf-8")
    (tmp_path / "staged.txt").write_text("old\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", "staged.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-q",
            "-m",
            "base",
        ],
        cwd=tmp_path,
        check=True,
    )

    (tmp_path / "tracked.txt").write_text("base\nchanged\n", encoding="utf-8")
    (tmp_path / "staged.txt").write_text("new\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=tmp_path, check=True)
    (tmp_path / "created.txt").write_text("created\n", encoding="utf-8")
    (tmp_path / ".mcp.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".prism_swebench_problem.md").write_text("problem\n", encoding="utf-8")
    (tmp_path / ".prism_swebench_agent_prompt.md").write_text("prompt\n", encoding="utf-8")
    (tmp_path / ".prism_bench_ready").write_text("", encoding="utf-8")

    patch = patch_run._capture_model_patch(
        tmp_path,
        {".mcp.json", ".prism_swebench_problem.md", ".prism_swebench_agent_prompt.md", ".prism_bench_ready"},
    )

    assert "diff --git a/tracked.txt b/tracked.txt" in patch
    assert "diff --git a/staged.txt b/staged.txt" in patch
    assert "diff --git a/created.txt b/created.txt" in patch
    assert ".mcp.json" not in patch
    assert ".prism_swebench_problem.md" not in patch
    assert ".prism_swebench_agent_prompt.md" not in patch
    assert ".prism_bench_ready" not in patch


def test_preflight_json_can_skip_expensive_checks():
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/preflight.py",
            "--skip-dataset",
            "--skip-docker",
            "--skip-official-evaluator",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode in {0, 1}
    result = json.loads(proc.stdout)
    assert result["benchmark"] == "swebench_preflight"
    assert "checks" in result
    assert "commands" in result
    assert any(check["id"] == "bench_mcp" and check.get("skipped") for check in result["checks"])
    assert any(check["id"] == "python_module:datasets" and check.get("skipped") for check in result["checks"])


def test_preflight_json_can_write_output_artifact(tmp_path):
    output = tmp_path / "preflight.json"
    proc = subprocess.run(
        [
            sys.executable,
            "benchmarks/swebench/preflight.py",
            "--skip-dataset",
            "--skip-docker",
            "--skip-official-evaluator",
            "--json",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["benchmark"] == "swebench_preflight"
    assert result["ready"] is True
    assert result["failed_required"] == []
    assert result["checked_at"]
    assert result["options"]["skip_docker"] is True


def test_preflight_helper_reports_missing_required_command(monkeypatch):
    preflight = _load_preflight_module()
    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)

    check = preflight.command_check("definitely-missing", required=True)

    assert check["id"] == "command:definitely-missing"
    assert check["required"] is True
    assert check["passed"] is False


def test_preflight_reports_evaluator_install_remediation(monkeypatch):
    preflight = _load_preflight_module()
    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda module: None)

    check = preflight.module_check("swebench.harness.run_evaluation", required=True)

    assert check["passed"] is False
    assert "requirements-swebench-eval.txt" in check["remediation"]


def test_preflight_wsl_shell_check_reports_remediation(monkeypatch):
    preflight = _load_preflight_module()

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 1, stdout="", stderr="No module named ensurepip")

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    check = preflight.wsl_shell_check(
        "wsl_python_venv",
        "python3 - <<'PY'\nimport ensurepip\nPY",
        required=True,
        remediation="Install python3.10-venv.",
    )

    assert check["passed"] is False
    assert check["required"] is True
    assert "ensurepip" in check["detail"]
    assert "python3.10-venv" in check["remediation"]


def test_preflight_reports_windows_resource_blocker(monkeypatch):
    preflight = _load_preflight_module()
    monkeypatch.setattr(preflight.importlib.util, "find_spec", lambda module: object())

    def fail_import(module):
        raise ModuleNotFoundError("No module named 'resource'")

    monkeypatch.setattr(preflight.importlib, "import_module", fail_import)

    check = preflight.module_check("swebench.harness.run_evaluation", required=True)

    assert check["passed"] is False
    assert "resource" in check["detail"]
    assert "WSL/Linux/container or Modal" in check["remediation"]


def test_make_eval_bundle_packages_predictions_and_commands(tmp_path):
    make_eval_bundle = _load_eval_bundle_module()
    pred_on = tmp_path / "prism_on.jsonl"
    pred_off = tmp_path / "prism_off.jsonl"
    pred_on.write_text(
        json.dumps({
            "instance_id": "demo__repo-1",
            "model_name_or_path": "prism-on",
            "model_patch": "diff --git a/a.py b/a.py\n",
        }) + "\n",
        encoding="utf-8",
    )
    pred_off.write_text(
        json.dumps({
            "instance_id": "demo__repo-1",
            "model_name_or_path": "prism-off",
            "model_patch": "",
        }) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "bundle.zip"

    manifest = make_eval_bundle.make_bundle(
        predictions=[pred_on, pred_off],
        dataset="lite",
        split="test",
        output=output,
        run_id_prefix="demo",
    )

    assert output.exists()
    assert manifest["dataset_name"] == "princeton-nlp/SWE-bench_Lite"
    assert manifest["predictions"][0]["patches_generated"] == 1
    assert manifest["predictions"][1]["patches_generated"] == 0
    assert "swebench.harness.run_evaluation" in manifest["commands"]["prism_on.jsonl"]

    import zipfile

    with zipfile.ZipFile(output) as zf:
        names = set(zf.namelist())
    assert "manifest.json" in names
    assert "README.md" in names
    assert "predictions/prism_on.jsonl" in names
    assert "predictions/prism_off.jsonl" in names
