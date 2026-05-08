#!/usr/bin/env python3
"""
prism-pipeline.py — Prism enrichment pipeline.

Chains two phases in sequence:
  Phase 1 (AST):        prism-scan.py    — tree-sitter ingestion + graph_rebuild
  Phase 2 (structural): prism-enrich.py  — regex-based cross-file edge inference

Both phases are free, fast, and idempotent. Run after significant code changes
or before a Barracuda investigation.

Config file: .prism/pipeline.json  (relative to cwd, or --config to override)
CLI flags always override config.

Usage:
    # Normal run:
    python .prism/scripts/prism-pipeline.py

    # Dry run — show what each phase would do without writing:
    python .prism/scripts/prism-pipeline.py --dry-run

    # AST ingest only (skip enrichment):
    python .prism/scripts/prism-pipeline.py --phases ast

    # Enrichment only (re-run after adding patterns, no re-ingest):
    python .prism/scripts/prism-pipeline.py --phases structural

    # Generate a default pipeline.json for this machine:
    python .prism/scripts/prism-pipeline.py --init

Example pipeline.json:
    {
      "repos": [
        "D:/dev/actions.api",
        "D:/dev/actions.manager",
        "D:/dev/express-comm",
        "D:/dev/express-engine",
        "D:/dev/express-executor",
        "D:/dev/express-integrations",
        "D:/dev/express-remote-comm",
        "D:/dev/express-scheduler",
        "D:/dev/express-web-api",
        "D:/dev/express-web-client",
        "D:/dev/orca",
        "D:/dev/resolve.platform.facade"
      ],
      "mcp_server": "prism"
    }
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

DEFAULT_CONFIG = {
    'repos': [],
    'mcp_server': 'prism',
}

PHASE_SCRIPTS = {
    'ast':        SCRIPTS_DIR / 'prism-scan.py',
    'structural': SCRIPTS_DIR / 'prism-enrich.py',
}

PHASE_LABELS = {
    'ast':        'Phase 1 - AST ingest (tree-sitter + graph_rebuild)',
    'structural': 'Phase 2 - Structural enrichment (regex, free)',
}

ALL_PHASES = ['ast', 'structural']


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(config_path) as f:
            on_disk = json.load(f)
        config = dict(DEFAULT_CONFIG)
        config.update(on_disk)
        return config
    except (json.JSONDecodeError, OSError) as e:
        print(f'[warn] Could not read {config_path}: {e}', file=sys.stderr)
        return dict(DEFAULT_CONFIG)


def run_phase(phase: str, repos: list[str], mcp_server: str, dry_run: bool) -> bool:
    script = PHASE_SCRIPTS[phase]
    if not script.exists():
        print(f'  [error] Script not found: {script}', file=sys.stderr)
        return False

    cmd = [sys.executable, str(script), '--repos'] + repos + ['--mcp-server', mcp_server]
    if dry_run:
        cmd.append('--dry-run')

    print(f'\n{"=" * 60}')
    print(f'{PHASE_LABELS[phase]}')
    print(f'{"=" * 60}')

    start = time.monotonic()
    result = subprocess.run(cmd)
    elapsed = time.monotonic() - start

    if result.returncode != 0:
        print(f'\n[error] {phase} phase exited with code {result.returncode}')
        return False

    print(f'\n[{phase}] done in {elapsed:.1f}s')
    return True


def write_default_config(config_path: Path, repos: list[str]) -> None:
    config = {'repos': repos, 'mcp_server': 'prism'}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f'Wrote default config to {config_path}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Prism enrichment pipeline (AST + structural).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--config', metavar='PATH',
                        help='Path to pipeline.json (default: .prism/pipeline.json)')
    parser.add_argument('--repos', nargs='+', metavar='PATH',
                        help='Repo paths (overrides config)')
    parser.add_argument('--phases', nargs='+', choices=ALL_PHASES,
                        help='Phases to run (default: all). Choices: ast, structural')
    parser.add_argument('--mcp-server', metavar='NAME',
                        help='mcp-cli server name (overrides config)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Pass --dry-run to every phase (nothing written)')
    parser.add_argument('--init', action='store_true',
                        help='Write a default pipeline.json and exit')
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else Path('.prism/pipeline.json')
    config = load_config(config_path)

    if args.init:
        repos = args.repos or config.get('repos', [])
        write_default_config(config_path, repos)
        return

    repos = args.repos or config.get('repos', [])
    if not repos:
        print(
            'No repos configured. Either pass --repos or create .prism/pipeline.json.\n'
            'Run with --init to generate a default config.',
            file=sys.stderr,
        )
        sys.exit(1)

    mcp_server = args.mcp_server or config.get('mcp_server', 'prism')
    run_order = args.phases or ALL_PHASES

    print(f'Prism pipeline')
    print(f'  Repos:      {len(repos)}')
    print(f'  Phases:     {", ".join(run_order)}')
    print(f'  MCP server: {mcp_server}')
    if args.dry_run:
        print('  Mode:       DRY RUN')

    total_start = time.monotonic()
    for phase in run_order:
        ok = run_phase(phase, repos, mcp_server, args.dry_run)
        if not ok:
            print(f'\nPipeline aborted at phase: {phase}')
            sys.exit(1)

    total = time.monotonic() - total_start
    print(f'\nPipeline complete in {total:.1f}s')


if __name__ == '__main__':
    main()
