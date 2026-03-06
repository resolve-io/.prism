#!/usr/bin/env python3
"""
remember: Persist an observation to Mulch expertise with auto-classification.

Usage: python3 remember.py <observation text...>

Example:
    python3 remember.py hooks always wrap DB ops in try/except
    python3 remember.py brain auto-bootstraps when docs table is empty
"""

import subprocess
import sys


# ── Classification ────────────────────────────────────────────────────────────

_DOMAIN_RULES: list[tuple[list[str], str]] = [
    (["hook", "stop hook", "activity hook", "posttooluse"], "hooks"),
    (["brain", "scores.db", "graph", "vector", "brain_engine"], "brain"),
    (["cli", "tui", "snapshot", "dashboard"], "cli"),
    (["conductor", "psp", "epsilon"], "conductor"),
    (["skill", "skill.md", "byos"], "byos"),
    (["wsl", "linux", "windows", "cross-platform"], "platform"),
]

_TYPE_RULES: list[tuple[list[str], str]] = [
    (["always", "never", "must", "should"], "convention"),
    (["pattern", "approach", "technique", "how to"], "pattern"),
    (["failed", "broke", "crash", "bug", "error"], "failure"),
    (["decided", "chose", "because", "tradeoff"], "decision"),
]


def classify_domain(observation: str) -> str:
    """Return a Mulch domain name inferred from the observation text."""
    lower = observation.lower()
    for keywords, domain in _DOMAIN_RULES:
        if any(kw in lower for kw in keywords):
            return domain
    return "general"


def classify_type(observation: str) -> str:
    """Return a Mulch record type inferred from the observation text."""
    lower = observation.lower()
    for keywords, record_type in _TYPE_RULES:
        if any(kw in lower for kw in keywords):
            return record_type
    return "pattern"


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]

    if not args:
        print("Usage: remember.py <observation text...>", file=sys.stderr)
        print("Example: remember.py hooks always wrap DB ops in try/except", file=sys.stderr)
        return 1

    observation = " ".join(args)
    domain = classify_domain(observation)
    record_type = classify_type(observation)

    cmd = [
        "ml", "record", domain,
        "--type", record_type,
        "--description", observation,
        "--classification", "tactical",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print(
            "Error: 'ml' (mulch) command not found. "
            "Install mulch or ensure it is on your PATH.",
            file=sys.stderr,
        )
        return 1

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode

    print(f"Recorded to domain '{domain}' as type '{record_type}':")
    if result.stdout:
        print(result.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
