#!/usr/bin/env python3
"""
Update Existing Knowledge Helper

Purpose: Update existing database entries rather than creating new ones
Usage: Run this to update patterns, decisions, or file analyses
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from storage import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_pattern,
    recall_file,
    get_memory_stats
)


def update_file_analysis(file_path: str, **updates):
    """
    Update an existing file analysis.

    Example:
        update_file_analysis(
            'c:/Dev/orca/Program.cs',
            summary='Updated summary after code changes',
            complexity='moderate'  # was 'complex' before
        )
    """
    # Get existing analysis
    existing = recall_file(file_path)

    if not existing:
        print(f"❌ File not in memory: {file_path}")
        print("   Use remember_file() to add it first")
        return False

    # Merge updates with existing data
    data = {
        'file_path': file_path,
        'summary': updates.get('summary', existing.get('summary')),
        'purpose': updates.get('purpose', existing.get('purpose')),
        'complexity': updates.get('complexity', existing.get('complexity')),
        'language': updates.get('language', existing.get('language')),
        'lines_of_code': updates.get('lines_of_code', existing.get('lines_of_code')),
        'dependencies': updates.get('dependencies', existing.get('dependencies', [])),
        'functions': updates.get('functions', existing.get('functions'))
    }

    result = store_file_analysis(**data)

    if result:
        print(f"✓ Updated analysis for {file_path}")

    return result


def update_pattern(name: str, **updates):
    """
    Update an existing pattern.

    Example:
        update_pattern(
            'authentication-flow',
            description='Updated description with new OAuth2 details'
        )
    """
    # Get existing pattern
    existing = recall_pattern(name)

    if not existing:
        print(f"❌ Pattern not found: {name}")
        print("   Use remember_pattern() to add it first")
        return False

    # Store with updates (UPSERT will update)
    result = store_pattern(
        name=name,
        description=updates.get('description', existing.get('description')),
        example_path=updates.get('example_path', existing.get('examples', [None])[0]),
        category=updates.get('category', existing.get('category'))
    )

    if result:
        print(f"✓ Updated pattern: {name}")

    return result


def show_updateable_entries():
    """Show what can be updated."""
    stats = get_memory_stats()

    print("\nUpdateable Knowledge Entries:")
    print(f"   Files: {stats['files']}")
    print(f"   Patterns: {stats['patterns']}")
    print(f"   Decisions: {stats['decisions']}")
    print(f"   Functions: {stats['functions']}")
    print("\nAll entries can be updated using UPSERT operations")
    print("Re-analyzing a file automatically updates its entry\n")


if __name__ == "__main__":
    show_updateable_entries()
