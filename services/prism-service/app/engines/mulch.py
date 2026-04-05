"""Mulch JSONL expertise file I/O."""
import json
from pathlib import Path
from typing import Optional


def read_domain(mulch_dir: Path, domain: str) -> list[dict]:
    """Read all entries from a domain JSONL file."""
    filepath = mulch_dir / f"{domain}.jsonl"
    if not filepath.exists():
        return []
    entries = []
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def write_domain(mulch_dir: Path, domain: str, entries: list[dict]) -> None:
    """Write all entries to a domain JSONL file (full rewrite)."""
    filepath = mulch_dir / f"{domain}.jsonl"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    filepath.write_text("\n".join(lines) + "\n" if lines else "", encoding="utf-8")


def append_entry(mulch_dir: Path, domain: str, entry: dict) -> None:
    """Append a single entry to a domain JSONL file."""
    filepath = mulch_dir / f"{domain}.jsonl"
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_domains(mulch_dir: Path) -> list[str]:
    """List all domain names from .jsonl files."""
    if not mulch_dir.exists():
        return []
    return sorted(
        p.stem for p in mulch_dir.glob("*.jsonl")
    )
