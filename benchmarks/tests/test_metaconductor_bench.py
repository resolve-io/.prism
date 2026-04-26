from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parent.parent / "metaconductor" / "run.py"
    spec = importlib.util.spec_from_file_location("metaconductor_run", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_summary_reports_false_and_missed_promotions():
    mod = _load_module()
    summary = mod.summarize(
        [
            {
                "case": "good",
                "expected_promoted": True,
                "actual_promoted": True,
                "correct": True,
            },
            {
                "case": "false-positive",
                "expected_promoted": False,
                "actual_promoted": True,
                "correct": False,
            },
            {
                "case": "missed",
                "expected_promoted": True,
                "actual_promoted": False,
                "correct": False,
            },
        ]
    )

    assert summary["decision_accuracy"] == 1 / 3
    assert summary["auto_created"] is False
    assert summary["false_promotions"] == ["false-positive"]
    assert summary["missed_promotions"] == ["missed"]


def test_run_cases_exercises_promotion_policy(tmp_path):
    mod = _load_module()

    results = mod.run_cases(tmp_path / "work")
    summary = mod.summarize(results)

    assert summary["decision_accuracy"] == 1.0
    assert summary["auto_created"] is True
    assert summary["false_promotions"] == []
    assert summary["missed_promotions"] == []
    assert any(r["actual_promoted"] for r in results)
    assert any(not r["actual_promoted"] for r in results)
