"""Stale-lock recovery on lifespan boot (v5.1.7).

Watchtower swaps the container while data/.mcp_started survives in the
mounted volume. The old behavior treated any pre-existing lock as
"another process is already running" and skipped starting every
background thread (governance, drift, quality, the v5.1.6
understand_drainer). The new behavior reclaims a stale lock and starts
the threads anyway.

Uses tmp_path so we never touch the real /data/.mcp_started.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest


@pytest.fixture
def isolated_lock(tmp_path, monkeypatch):
    import app.main as main_mod
    monkeypatch.setattr(main_mod, "_LOCK_FILE", tmp_path / ".mcp_started")
    return tmp_path / ".mcp_started"


def _run_lifespan(app=None) -> None:
    """Enter and exit the lifespan context once, synchronously."""
    import app.main as main_mod
    cm = main_mod.lifespan(app or object())

    async def runner():
        await cm.__aenter__()
        await cm.__aexit__(None, None, None)

    asyncio.run(runner())


def test_lifespan_starts_threads_when_no_lock(isolated_lock):
    assert not isolated_lock.exists()
    with patch("app.main.threading.Thread") as mock_t, \
            patch("app.main._install_stackdump_handler"):
        _run_lifespan()

    # 5 daemon threads: mcp + governance + drift + quality + drainer.
    started = [c for c in mock_t.return_value.start.mock_calls]
    assert len(started) == 5


def test_lifespan_reclaims_stale_lock_and_starts_threads(isolated_lock, capsys):
    # Simulate a previous container's lock left behind.
    isolated_lock.write_text("999999", encoding="utf-8")
    assert isolated_lock.exists()

    with patch("app.main.threading.Thread") as mock_t, \
            patch("app.main._install_stackdump_handler"):
        _run_lifespan()

    started = [c for c in mock_t.return_value.start.mock_calls]
    assert len(started) == 5  # threads started despite the stale lock

    err = capsys.readouterr().err
    assert "stale lock detected" in err
    assert "999999" in err  # the prior tid is reported


def test_lifespan_unlinks_lock_on_exit(isolated_lock):
    with patch("app.main.threading.Thread"), \
            patch("app.main._install_stackdump_handler"):
        _run_lifespan()
    assert not isolated_lock.exists()
