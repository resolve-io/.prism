#!/usr/bin/env python3
"""
Show Knowledge Base Contents

Quick script to view all patterns, decisions, and files in the context memory.
Run anytime to validate what knowledge has been captured.
"""

import sys
import io
from pathlib import Path
import json

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from storage import get_db_connection


def show_patterns():
    """Display all patterns in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("PATTERNS")
    print("=" * 80)

    cursor.execute("SELECT name, description, category, examples FROM patterns ORDER BY category, name")
    patterns = cursor.fetchall()

    current_category = None
    for p in patterns:
        if p['category'] != current_category:
            current_category = p['category']
            print(f"\n[{current_category.upper()}]")

        print(f"\n  {p['name']}")
        print(f"    {p['description']}")
        if p['examples']:
            examples = json.loads(p['examples'])
            if examples:
                print(f"    Example: {examples[0].split('/')[-1]}")

    conn.close()
    return len(patterns)


def show_decisions():
    """Display all active decisions in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("ARCHITECTURAL DECISIONS")
    print("=" * 80)

    cursor.execute("""
        SELECT title, reasoning, context
        FROM decisions
        WHERE status = 'active'
        ORDER BY decision_date DESC
    """)
    decisions = cursor.fetchall()

    for d in decisions:
        print(f"\n  {d['title']}")
        print(f"    Why: {d['reasoning']}")
        if d['context']:
            print(f"    Context: {d['context']}")

    conn.close()
    return len(decisions)


def show_files_summary():
    """Display summary of analyzed files."""
    conn = get_db_connection()
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("FILES ANALYZED")
    print("=" * 80)

    cursor.execute("""
        SELECT path, complexity, lines_of_code, summary
        FROM files
        ORDER BY complexity DESC, lines_of_code DESC
    """)
    files = cursor.fetchall()

    # Group by complexity
    by_complexity = {'complex': [], 'moderate': [], 'simple': []}
    for f in files:
        filename = f['path'].split('/')[-1]
        by_complexity[f['complexity']].append({
            'name': filename,
            'lines': f['lines_of_code'],
            'summary': f['summary']
        })

    for complexity in ['complex', 'moderate', 'simple']:
        if by_complexity[complexity]:
            print(f"\n[{complexity.upper()}]")
            for f in by_complexity[complexity]:
                print(f"  {f['name']} ({f['lines']} lines)")
                print(f"    {f['summary'][:70]}...")

    conn.close()
    return len(files)


def show_stats():
    """Display overall statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}
    for table in ['files', 'functions', 'patterns', 'decisions']:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        stats[table] = cursor.fetchone()['count']

    conn.close()

    print("\n" + "=" * 80)
    print("KNOWLEDGE BASE STATISTICS")
    print("=" * 80)
    print(f"\n  Files:     {stats['files']}")
    print(f"  Functions: {stats['functions']}")
    print(f"  Patterns:  {stats['patterns']}")
    print(f"  Decisions: {stats['decisions']}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Show context memory knowledge base contents')
    parser.add_argument('--patterns', action='store_true', help='Show only patterns')
    parser.add_argument('--decisions', action='store_true', help='Show only decisions')
    parser.add_argument('--files', action='store_true', help='Show only files')
    parser.add_argument('--stats', action='store_true', help='Show only statistics')

    args = parser.parse_args()

    # If no specific flags, show everything
    show_all = not (args.patterns or args.decisions or args.files or args.stats)

    if show_all or args.stats:
        show_stats()

    if show_all or args.patterns:
        count = show_patterns()
        if not show_all:
            print(f"\nTotal: {count} patterns")

    if show_all or args.decisions:
        count = show_decisions()
        if not show_all:
            print(f"\nTotal: {count} decisions")

    if show_all or args.files:
        count = show_files_summary()
        if not show_all:
            print(f"\nTotal: {count} files")

    print("\n" + "=" * 80)
    print()
