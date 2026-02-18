#!/usr/bin/env python3
"""
Portability Checker
===================
Validates that instruction files, skill definitions, and agent prompts do not
contain hardcoded paths that only work on a specific machine or user.

Implements rules PC001-PC005 from the portability-checker agent definition.

Usage:
    python check-portability.py                  # Scan current directory
    python check-portability.py --root /path     # Scan specific directory
    python check-portability.py --help

Exit Codes:
    0 - PASS (no errors) or WARNINGS only (PC004-PC005)
    1 - FAIL (PC001-PC003 errors found)
    2 - Script error
"""
import json
import sys
import re
import argparse
from pathlib import Path


# --- Configuration -----------------------------------------------------------

FILE_EXTENSIONS = {'.md', '.yaml', '.yml', '.json'}
EXCLUDE_DIRS = {'node_modules', '__pycache__', '.git', 'vendor', 'dist', 'build', 'archive'}

# --- Rule Patterns -----------------------------------------------------------

# PC001: Drive letter in instruction context (e.g. D:\dev\.claude\hooks\)
PC001_PATTERN = re.compile(r'[A-Z]:\\')

# PC002: Hardcoded username path (e.g. C:\Users\DanPuzon\)
PC002_PATTERN = re.compile(r'C:\\Users\\[A-Za-z][A-Za-z0-9._-]+\\')

# PC003: Hardcoded OneDrive org name (e.g. OneDrive - Resolve Systems)
PC003_PATTERN = re.compile(r'OneDrive\s*-\s*[A-Z][A-Za-z\s]+(?:\\|/|")')

# PC004: $env:USERPROFILE with org-specific subdirectory
PC004_PATTERN = re.compile(r'\$env:USERPROFILE[\\\/]OneDrive\s*-\s*\S+')

# PC005: Absolute path where relative would work
# Matches drive-letter paths containing known project-relative segments
PC005_RELATIVE_SEGMENTS = ['.claude', '.prism', 'plugins', 'hooks', 'scripts', 'skills', 'agents']

# --- Exemption Patterns ------------------------------------------------------

# Placeholder tokens that indicate already-parameterized paths
PLACEHOLDER_TOKENS = ['{devRoot}', '{docsRoot}', '{USER}', '{user}', '{username}',
                      '{USERPROFILE}', '{projectRoot}', '{repoRoot}', '{home}']

# Portable environment variable patterns (these ARE the fix, not violations)
PORTABLE_ENV_VARS = re.compile(
    r'\$env:(DEV_ROOT|CLAUDE_PROJECT_DIR|USERPROFILE|HOME|APPDATA|LOCALAPPDATA)'
    r'|\$PWD|\$HOME|\$\{?HOME\}?'
)

# GetFolderPath API calls (the portable alternative)
GETFOLDERPATH_PATTERN = re.compile(r'\[Environment\]::GetFolderPath', re.IGNORECASE)

# Code block fence tags that indicate output/log context
OUTPUT_FENCE_TAGS = {'output', 'log', 'stderr', 'stdout', 'error', 'console'}

# Historical narrative markers
HISTORY_VERB_MARKERS = re.compile(
    r'\b(was|were|had|deleted|recovered|restored|lost|broke|crashed|caused'
    r'|happened|incident|migrated|moved|removed)\b', re.IGNORECASE
)
HISTORY_DATE_PATTERN = re.compile(r'\b20\d{2}-\d{2}(?:-\d{2})?\b')
HISTORY_KEYWORDS = {'incident', 'recovered', 'deleted', 'what happened',
                    'root cause', 'post-mortem', 'postmortem', 'lesson'}

# Section headings that indicate historical/incident documentation
HISTORY_HEADING_KEYWORDS = re.compile(
    r'\b(incident|lesson|evidence|post-?mortem|what happened|root cause'
    r'|recovery|deleted|critical)\b', re.IGNORECASE
)

# Rule documentation pattern (lines describing PC rules, not violating them)
RULE_DOC_PATTERN = re.compile(r'PC00[1-5]')

# Python traceback pattern (error output, not instructions)
PYTHON_TRACEBACK_PATTERN = re.compile(r'^\s*File\s+"[^"]*"')


# --- Exemption Logic ---------------------------------------------------------

def is_in_output_code_block(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a code block tagged as output/log/stderr/stdout."""
    fence_count = 0
    in_output_block = False
    for i in range(line_idx):
        stripped = lines[i].strip()
        if stripped.startswith('```'):
            if fence_count % 2 == 0:
                # Opening fence — check tag
                tag = stripped[3:].strip().lower().split()[0] if stripped[3:].strip() else ''
                in_output_block = tag in OUTPUT_FENCE_TAGS
            else:
                in_output_block = False
            fence_count += 1
    return in_output_block and fence_count % 2 == 1


def is_rule_documentation(line: str) -> bool:
    """Check if a line is documenting PC rules (not violating them)."""
    return bool(RULE_DOC_PATTERN.search(line))


def is_python_traceback(line: str) -> bool:
    """Check if a line looks like a Python traceback (error output)."""
    return bool(PYTHON_TRACEBACK_PATTERN.match(line))


def is_in_historical_section(lines: list[str], line_idx: int) -> bool:
    """Check if any heading in the hierarchy above indicates historical context.

    Forward-scans from the start of the file, tracking code blocks correctly.
    Maintains a heading stack so that a line under '### Rule 6' which is under
    '# Critical Lessons - Incident' is exempt via the parent heading.
    """
    in_code_block = False
    heading_stack: list[tuple[int, str]] = []

    for i in range(line_idx):
        stripped = lines[i].strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith('#'):
            level = len(stripped) - len(stripped.lstrip('#'))
            # Pop headings at same or deeper level (they're siblings/children)
            heading_stack = [(l, t) for l, t in heading_stack if l < level]
            heading_stack.append((level, stripped))

    return any(HISTORY_HEADING_KEYWORDS.search(text) for _, text in heading_stack)


def has_placeholder(line: str) -> bool:
    """Check if line contains placeholder tokens indicating parameterized paths."""
    return any(token in line for token in PLACEHOLDER_TOKENS)


def is_portable_reference(line: str) -> bool:
    """Check if the match is part of a portable env var or API call."""
    if PORTABLE_ENV_VARS.search(line):
        return True
    if GETFOLDERPATH_PATTERN.search(line):
        return True
    return False


def is_historical_context(lines: list[str], line_idx: int, window: int = 5) -> bool:
    """Check if a line is in historical narrative context (5-line window)."""
    start = max(0, line_idx - window)
    end = min(len(lines), line_idx + window + 1)
    window_text = ' '.join(lines[start:end])

    markers_found = 0
    if HISTORY_VERB_MARKERS.search(window_text):
        markers_found += 1
    if HISTORY_DATE_PATTERN.search(window_text):
        markers_found += 1
    if any(kw in window_text.lower() for kw in HISTORY_KEYWORDS):
        markers_found += 1

    return markers_found >= 2


# --- File Discovery ----------------------------------------------------------

def should_exclude(path: Path) -> bool:
    """Check if path is under an excluded directory."""
    return any(part in EXCLUDE_DIRS for part in path.parts)


def find_scannable_files(root: Path) -> list[Path]:
    """Find all files with scannable extensions, excluding ignored directories."""
    files = []
    for ext in FILE_EXTENSIONS:
        for f in root.rglob(f'*{ext}'):
            if not should_exclude(f):
                files.append(f)
    return sorted(files)


# --- Rule Checking -----------------------------------------------------------

def suggest_fix(rule_id: str, line: str) -> str:
    """Generate a portable alternative suggestion for a violation."""
    if rule_id == 'PC001':
        # Try to extract the relative portion
        for seg in PC005_RELATIVE_SEGMENTS:
            idx = line.find(seg)
            if idx != -1:
                return f'Use relative path: {line[idx:].split()[0].split("`")[0]}'
        return 'Replace with relative path from project root'
    if rule_id == 'PC002':
        return '[Environment]::GetFolderPath("MyDocuments") or $env:USERPROFILE'
    if rule_id == 'PC003':
        return '$env:USERPROFILE with dynamic subfolder discovery'
    if rule_id == 'PC004':
        return '[Environment]::GetFolderPath() API instead of hardcoded org subdir'
    if rule_id == 'PC005':
        for seg in PC005_RELATIVE_SEGMENTS:
            idx = line.find(seg)
            if idx != -1:
                relative = line[idx:].split()[0].split('`')[0].rstrip('\\/"\'')
                return f'Use relative path: {relative}'
        return 'Replace absolute path with relative path'
    return ''


def check_line(line: str, lines: list[str], line_idx: int,
               file_path: str, issues: list, exemptions_count: list) -> None:
    """Check a single line against all PC rules, respecting exemptions."""
    # --- Shared exemption checks (apply to all rules) ---
    if has_placeholder(line):
        exemptions_count[0] += 1
        return
    if is_in_output_code_block(lines, line_idx):
        exemptions_count[0] += 1
        return
    if is_rule_documentation(line):
        exemptions_count[0] += 1
        return
    if is_python_traceback(line):
        exemptions_count[0] += 1
        return
    if is_historical_context(lines, line_idx):
        exemptions_count[0] += 1
        return
    if is_in_historical_section(lines, line_idx):
        exemptions_count[0] += 1
        return

    # --- PC002 (most specific, check first) ---
    if PC002_PATTERN.search(line):
        if not is_portable_reference(line):
            issues.append({
                'rule_id': 'PC002',
                'severity': 'Error',
                'file': file_path,
                'line': line_idx + 1,
                'content': line.strip(),
                'fix': suggest_fix('PC002', line)
            })
            return  # PC002 subsumes PC001

    # --- PC003 ---
    if PC003_PATTERN.search(line):
        if not is_portable_reference(line):
            issues.append({
                'rule_id': 'PC003',
                'severity': 'Error',
                'file': file_path,
                'line': line_idx + 1,
                'content': line.strip(),
                'fix': suggest_fix('PC003', line)
            })
            return

    # --- PC004 ---
    if PC004_PATTERN.search(line):
        issues.append({
            'rule_id': 'PC004',
            'severity': 'Warning',
            'file': file_path,
            'line': line_idx + 1,
            'content': line.strip(),
            'fix': suggest_fix('PC004', line)
        })
        return

    # --- PC001 (general drive letter — after PC002/PC005 specifics) ---
    if PC001_PATTERN.search(line):
        if not is_portable_reference(line):
            # Check if this is PC005 (absolute but could be relative)
            is_pc005 = any(seg in line for seg in PC005_RELATIVE_SEGMENTS)
            if is_pc005:
                issues.append({
                    'rule_id': 'PC005',
                    'severity': 'Warning',
                    'file': file_path,
                    'line': line_idx + 1,
                    'content': line.strip(),
                    'fix': suggest_fix('PC005', line)
                })
            else:
                issues.append({
                    'rule_id': 'PC001',
                    'severity': 'Error',
                    'file': file_path,
                    'line': line_idx + 1,
                    'content': line.strip(),
                    'fix': suggest_fix('PC001', line)
                })


# --- Main Scanner ------------------------------------------------------------

def scan_files(root: Path) -> dict:
    """Scan all files under root and return structured results."""
    files = find_scannable_files(root)
    all_issues: list[dict] = []
    file_exemptions: dict[str, int] = {}
    exemptions_total = [0]  # mutable counter for pass-by-ref into check_line

    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            try:
                content = file_path.read_text(encoding='latin-1')
            except Exception:
                continue

        lines = content.split('\n')
        pre_count = exemptions_total[0]

        try:
            rel_path = str(file_path.relative_to(root)).replace('\\', '/')
        except ValueError:
            rel_path = str(file_path)

        for idx, line in enumerate(lines):
            check_line(line, lines, idx, rel_path, all_issues, exemptions_total)

        file_exempted = exemptions_total[0] - pre_count
        if file_exempted > 0:
            file_exemptions[rel_path] = file_exempted

    errors = sum(1 for i in all_issues if i['severity'] == 'Error')
    warnings = sum(1 for i in all_issues if i['severity'] == 'Warning')

    if errors > 0:
        status = 'FAIL'
    elif warnings > 0:
        status = 'WARNINGS'
    else:
        status = 'PASS'

    exemption_list = [
        {'file': f, 'reason': 'Matched exemption criteria', 'lines_skipped': count}
        for f, count in file_exemptions.items()
    ]

    return {
        'status': status,
        'summary': {
            'files_scanned': len(files),
            'issues_found': len(all_issues),
            'errors': errors,
            'warnings': warnings,
            'exemptions_applied': exemptions_total[0]
        },
        'issues': all_issues,
        'exemptions': exemption_list
    }


# --- CLI Entry Point ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Check PRISM files for hardcoded paths that break portability.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=Path('.').resolve(),
        help='Root directory to scan (default: current directory)'
    )

    args = parser.parse_args()

    try:
        result = scan_files(args.root.resolve())
        print(json.dumps(result, indent=2))

        if result['status'] == 'FAIL':
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        error_result = {
            'status': 'ERROR',
            'error': str(e),
            'summary': {},
            'issues': [],
            'exemptions': []
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(2)


if __name__ == '__main__':
    main()
