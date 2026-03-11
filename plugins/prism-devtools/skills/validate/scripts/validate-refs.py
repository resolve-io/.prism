#!/usr/bin/env python3
"""
Markdown Reference Validator
============================
Validates markdown file references in .claude and .prism directories.
Returns clean JSON output for programmatic use.

Usage:
    python validate-refs.py                    # Scan default directories
    python validate-refs.py --directories .claude .prism
    python validate-refs.py --include-archive  # Include archive directories
    python validate-refs.py --help

Exit Codes:
    0 - No broken links found
    1 - Broken links found
    2 - Script error
"""
import json
import sys
import os
import re
import argparse
from pathlib import Path

# Default configuration
DEFAULT_DIRECTORIES = ['.claude', '.prism']
EXCLUDE_PATTERNS = ['node_modules', '__pycache__', '.git', 'vendor', 'dist', 'build', 'archive', 'plugins/cache']

# Template detection patterns
TEMPLATE_FILE_PATTERNS = [r'template', r'example', r'sample', r'scaffold', r'boilerplate']
TEMPLATE_MARKERS = ['{{', '${', '<%', '{%', '<!-- TODO', '[PLACEHOLDER]', '[TODO]']

# Plugin cache path pattern for deduplication
PLUGIN_CACHE_PATTERN = re.compile(r'plugins[/\\]cache[/\\]([^/\\]+)[/\\]([^/\\]+)[/\\]([^/\\]+)[/\\](.*)')


def normalize_plugin_path(file_path: Path, base_dir: Path) -> tuple:
    """Extract normalized plugin identifier for deduplication."""
    path_str = str(file_path).replace('\\', '/')

    cache_match = PLUGIN_CACHE_PATTERN.search(path_str)
    if cache_match:
        namespace, plugin_name, version, rel_path = cache_match.groups()
        return plugin_name, rel_path.replace('\\', '/')

    try:
        rel_to_base = file_path.relative_to(base_dir)
        parts = rel_to_base.parts

        if 'plugins' in parts:
            plugins_idx = parts.index('plugins')
            if plugins_idx + 1 < len(parts):
                plugin_name = parts[plugins_idx + 1]
                rel_path = str(Path(*parts[plugins_idx + 2:])) if plugins_idx + 2 < len(parts) else ""
                return plugin_name, rel_path.replace('\\', '/')

        return base_dir.name, str(rel_to_base).replace('\\', '/')
    except ValueError:
        return "unknown", path_str


def is_template_file(file_path: Path, content: str) -> bool:
    """Detect if a file is a template based on name and content."""
    path_lower = str(file_path).lower()
    has_template_name = any(re.search(p, path_lower) for p in TEMPLATE_FILE_PATTERNS)
    if not has_template_name:
        return False
    return any(marker in content for marker in TEMPLATE_MARKERS)


def is_template_sibling_link(ref_path: str) -> bool:
    """Check if a link is a simple sibling reference in a template."""
    if ref_path.startswith(('..', '/', '\\')):
        return False
    ref_path_clean = ref_path.lstrip('./')
    return '/' not in ref_path_clean and '\\' not in ref_path_clean


def should_exclude(path: Path, include_archive: bool) -> bool:
    """Check if path should be excluded from scanning."""
    path_str = str(path)
    patterns = EXCLUDE_PATTERNS.copy()
    if include_archive and 'archive' in patterns:
        patterns.remove('archive')
    return any(excluded in path_str for excluded in patterns)


def find_md_files(base_dir: Path, include_archive: bool) -> list:
    """Find all markdown files in directory."""
    md_files = []
    for pattern in ['**/*.md', '**/*.MD']:
        for f in base_dir.glob(pattern):
            if not should_exclude(f, include_archive):
                md_files.append(f)
    return md_files


def is_valid_file_path(path: str) -> bool:
    """Check if string looks like a valid file path reference."""
    if not path or len(path) < 2:
        return False
    if any(c in path for c in ['(', ')', '{', '}', '=', ';', ',']):
        return False
    if '/' not in path and '\\' not in path and '.' not in path:
        return False
    if not re.search(r'\.\w+$', path) and not path.endswith('/'):
        return False
    return True


def extract_references(content: str, file_path: Path) -> list:
    """Extract file references from markdown content."""
    refs = []
    lines = content.split('\n')
    in_fenced_block = False

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith('```'):
            in_fenced_block = not in_fenced_block
            continue

        if in_fenced_block:
            continue

        if line.startswith('    ') and not stripped.startswith(('-', '*', '1')):
            continue

        # Standard markdown links
        for match in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', line):
            link_text, link_path = match.groups()
            link_path = link_path.split('#')[0].strip()
            if link_path.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            if is_valid_file_path(link_path):
                refs.append({
                    'file': str(file_path),
                    'line': line_num,
                    'text': link_text,
                    'path': link_path
                })

        # Reference-style links
        for match in re.finditer(r'^\[([^\]]+)\]:\s*(\S+)', line):
            ref_name, ref_path = match.groups()
            ref_path = ref_path.split('#')[0].strip()
            if ref_path.startswith(('http://', 'https://', '#')):
                continue
            if is_valid_file_path(ref_path):
                refs.append({
                    'file': str(file_path),
                    'line': line_num,
                    'text': ref_name,
                    'path': ref_path
                })

    return refs


def resolve_path(ref_path: str, source_file: Path, project_dir: Path) -> Path:
    """Resolve a reference path relative to its source file."""
    ref_path = ref_path.strip()
    if ref_path.startswith('/'):
        return project_dir / ref_path.lstrip('/')
    return (source_file.parent / ref_path).resolve()


def get_directories_to_scan(project_dir: Path, directories: list) -> list:
    """Get all directories to scan with labels."""
    dirs = []
    for subdir in directories:
        path = project_dir / subdir
        if path.exists():
            dirs.append((path, f"project:{subdir}"))

    # NOTE: We intentionally do NOT scan user-level ~/.claude here.
    # This is a PRISM quality gate — it only validates project-level content
    # that will be checked in. The session-start hook handles user-level scanning.

    return dirs


def validate_references(project_dir: Path, directories: list, include_archive: bool) -> dict:
    """Validate all markdown references and return results."""
    seen_errors = {}
    warnings = []
    scanned_locations = []

    stats = {
        'files_scanned': 0,
        'total_refs_checked': 0,
        'broken_before_dedup': 0,
        'template_filtered': 0,
        'duplicates_removed': 0,
        'broken_links': 0,
        'valid_links': 0,
    }

    plugin_dirs = get_directories_to_scan(project_dir, directories)

    for target_dir, label in plugin_dirs:
        scanned_locations.append(f"{label} ({target_dir})")
        md_files = find_md_files(target_dir, include_archive)

        for md_file in md_files:
            stats['files_scanned'] += 1

            try:
                content = md_file.read_text(encoding='utf-8')
            except Exception as e:
                warnings.append(f"Cannot read {md_file}: {e}")
                continue

            file_is_template = is_template_file(md_file, content)
            refs = extract_references(content, md_file)

            for ref in refs:
                if not ref['path']:
                    continue

                stats['total_refs_checked'] += 1
                resolved = resolve_path(ref['path'], md_file, target_dir)

                if not resolved.exists():
                    stats['broken_before_dedup'] += 1

                    if file_is_template and is_template_sibling_link(ref['path']):
                        stats['template_filtered'] += 1
                        continue

                    try:
                        rel_source = md_file.relative_to(target_dir)
                        display_path = f"{rel_source}"
                    except ValueError:
                        display_path = str(md_file)

                    plugin_id, plugin_rel_path = normalize_plugin_path(md_file, target_dir)
                    dedup_key = f"{plugin_id}:{plugin_rel_path}:{ref['line']}:{ref['path']}"

                    if dedup_key in seen_errors:
                        stats['duplicates_removed'] += 1
                    else:
                        seen_errors[dedup_key] = {
                            'source_file': display_path,
                            'line': ref['line'],
                            'link_text': ref['text'],
                            'target_path': ref['path'],
                            'resolved_path': str(resolved),
                            'error': 'File not found'
                        }
                else:
                    stats['valid_links'] += 1

    broken_links = list(seen_errors.values())
    stats['broken_links'] = len(broken_links)

    return {
        'status': 'PASS' if len(broken_links) == 0 else 'FAIL',
        'summary': stats,
        'broken_links': broken_links,
        'scanned_locations': scanned_locations,
        'warnings': warnings
    }


def main():
    parser = argparse.ArgumentParser(
        description='Validate markdown file references in Claude Code plugins.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--directories', '-d',
        nargs='+',
        default=DEFAULT_DIRECTORIES,
        help=f'Directories to scan (default: {DEFAULT_DIRECTORIES})'
    )
    parser.add_argument(
        '--include-archive',
        action='store_true',
        help='Include archive directories in scan'
    )
    parser.add_argument(
        '--project-dir', '-p',
        type=Path,
        default=Path(os.environ.get('CLAUDE_PROJECT_DIR', '.')).resolve(),
        help='Project root directory (default: CLAUDE_PROJECT_DIR or current dir)'
    )

    args = parser.parse_args()

    try:
        result = validate_references(
            project_dir=args.project_dir,
            directories=args.directories,
            include_archive=args.include_archive
        )

        print(json.dumps(result, indent=2))

        sys.exit(0 if result['status'] == 'PASS' else 1)

    except Exception as e:
        error_result = {
            'status': 'ERROR',
            'error': str(e),
            'summary': {},
            'broken_links': [],
            'scanned_locations': [],
            'warnings': []
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(2)


if __name__ == '__main__':
    main()
