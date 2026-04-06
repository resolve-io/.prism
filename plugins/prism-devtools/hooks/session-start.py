#!/usr/bin/env python3
"""SessionStart hook — bootstrap Brain and redirect auto-memory.

Fires at the start of every Claude Code session. Responsibilities:
1. Ensure .prism/brain/memory/ directory exists (auto-memory target).
2. Seed MEMORY.md pointer file if absent (Slavka pattern).
3. Run Brain.incremental_reindex() to stay current with git changes.
4. Inject a system context note about Brain availability.

CLAUDE_CODE_AUTO_MEMORY_PATH should be set to .prism/brain/memory/ in the
project's environment or shell profile so Claude Code routes auto-memory
writes to this directory (which is indexed by Brain on each session start).
"""

import json
import os
import sys
from pathlib import Path


_MEMORY_NOTE = """# Brain Knowledge Base

Brain is your primary memory for this project. Use it before reading unfamiliar
files or making assumptions about architecture.

## How to query Brain

Before editing an unfamiliar module:
  Use /brain search "module name or concept"

Brain indexes: source code, git commits, story files, Mulch expertise records,
and overstory session logs. Results are ranked by BM25 + vector similarity + graph.

## Where to persist learnings

- **Short observations** (conventions, pitfalls, patterns): append a bullet to
  this file under ## Session Notes.
- **Structured knowledge** (confirmed patterns, decisions, failures): use
  `mulch record <domain> --type <convention|pattern|failure|decision> --description "..."`
  This makes learnings searchable for ALL future agents via Brain.

## Session Notes

"""

_MEMORY_FILENAME = "MEMORY.md"
_MEMORY_DIR = Path(".prism/brain/memory")


def _find_project_root() -> Path:
    """Anchor to git root; fall back to cwd."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def _load_brain():
    hooks_dir = str(Path(__file__).resolve().parent)
    if hooks_dir not in sys.path:
        sys.path.insert(0, hooks_dir)
    from brain_engine import Brain
    return Brain


def _ensure_memory_dir(project_root: Path) -> Path:
    """Create .prism/brain/memory/ and seed MEMORY.md if absent."""
    mem_dir = project_root / _MEMORY_DIR
    mem_dir.mkdir(parents=True, exist_ok=True)
    mem_file = mem_dir / _MEMORY_FILENAME
    if not mem_file.exists():
        mem_file.write_text(_MEMORY_NOTE, encoding="utf-8")
    return mem_dir


def _run_reindex(project_root: Path) -> int:
    """Run Brain incremental reindex; return count of reindexed files."""
    try:
        orig_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            Brain = _load_brain()
            brain = Brain()
            return brain.incremental_reindex()
        finally:
            os.chdir(orig_cwd)
    except Exception:
        return 0


def _brain_doc_count(project_root: Path) -> int:
    """Return number of indexed documents; 0 on error."""
    try:
        orig_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            Brain = _load_brain()
            brain = Brain()
            row = brain._brain.execute("SELECT COUNT(*) FROM docs").fetchone()
            return row[0] if row else 0
        finally:
            os.chdir(orig_cwd)
    except Exception:
        return 0


def main():
    project_root = _find_project_root()

    # 1. Ensure auto-memory directory and seed pointer file
    mem_dir = _ensure_memory_dir(project_root)
    mem_path = mem_dir / _MEMORY_FILENAME
    # Relative path for display
    try:
        rel_mem = str(mem_path.relative_to(project_root))
    except ValueError:
        rel_mem = str(mem_path)

    # 2. Incremental reindex (fail silently)
    reindexed = _run_reindex(project_root)

    # 3. Count indexed docs for context note
    doc_count = _brain_doc_count(project_root)

    # 4. Output system context note
    reindex_note = f" ({reindexed} files reindexed)" if reindexed else ""
    msg = (
        f"Brain knowledge base ready: {doc_count} docs indexed{reindex_note}. "
        f"Auto-memory target: {rel_mem}. "
        "Query Brain before reading unfamiliar modules. "
        "Record structured learnings with `mulch record`."
    )
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
