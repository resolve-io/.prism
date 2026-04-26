from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parent.parent / "contextpack" / "run.py"
    spec = importlib.util.spec_from_file_location("contextpack_run", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_summary_averages_context_pack_metrics():
    mod = _load_module()
    per_case = [
        {
            "role_score": 1.0,
            "rules_score": 1.0,
            "determinism_score": 1.0,
            "context_recall": 1.0,
            "brain_recall": 1.0,
            "memory_recall": 1.0,
            "task_recall": 1.0,
            "noise_rejection": 1.0,
        },
        {
            "role_score": 0.0,
            "rules_score": 1.0,
            "determinism_score": 0.0,
            "context_recall": 0.5,
            "brain_recall": 0.0,
            "memory_recall": 0.5,
            "task_recall": 1.0,
            "noise_rejection": 1.0,
        },
    ]

    summary = mod.summarize(per_case)

    assert summary["persona_accuracy"] == 0.5
    assert summary["rules_presence"] == 1.0
    assert summary["determinism"] == 0.5
    assert summary["context_recall"] == 0.75
    assert summary["brain_recall"] == 0.5
    assert summary["memory_recall"] == 0.75
    assert summary["task_recall"] == 1.0
    assert summary["noise_rejection"] == 1.0


def test_failed_thresholds_reports_missing_and_leaked_tokens():
    mod = _load_module()
    summary = {
        "persona_accuracy": 1.0,
        "rules_presence": 1.0,
        "determinism": 1.0,
        "context_recall": 0.75,
        "brain_recall": 1.0,
        "memory_recall": 0.5,
        "task_recall": 1.0,
        "noise_rejection": 0.5,
    }
    per_case = [
        {
            "case": "dev",
            "missing_expected": ["DEV_MEMORY_MCP_FIRST"],
            "forbidden_hits": ["SM_SCOPE_AC"],
        }
    ]

    failures = mod.failed_thresholds(summary, per_case)

    assert any("context_recall" in f for f in failures)
    assert any("memory_recall" in f for f in failures)
    assert any("noise_rejection" in f for f in failures)
    assert any("missing" in f and "DEV_MEMORY_MCP_FIRST" in f for f in failures)
    assert any("leaked" in f and "SM_SCOPE_AC" in f for f in failures)


def test_role_forbidden_tokens_include_other_persona_context():
    mod = _load_module()
    dev = next(case for case in mod.CASES if case.name == "dev")

    forbidden = mod._role_forbidden_tokens(dev)

    assert "NOISE_RED_HERRING" in forbidden
    assert "QA_GATE_MATRIX" in forbidden
    assert "QA_MEMORY_REGRESSION" in forbidden
    assert "SM_SCOPE_AC" in forbidden
    assert "ARCH_MCP_BOUNDARY" in forbidden
    assert "DEV_REFUND_POLICY" not in forbidden


def test_stable_pack_ignores_request_id_only():
    mod = _load_module()
    pack = {
        "request": {"request_id": "abc", "persona": "dev"},
        "asset_versions": {"role_card": "123"},
    }

    stable = mod._stable_pack(pack)

    assert stable["request"]["request_id"] == ""
    assert stable["request"]["persona"] == "dev"
    assert stable["asset_versions"] == {"role_card": "123"}
