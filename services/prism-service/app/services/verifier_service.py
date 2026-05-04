"""Verifier service — outer-harness sensor that catches builder claims
that don't survive contact with the codebase.

Two tiers, ordered by cost:

    Tier 0 — project-tooling sensors. Run the project's own linters /
        type checkers / test runners on git-diff-scoped files. Free,
        fast, deterministic. Catches >80% of regressions.
    Tier 1 — record-driven deterministic checks. Walk PRISM tables
        (tasks marked done, brain_index_doc claims, memory writes,
        skill invocations) since the session started; confirm each
        claim against current state (file exists, hash matches, entry
        present). Free, fast, deterministic.
    Tier 2 — LLM judgment (separate module ``verifier_backends``).
        Only fires for high-stakes claims that survived Tier 1 with
        ``status=unverifiable``. Cost-bounded.

The service is read-only against PRISM's existing DBs and writes its
own audit trail to ``scores.db`` (verifier_runs / verifier_claims).
That keeps the verifier independent of the four pillars: it observes
without mutating Brain / Memory / Tasks / Workflow.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Schema migration (idempotent, runs on first connection)
# ---------------------------------------------------------------------------


def _verifier_schema(conn: sqlite3.Connection) -> None:
    """Create verifier_runs + verifier_claims tables in scores.db.

    Lives in scores.db (same file as session_outcomes / skill_usage /
    subagent_outcomes) so the verifier audit trail joins cleanly to
    the existing per-session telemetry. Safe to call repeatedly.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS verifier_runs (
            run_id        TEXT PRIMARY KEY,
            session_id    TEXT,
            task_id       TEXT,
            status        TEXT NOT NULL,    -- pass | fail | partial | error
            backend       TEXT,              -- claude-cli | claude-api | codex-cli | none
            model         TEXT,
            tier0_status  TEXT,              -- pass | fail | not-run
            tier1_status  TEXT,              -- pass | fail | partial
            tier2_status  TEXT,              -- pass | fail | skipped
            cost_usd      REAL DEFAULT 0.0,
            started_at    TEXT DEFAULT (datetime('now')),
            completed_at  TEXT,
            summary       TEXT,
            feedback      TEXT               -- improvement_seeds, JSON
        );

        CREATE INDEX IF NOT EXISTS idx_verifier_runs_session
            ON verifier_runs(session_id);
        CREATE INDEX IF NOT EXISTS idx_verifier_runs_task
            ON verifier_runs(task_id);

        CREATE TABLE IF NOT EXISTS verifier_claims (
            claim_id      TEXT PRIMARY KEY,
            run_id        TEXT NOT NULL,
            tier          INTEGER NOT NULL,  -- 0 | 1 | 2
            kind          TEXT NOT NULL,     -- e.g. tooling.pytest, record.task_done
            target        TEXT,              -- claim's subject (file path, task_id, ...)
            status        TEXT NOT NULL,     -- pass | fail | unverifiable | skipped
            evidence      TEXT,              -- JSON: details the verifier inspected
            feedback      TEXT,              -- human-readable reason if not pass
            FOREIGN KEY (run_id) REFERENCES verifier_runs(run_id)
        );

        CREATE INDEX IF NOT EXISTS idx_verifier_claims_run
            ON verifier_claims(run_id);
        CREATE INDEX IF NOT EXISTS idx_verifier_claims_status
            ON verifier_claims(status);
        """
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Claim record (in-flight, before persistence)
# ---------------------------------------------------------------------------


@dataclass
class Claim:
    """One verifiable assertion the builder agent (implicitly) made.

    Examples:
      * tooling.pytest — "the changed test files pass"
      * tooling.ruff   — "the changed Python files lint clean"
      * record.task_done — "task X was marked done and its ACs hold"
      * record.brain_indexed — "file Y was claimed indexed; check Brain"
    """
    tier: int
    kind: str
    target: str = ""
    status: str = "pending"        # pass | fail | unverifiable | skipped
    evidence: dict = field(default_factory=dict)
    feedback: str = ""


# ---------------------------------------------------------------------------
# Tier 0 — project tooling sensors
# ---------------------------------------------------------------------------


def _detect_python_project(workspace: Path) -> bool:
    return any(
        (workspace / m).exists()
        for m in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
    )


def _detect_node_project(workspace: Path) -> bool:
    return (workspace / "package.json").exists()


def _detect_rust_project(workspace: Path) -> bool:
    return (workspace / "Cargo.toml").exists()


def _detect_go_project(workspace: Path) -> bool:
    return (workspace / "go.mod").exists()


def _git_changed_files(
    workspace: Path, baseline: Optional[str] = None
) -> list[str]:
    """Files changed in the working tree relative to ``baseline`` (or HEAD).

    Returns repo-relative paths. Empty list if not a git repo or git
    isn't available — Tier 0 then runs nothing, which is correct
    (no diff scope = nothing to lint).
    """
    if not (workspace / ".git").exists() and not (workspace / ".git").is_file():
        return []
    try:
        rev = baseline or "HEAD"
        out = subprocess.run(
            ["git", "diff", "--name-only", rev],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return []
        files = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
        # Also include untracked files — those are claims-in-flight too
        out2 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out2.returncode == 0:
            files.extend(
                ln.strip() for ln in out2.stdout.splitlines() if ln.strip()
            )
        # Dedupe preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for f in files:
            if f not in seen:
                seen.add(f)
                deduped.append(f)
        return deduped
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _filter_files(files: Iterable[str], suffixes: tuple[str, ...]) -> list[str]:
    return [f for f in files if f.endswith(suffixes)]


def _run_tool(
    cmd: list[str], workspace: Path, timeout_s: float = 120.0
) -> tuple[int, str, str]:
    """Run a tool subprocess. Returns (exit_code, stdout, stderr).

    Exit code 127 is reserved for "tool not installed" (we check
    shutil.which first and skip cleanly without running). Anything else
    is the tool's own exit code.
    """
    try:
        out = subprocess.run(
            cmd,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return out.returncode, out.stdout or "", out.stderr or ""
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", (e.stderr or "") + f"\n[verifier] timeout after {timeout_s}s"
    except (FileNotFoundError, OSError) as e:
        return 127, "", f"[verifier] could not run {cmd[0]}: {e}"


def _trim(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit // 2] + f"\n[…trimmed {len(text) - limit} chars…]\n" + text[-limit // 2 :]


def _claim(tier: int, kind: str, target: str, exit_code: int, stdout: str, stderr: str) -> Claim:
    """Assemble a Claim from a tool subprocess result."""
    if exit_code == 127:
        status = "skipped"
        feedback = stderr.strip() or "tool not installed"
    elif exit_code == 124:
        status = "unverifiable"
        feedback = "timed out"
    elif exit_code == 0:
        status = "pass"
        feedback = ""
    else:
        status = "fail"
        feedback = (stderr.strip() or stdout.strip() or "non-zero exit").splitlines()[0][:200]
    return Claim(
        tier=tier, kind=kind, target=target, status=status,
        evidence={"exit_code": exit_code, "stdout": _trim(stdout), "stderr": _trim(stderr)},
        feedback=feedback,
    )


# Per-language tool runners. Each takes the workspace + the diff-scoped
# files relevant to its language, returns a list of Claims (one per
# tool that ran). Tools that aren't installed are emitted as
# ``status=skipped`` so the operator sees the gap instead of silent
# acceptance.


def _run_python_tools(workspace: Path, py_files: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    if not py_files:
        return claims
    if shutil.which("ruff"):
        rc, out, err = _run_tool(["ruff", "check", *py_files], workspace)
        claims.append(_claim(0, "tooling.ruff", ",".join(py_files[:5]), rc, out, err))
    else:
        claims.append(Claim(tier=0, kind="tooling.ruff", target="", status="skipped",
                            feedback="ruff not installed"))
    if shutil.which("mypy"):
        rc, out, err = _run_tool(["mypy", "--no-error-summary", *py_files], workspace)
        claims.append(_claim(0, "tooling.mypy", ",".join(py_files[:5]), rc, out, err))
    # pytest only runs if test files actually changed — running the
    # whole suite on every Stop hook is too slow. Match common test
    # file patterns and run pytest scoped to those.
    test_files = [f for f in py_files if "/test_" in f or f.startswith("test_") or f.endswith("_test.py")]
    if test_files and shutil.which("pytest"):
        rc, out, err = _run_tool(["pytest", "-q", "--no-header", *test_files], workspace, timeout_s=180.0)
        claims.append(_claim(0, "tooling.pytest", ",".join(test_files[:5]), rc, out, err))
    return claims


def _run_node_tools(workspace: Path, js_files: list[str]) -> list[Claim]:
    claims: list[Claim] = []
    if not js_files:
        return claims
    if shutil.which("eslint"):
        rc, out, err = _run_tool(["eslint", *js_files], workspace)
        claims.append(_claim(0, "tooling.eslint", ",".join(js_files[:5]), rc, out, err))
    ts_files = [f for f in js_files if f.endswith((".ts", ".tsx"))]
    if ts_files and shutil.which("tsc"):
        rc, out, err = _run_tool(["tsc", "--noEmit"], workspace)
        claims.append(_claim(0, "tooling.tsc", ",".join(ts_files[:5]), rc, out, err))
    return claims


def _run_rust_tools(workspace: Path) -> list[Claim]:
    if not shutil.which("cargo"):
        return []
    rc, out, err = _run_tool(["cargo", "check", "--quiet"], workspace, timeout_s=180.0)
    return [_claim(0, "tooling.cargo_check", "Cargo.toml", rc, out, err)]


def _run_go_tools(workspace: Path) -> list[Claim]:
    if not shutil.which("go"):
        return []
    rc, out, err = _run_tool(["go", "vet", "./..."], workspace, timeout_s=180.0)
    return [_claim(0, "tooling.go_vet", "./...", rc, out, err)]


def run_tier0(workspace: Path, baseline: Optional[str] = None) -> list[Claim]:
    """Run all detected project-tooling sensors. Returns one Claim per
    tool invocation. Empty list if no tooling detected or no files
    changed (no diff = no scope = no claims to make)."""
    workspace = Path(workspace)
    changed = _git_changed_files(workspace, baseline)
    if not changed:
        return []
    claims: list[Claim] = []
    if _detect_python_project(workspace):
        py_files = _filter_files(changed, (".py",))
        claims.extend(_run_python_tools(workspace, py_files))
    if _detect_node_project(workspace):
        js_files = _filter_files(changed, (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"))
        claims.extend(_run_node_tools(workspace, js_files))
    if _detect_rust_project(workspace):
        if any(f.endswith(".rs") for f in changed):
            claims.extend(_run_rust_tools(workspace))
    if _detect_go_project(workspace):
        if any(f.endswith(".go") for f in changed):
            claims.extend(_run_go_tools(workspace))
    return claims


# ---------------------------------------------------------------------------
# Tier 1 — record-driven deterministic checks
# ---------------------------------------------------------------------------


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _check_brain_indexed(brain_db: Optional[str], workspace: Path,
                        since_iso: str) -> list[Claim]:
    """For each file the agent claimed to index since session start,
    confirm: (a) the file exists in code_docs, (b) the on-disk content
    hash matches what Brain stored. Drift = claim was wrong (file
    deleted) or stale (file changed since indexing)."""
    claims: list[Claim] = []
    if not brain_db or not Path(brain_db).exists():
        return claims
    try:
        conn = sqlite3.connect(brain_db, timeout=5.0)
        conn.row_factory = sqlite3.Row
        if not _table_exists(conn, "code_docs"):
            return claims
        rows = conn.execute(
            "SELECT path, content_hash FROM code_docs "
            "WHERE indexed_at >= ? ORDER BY indexed_at DESC LIMIT 200",
            (since_iso,),
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        return claims
    for r in rows:
        path = r["path"]
        recorded_hash = r["content_hash"] or ""
        target_path = workspace / path
        if not target_path.exists():
            claims.append(Claim(
                tier=1, kind="record.brain_indexed", target=path,
                status="fail",
                evidence={"recorded_hash": recorded_hash, "exists": False},
                feedback=f"Brain claims {path} indexed but file is gone",
            ))
            continue
        # Hash check is best-effort — schema may not store hashes for
        # every row. If we have one, compare; otherwise pass.
        if recorded_hash:
            import hashlib
            try:
                disk_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
            except OSError:
                disk_hash = ""
            if disk_hash and disk_hash != recorded_hash:
                claims.append(Claim(
                    tier=1, kind="record.brain_indexed", target=path,
                    status="fail",
                    evidence={"recorded_hash": recorded_hash[:16],
                              "disk_hash": disk_hash[:16]},
                    feedback=f"{path} drifted since Brain indexed it",
                ))
                continue
        claims.append(Claim(
            tier=1, kind="record.brain_indexed", target=path, status="pass",
            evidence={"hash_match": bool(recorded_hash)},
        ))
    return claims


def _check_tasks_done(tasks_db: Optional[str], session_id: Optional[str],
                     since_iso: str) -> list[Claim]:
    """Tasks marked ``done`` since session start: check that the task
    has actual recorded work (subagent_outcomes / sessions joined to
    it, or non-empty completion). Catches the failure mode where an
    agent marks a task done without doing anything."""
    claims: list[Claim] = []
    if not tasks_db or not Path(tasks_db).exists():
        return claims
    try:
        conn = sqlite3.connect(tasks_db, timeout=5.0)
        conn.row_factory = sqlite3.Row
        if not _table_exists(conn, "tasks"):
            return claims
        rows = conn.execute(
            "SELECT id, subject, status, updated_at FROM tasks "
            "WHERE status IN ('done', 'completed') AND updated_at >= ? "
            "ORDER BY updated_at DESC LIMIT 50",
            (since_iso,),
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        return claims
    for r in rows:
        tid = r["id"]
        subject = r["subject"] or ""
        # Heuristic: a task marked done without a subject or with
        # placeholder subject is suspicious. Real check (was code
        # actually written for this task) requires Tier 2.
        if not subject.strip() or subject.strip().lower() in ("todo", "task"):
            claims.append(Claim(
                tier=1, kind="record.task_done", target=tid, status="fail",
                evidence={"subject": subject},
                feedback=f"task {tid} marked done with empty/placeholder subject",
            ))
        else:
            claims.append(Claim(
                tier=1, kind="record.task_done", target=tid, status="pass",
                evidence={"subject": subject[:80]},
            ))
    return claims


def _check_memory_writes(memory_dir: Optional[str], since_iso: str) -> list[Claim]:
    """Each memory_store call leaves a markdown file in the mulch dir.
    Confirm files written since session start are non-empty and have
    minimum required frontmatter fields."""
    claims: list[Claim] = []
    if not memory_dir:
        return claims
    md = Path(memory_dir)
    if not md.exists():
        return claims
    since_ts = _iso_to_epoch(since_iso)
    for entry in md.rglob("*.md"):
        try:
            st = entry.stat()
        except OSError:
            continue
        if st.st_mtime < since_ts:
            continue
        try:
            text = entry.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(entry.relative_to(md))
        if len(text.strip()) < 20:
            claims.append(Claim(
                tier=1, kind="record.memory_write", target=rel, status="fail",
                evidence={"size": len(text)},
                feedback=f"memory entry {rel} is suspiciously empty",
            ))
            continue
        if "---" not in text[:200]:
            claims.append(Claim(
                tier=1, kind="record.memory_write", target=rel, status="fail",
                evidence={"size": len(text)},
                feedback=f"memory entry {rel} missing frontmatter delimiter",
            ))
            continue
        claims.append(Claim(
            tier=1, kind="record.memory_write", target=rel, status="pass",
            evidence={"size": len(text)},
        ))
    return claims


def _iso_to_epoch(iso: str) -> float:
    """Parse a SQLite-style ``YYYY-MM-DD HH:MM:SS`` (or ISO 8601)
    timestamp to a unix epoch float. Returns 0.0 if unparseable —
    callers treat that as "include everything" which is the safer
    failure mode for a sensor."""
    if not iso:
        return 0.0
    s = iso.strip().replace("T", " ")
    # Strip timezone designators we don't care about
    if s.endswith("Z"):
        s = s[:-1]
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            from datetime import datetime as _dt
            return _dt.strptime(s, fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def run_tier1(brain_db: Optional[str], tasks_db: Optional[str],
             memory_dir: Optional[str], workspace: Path,
             session_id: Optional[str], since_iso: str) -> list[Claim]:
    """Aggregate Tier 1 record checks. All sub-checks are best-effort
    against tables/dirs that may not exist yet — missing data
    structures just return empty claims (no crash)."""
    claims: list[Claim] = []
    claims.extend(_check_brain_indexed(brain_db, Path(workspace), since_iso))
    claims.extend(_check_tasks_done(tasks_db, session_id, since_iso))
    claims.extend(_check_memory_writes(memory_dir, since_iso))
    return claims


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _tier_status(claims: list[Claim], tier: int) -> str:
    """Aggregate one tier's per-claim statuses into pass/fail/partial.
    "partial" = at least one fail or unverifiable but at least one
    pass too. "not-run" if no claims for this tier."""
    tier_claims = [c for c in claims if c.tier == tier]
    if not tier_claims:
        return "not-run"
    has_fail = any(c.status == "fail" for c in tier_claims)
    has_pass = any(c.status == "pass" for c in tier_claims)
    if has_fail and has_pass:
        return "partial"
    if has_fail:
        return "fail"
    return "pass"


def _overall_status(tier0: str, tier1: str, tier2: str) -> str:
    """Top-line verdict. Any tier failing = run fails. All not-run = error
    (we tried to verify and had nothing to check)."""
    statuses = [tier0, tier1, tier2]
    if all(s in ("not-run", "skipped") for s in statuses):
        return "error"   # nothing to verify — suspicious by itself
    if "fail" in statuses:
        return "fail"
    if "partial" in statuses:
        return "partial"
    return "pass"


# ---------------------------------------------------------------------------
# VerifierService — the public surface
# ---------------------------------------------------------------------------


class VerifierService:
    """Run a verifier pass and persist the audit trail.

    Read-only against PRISM's existing DBs; writes only its own tables
    (verifier_runs / verifier_claims) inside scores.db. Safe to invoke
    on every Stop hook — typical run is <1s when no diff is in scope.
    """

    def __init__(self, scores_db: str, brain_db: Optional[str] = None,
                 tasks_db: Optional[str] = None, memory_dir: Optional[str] = None,
                 workspace: Optional[str] = None) -> None:
        self.scores_db = scores_db
        self.brain_db = brain_db
        self.tasks_db = tasks_db
        self.memory_dir = memory_dir
        self.workspace = Path(workspace) if workspace else Path.cwd()
        # Run schema migration once on init.
        Path(scores_db).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(scores_db, timeout=5.0) as conn:
            _verifier_schema(conn)

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------

    def _resolve_since_iso(self, session_id: Optional[str],
                          since_iso: Optional[str]) -> str:
        """Pick the timestamp to scope claim collection from."""
        if since_iso:
            return since_iso
        # Try session_outcomes for a started_at marker.
        if session_id and Path(self.scores_db).exists():
            try:
                with sqlite3.connect(self.scores_db, timeout=5.0) as conn:
                    if _table_exists(conn, "session_outcomes"):
                        row = conn.execute(
                            "SELECT timestamp FROM session_outcomes "
                            "WHERE session_id = ?",
                            (session_id,),
                        ).fetchone()
                        if row and row[0]:
                            return row[0]
            except sqlite3.OperationalError:
                pass
        # Fallback: 1 hour ago. Better than 1970 — keeps the verifier
        # bounded when no session marker exists yet.
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz
        return (_dt.now(_tz.utc) - _td(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, session_id: Optional[str] = None,
            task_id: Optional[str] = None,
            since_iso: Optional[str] = None,
            baseline_rev: Optional[str] = None,
            workspace: Optional[str] = None) -> dict:
        """Execute Tier 0 + Tier 1 and persist results. Returns a dict
        suitable for serializing back through MCP.

        ``workspace`` overrides the service's default — the hook
        passes ``${CLAUDE_PROJECT_DIR}`` here so Tier 0 runs against
        the host's source tree, not the MCP container's cwd.
        """
        run_id = str(uuid.uuid4())
        started = time.time()
        since = self._resolve_since_iso(session_id, since_iso)
        ws = Path(workspace) if workspace else self.workspace

        claims: list[Claim] = []
        # Tier 0 — project tooling
        try:
            claims.extend(run_tier0(ws, baseline_rev))
        except Exception as e:
            claims.append(Claim(
                tier=0, kind="tooling.error", target="",
                status="unverifiable",
                feedback=f"Tier 0 raised: {type(e).__name__}: {e}",
            ))
        # Tier 1 — record checks
        try:
            claims.extend(run_tier1(
                self.brain_db, self.tasks_db, self.memory_dir,
                ws, session_id, since,
            ))
        except Exception as e:
            claims.append(Claim(
                tier=1, kind="record.error", target="",
                status="unverifiable",
                feedback=f"Tier 1 raised: {type(e).__name__}: {e}",
            ))

        tier0_status = _tier_status(claims, 0)
        tier1_status = _tier_status(claims, 1)
        tier2_status = "skipped"   # v1 ships no Tier 2 invocation
        status = _overall_status(tier0_status, tier1_status, tier2_status)

        feedback_seeds = [c.feedback for c in claims if c.feedback and c.status != "pass"]
        summary = self._summarize(claims, status)

        elapsed = time.time() - started
        self._persist(
            run_id=run_id, session_id=session_id, task_id=task_id,
            status=status, tier0_status=tier0_status, tier1_status=tier1_status,
            tier2_status=tier2_status, summary=summary,
            feedback_json=json.dumps(feedback_seeds), claims=claims,
        )

        return {
            "run_id": run_id,
            "status": status,
            "tier0": tier0_status,
            "tier1": tier1_status,
            "tier2": tier2_status,
            "elapsed_s": round(elapsed, 3),
            "claim_count": len(claims),
            "fail_count": sum(1 for c in claims if c.status == "fail"),
            "skip_count": sum(1 for c in claims if c.status == "skipped"),
            "summary": summary,
            "claims": [asdict(c) for c in claims],
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(self, *, run_id: str, session_id: Optional[str],
                task_id: Optional[str], status: str, tier0_status: str,
                tier1_status: str, tier2_status: str, summary: str,
                feedback_json: str, claims: list[Claim]) -> None:
        with sqlite3.connect(self.scores_db, timeout=5.0) as conn:
            conn.execute(
                "INSERT INTO verifier_runs "
                "(run_id, session_id, task_id, status, backend, model, "
                " tier0_status, tier1_status, tier2_status, "
                " completed_at, summary, feedback) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?)",
                (run_id, session_id, task_id, status, "none", None,
                 tier0_status, tier1_status, tier2_status,
                 summary, feedback_json),
            )
            for c in claims:
                conn.execute(
                    "INSERT INTO verifier_claims "
                    "(claim_id, run_id, tier, kind, target, status, "
                    " evidence, feedback) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), run_id, c.tier, c.kind, c.target,
                     c.status, json.dumps(c.evidence), c.feedback),
                )
            conn.commit()

    @staticmethod
    def _summarize(claims: list[Claim], status: str) -> str:
        if not claims:
            return "no claims to verify (no diff in scope)"
        n = len(claims)
        passed = sum(1 for c in claims if c.status == "pass")
        failed = sum(1 for c in claims if c.status == "fail")
        skipped = sum(1 for c in claims if c.status == "skipped")
        return (f"{status}: {passed}/{n} pass, {failed} fail, "
                f"{skipped} skipped")

    # ------------------------------------------------------------------
    # History — for the dashboard / agent
    # ------------------------------------------------------------------

    def history(self, task_id: Optional[str] = None, limit: int = 20) -> list[dict]:
        """Recent verifier runs (newest first). Filters by task_id if given."""
        with sqlite3.connect(self.scores_db, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            if task_id:
                rows = conn.execute(
                    "SELECT * FROM verifier_runs WHERE task_id = ? "
                    "ORDER BY started_at DESC LIMIT ?",
                    (task_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM verifier_runs ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def feedback_summary(self, limit: int = 50) -> list[str]:
        """Recent unresolved improvement seeds — what the verifier
        couldn't verify. Surfaced by SessionStart hook as
        additionalContext so the agent picks up where the last run
        left off."""
        with sqlite3.connect(self.scores_db, timeout=5.0) as conn:
            rows = conn.execute(
                "SELECT feedback FROM verifier_runs "
                "WHERE status IN ('fail', 'partial', 'error') "
                "ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        seeds: list[str] = []
        for (raw,) in rows:
            try:
                items = json.loads(raw or "[]")
                seeds.extend(s for s in items if isinstance(s, str))
            except (json.JSONDecodeError, TypeError):
                continue
        # Dedupe preserving order
        seen: set[str] = set()
        out: list[str] = []
        for s in seeds:
            if s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= limit:
                break
        return out
