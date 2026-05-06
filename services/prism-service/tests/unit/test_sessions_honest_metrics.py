"""Sessions page — honest metrics filtering and percentile math.

Covers two changes that landed together:

* `ConductorService._is_smoke_session` drops smoke/probe rows
  (test-* / dogfood-* prefixes, zero-token records) so they don't
  drag the mean toward zero and make real sessions look inflated.
* `sessions_page._percentile` returns the nearest-rank percentile
  used by the new median + p95 KPIs and the trend chart.
"""

from __future__ import annotations

from app.services.conductor_service import ConductorService
from app.ui.sessions_page import _percentile


def test_smoke_session_id_prefixes_are_filtered():
    is_smoke = ConductorService._is_smoke_session
    assert is_smoke({"session_id": "test-plumb", "tokens_used": 1000})
    assert is_smoke({"session_id": "dogfood-verify-1", "tokens_used": 0})
    assert is_smoke({"session_id": "sse-smoke-001", "tokens_used": 100})
    assert is_smoke({"session_id": "manual-smoke-test", "tokens_used": 0})
    assert is_smoke({"session_id": "bridge-verify-17", "tokens_used": 0})


def test_real_uuid_session_is_kept_when_tokens_present():
    is_smoke = ConductorService._is_smoke_session
    assert not is_smoke({
        "session_id": "275f5cde-0e01-4c12-9cd1-abcdef012345",
        "tokens_used": 270938,
    })


def test_zero_token_real_session_is_filtered():
    """Stop hook fired but transcript had no usable data — incomplete
    record, not useful signal."""
    is_smoke = ConductorService._is_smoke_session
    assert is_smoke({
        "session_id": "f5613ff4-357c-48aa-bbbb-ccccdddd0000",
        "tokens_used": 0,
    })


def test_percentile_empty_returns_zero():
    assert _percentile([], 50) == 0.0
    assert _percentile([], 95) == 0.0


def test_percentile_known_distribution():
    values = list(range(1, 11))  # 1..10
    # nearest-rank: median of 10 values is index 4 (value 5)
    assert _percentile(values, 50) == 5.0
    # p95 of 10 values is index 9 (value 10)
    assert _percentile(values, 95) == 10.0
    assert _percentile(values, 0) == 1.0


def test_percentile_handles_unsorted_input():
    assert _percentile([100, 1, 50, 10, 5], 50) == 10.0
