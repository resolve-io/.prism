#!/usr/bin/env python3
"""
Unified Validation Runner
=========================
Runs all PRISM documentation quality checks and produces a single summary.

Checks:
  1. Documentation validation (validate-docs.py) — 6-phase structural scan
  2. Link validation (validate-refs.py) — fast broken-link check
  3. Portability check (check-portability.py) — PC001-PC005 hardcoded paths

Usage:
    python validate-all.py                  # Scan prism-devtools plugin
    python validate-all.py --root /path     # Scan specific directory
    python validate-all.py --help

Exit Codes:
    0 - All checks passed (warnings are OK)
    1 - One or more checks found blocking issues
    2 - Script error
"""
import json
import subprocess
import sys
from pathlib import Path


def find_plugin_dir() -> Path:
    """Walk up from this script to find the prism-devtools plugin root."""
    # This script lives at skills/validate-all/scripts/validate-all.py
    # Plugin root is 4 levels up: scripts/ → validate-all/ → skills/ → plugin root
    return Path(__file__).resolve().parent.parent.parent.parent


def find_script(plugin_dir: Path, name: str) -> Path:
    """Find a script by name within the plugin directory."""
    candidates = [
        plugin_dir / 'scripts' / name,
        plugin_dir / 'skills' / 'validate-markdown-refs' / 'scripts' / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Script not found: {name}")


def run_check(label: str, cmd: list[str]) -> dict:
    """Run a validation command and capture results."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        return {
            'label': label,
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            'label': label,
            'exit_code': 2,
            'stdout': '',
            'stderr': 'Timed out after 120 seconds',
        }
    except Exception as e:
        return {
            'label': label,
            'exit_code': 2,
            'stdout': '',
            'stderr': str(e),
        }


def parse_json_output(stdout: str) -> dict | None:
    """Try to parse JSON from command output."""
    try:
        return json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def print_divider(char: str = '-', width: int = 60):
    print(char * width)


def main():
    plugin_dir = find_plugin_dir()
    scan_root = plugin_dir  # Default: scan the plugin itself

    # Simple --root override
    if '--root' in sys.argv:
        idx = sys.argv.index('--root')
        if idx + 1 < len(sys.argv):
            scan_root = Path(sys.argv[idx + 1]).resolve()

    print(f"PRISM Unified Validation")
    print_divider('=')
    print(f"Scan root: {scan_root}")
    print()

    scripts = {
        'validate-docs.py': find_script(plugin_dir, 'validate-docs.py'),
        'validate-refs.py': find_script(plugin_dir, 'validate-refs.py'),
        'check-portability.py': find_script(plugin_dir, 'check-portability.py'),
    }

    blocked = False
    results = []

    # --- Check 1: Documentation validation ---
    print("[1/3] Documentation validation (6-phase structural scan)")
    r = run_check('Documentation', [
        sys.executable, str(scripts['validate-docs.py']),
        '--root', str(scan_root), '--output', 'nul'
    ])
    results.append(r)
    if r['exit_code'] == 1:
        # Extract critical count from stderr/stdout
        for line in (r['stdout'] + r['stderr']).split('\n'):
            if 'CRITICAL:' in line:
                print(f"  FAIL: {line.strip()}")
                break
        else:
            print("  FAIL: Critical issues found")
        blocked = True
    elif r['exit_code'] == 2:
        print(f"  SKIP: Script error — {r['stderr'][:100]}")
    else:
        print("  PASS")
    print()

    # --- Check 2: Link validation ---
    print("[2/3] Link validation (broken reference check)")
    r = run_check('Links', [
        sys.executable, str(scripts['validate-refs.py']),
        '--project-dir', str(scan_root.parent),
        '--directories', scan_root.name,
    ])
    results.append(r)
    data = parse_json_output(r['stdout'])
    if r['exit_code'] == 1 and data:
        broken = data.get('summary', {}).get('broken_links', '?')
        print(f"  FAIL: {broken} broken links found")
        blocked = True
    elif r['exit_code'] == 1:
        print("  FAIL: Broken links found")
        blocked = True
    elif r['exit_code'] == 2:
        print(f"  SKIP: Script error — {r['stderr'][:100]}")
    else:
        scanned = data.get('summary', {}).get('files_scanned', '?') if data else '?'
        print(f"  PASS ({scanned} files scanned)")
    print()

    # --- Check 3: Portability check ---
    print("[3/3] Portability check (PC001-PC005)")
    r = run_check('Portability', [
        sys.executable, str(scripts['check-portability.py']),
        '--root', str(scan_root)
    ])
    results.append(r)
    data = parse_json_output(r['stdout'])
    if r['exit_code'] == 1 and data:
        errors = data.get('summary', {}).get('errors', '?')
        print(f"  FAIL: {errors} portability errors (PC001-PC003)")
        blocked = True
    elif r['exit_code'] == 1:
        print("  FAIL: Portability errors found")
        blocked = True
    elif r['exit_code'] == 2:
        print(f"  SKIP: Script error — {r['stderr'][:100]}")
    elif data and data.get('status') == 'WARNINGS':
        warnings = data.get('summary', {}).get('warnings', 0)
        print(f"  PASS ({warnings} advisory warnings)")
    else:
        print("  PASS")
    print()

    # --- Summary ---
    print_divider('=')
    if blocked:
        print("RESULT: BLOCKED — issues must be fixed before committing")
        print()
        print("To see full details, run individual checks:")
        print(f"  python {scripts['validate-docs.py'].relative_to(plugin_dir)}")
        print(f"  python {scripts['validate-refs.py'].relative_to(plugin_dir)}")
        print(f"  python {scripts['check-portability.py'].relative_to(plugin_dir)}")
        sys.exit(1)
    else:
        print("RESULT: ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == '__main__':
    main()
