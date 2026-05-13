"""@app.on_startup lock cleanup tests.

Bug: the lock at ``DATA_DIR / ".mcp_started"`` lives in the bind-mounted
``/data`` volume. The ``@app.on_shutdown`` handler unlinks it on graceful
exit, but ungraceful container exits (force-recreate, host reboot,
Docker Desktop restart, kernel OOM) leave it behind. The next start
sees ``_LOCK_FILE.exists()``, short-circuits ``@app.on_startup``, and
silently skips the MCP server thread. The container appears healthy
(NiceGUI runs on 7778, ports are mapped) but port 7777 has nothing
listening — every MCP client gets ECONNRESET.

Fix: record the owning process's PID and ``/proc/<pid>/stat`` starttime
in the lock. Treat the lock as absent if its owner is no longer alive
or if its starttime no longer matches (PID was recycled).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


_HERE = Path(__file__).resolve()
_SERVICE_ROOT = _HERE.parent.parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


from app.main import (  # noqa: E402
    _lock_is_stale,
    _process_starttime_jiffies,
    _LOCK_FILE,
)


def test_starttime_for_current_process_is_readable() -> None:
    """We need /proc/<pid>/stat to be parseable on the host running
    these tests (Linux/Docker container). Sanity check."""
    starttime = _process_starttime_jiffies(os.getpid())
    assert starttime is not None
    assert starttime > 0


def test_starttime_for_missing_pid_is_none() -> None:
    """A PID that doesn't exist (very high) should yield None — used
    to detect that the owner of a stale lock has gone away."""
    assert _process_starttime_jiffies(2**22) is None


def test_lock_absent_is_not_stale(tmp_path, monkeypatch) -> None:
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    assert _lock_is_stale() is False


def test_lock_owned_by_live_self_is_not_stale(tmp_path, monkeypatch) -> None:
    """The common in-process re-entry case: this very process holds
    the lock. Must not be flagged stale, or we'd double-init."""
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    starttime = _process_starttime_jiffies(os.getpid())
    fake_lock.write_text(f"{os.getpid()}:{starttime}", encoding="utf-8")
    assert _lock_is_stale() is False


def test_lock_owned_by_dead_pid_is_stale(tmp_path, monkeypatch) -> None:
    """A lock whose recorded PID has no /proc entry is stale —
    that's the post-ungraceful-exit case we're trying to recover."""
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    # Very high PID that won't exist
    fake_lock.write_text("4194300:12345", encoding="utf-8")
    assert _lock_is_stale() is True


def test_lock_with_recycled_pid_is_stale(tmp_path, monkeypatch) -> None:
    """A lock whose PID exists but with a different starttime means
    the prior process exited and the kernel reused its PID for an
    unrelated process. The lock is stale; our service did not
    survive across that boundary."""
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    live_starttime = _process_starttime_jiffies(os.getpid())
    # Same PID, deliberately wrong starttime
    fake_lock.write_text(f"{os.getpid()}:{(live_starttime or 0) + 99999}",
                         encoding="utf-8")
    assert _lock_is_stale() is True


def test_lock_with_malformed_contents_is_stale(tmp_path, monkeypatch) -> None:
    """Corrupt or legacy-format lock (e.g. pre-fix versions wrote
    just ``threading.get_ident()`` with no separator). Treat as
    stale so the next start recovers cleanly."""
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    fake_lock.write_text("not-a-pid-format", encoding="utf-8")
    assert _lock_is_stale() is True


def test_lock_with_empty_starttime_falls_back_to_pid_check(tmp_path, monkeypatch) -> None:
    """If the starttime field is missing (legacy lock that wrote
    only an integer PID), fall back to a pure PID-alive check.
    Live PID → not stale; dead PID → stale."""
    fake_lock = tmp_path / ".mcp_started"
    monkeypatch.setattr("app.main._LOCK_FILE", fake_lock)
    # Live PID with no starttime
    fake_lock.write_text(f"{os.getpid()}:", encoding="utf-8")
    assert _lock_is_stale() is False
    # Dead PID with no starttime
    fake_lock.write_text("4194300:", encoding="utf-8")
    assert _lock_is_stale() is True
