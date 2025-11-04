#!/usr/bin/env python3
"""
PRISM Context Memory Operations

Agent-friendly wrappers for context memory storage.
Analysis is performed by the Claude Code agent using native tools.
This module provides convenient functions for storing and retrieving context.

NOTE: For direct storage operations, use storage.py instead.
"""

import sqlite3
import json
import os
import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import pure storage functions
from storage import (
    store_file_analysis,
    store_pattern,
    store_decision,
    store_interaction,
    recall_query,
    recall_file,
    recall_pattern,
    get_memory_stats as get_stats,
    get_db_connection,
    find_git_root
)


# ============================================================================
# REMEMBER operations (convenient wrappers that call storage functions)
# ============================================================================

def remember_pattern(name: str, description: str, example_path: Optional[str] = None, category: Optional[str] = None) -> bool:
    """Store a reusable code pattern. Wrapper for store_pattern()."""
    return store_pattern(name, description, example_path, category)


def remember_decision(title: str, reasoning: str, context: Optional[str] = None, alternatives: Optional[str] = None) -> bool:
    """Store an architectural decision. Wrapper for store_decision()."""
    return store_decision(title, reasoning, context, alternatives)


def remember_interaction(skill: str, context: str, action: str, outcome: str, learned: str, effectiveness: str = "successful") -> bool:
    """Store agent interaction and learning. Wrapper for store_interaction()."""
    return store_interaction(skill, context, action, outcome, learned, effectiveness)


# ============================================================================
# RECALL operations (wrappers for storage recall functions)
# ============================================================================

# All recall functions are imported from storage.py and re-exported here
# for convenience. Use them directly:
# - recall_query(query, limit)
# - recall_file(path)
# - recall_pattern(name)


def recall_decisions(days: Optional[int] = None) -> List[Dict]:
    """Get architectural decisions, optionally filtered by timeframe."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM decisions
                WHERE status = 'active' AND decision_date >= ?
                ORDER BY decision_date DESC
            """, (cutoff.isoformat(),))
        else:
            cursor.execute("""
                SELECT * FROM decisions
                WHERE status = 'active'
                ORDER BY decision_date DESC
            """)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


def remember_file(file_path: str, summary: str = None, purpose: str = None,
                  complexity: str = None, note: str = None) -> bool:
    """
    Store file analysis. Can be called with full analysis or minimal metadata.

    For full analysis, provide summary, purpose, and complexity.
    For minimal capture (from hooks), just provide file_path.

    Args:
        file_path: Path to file
        summary: One-sentence summary (optional - will be generated if missing)
        purpose: Main purpose (optional - will be generated if missing)
        complexity: 'simple', 'moderate', or 'complex' (optional)
        note: Additional notes (e.g., "Modified via Edit")

    Returns:
        True if successful
    """
    import os

    # Check if file exists
    if not os.path.exists(file_path):
        return False

    # Detect language from extension
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.jsx': 'javascript', '.tsx': 'typescript', '.rb': 'ruby',
        '.go': 'go', '.rs': 'rust', '.java': 'java', '.cs': 'csharp',
        '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.hpp': 'cpp',
        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin'
    }

    ext = os.path.splitext(file_path)[1].lower()
    language = ext_map.get(ext, 'unknown')

    # Count lines
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = len(f.readlines())
    except:
        lines = 0

    # Use provided values or defaults
    summary = summary or f"File: {os.path.basename(file_path)}"
    purpose = purpose or "Pending analysis"
    complexity = complexity or "moderate"

    if note:
        summary = f"{summary} ({note})"

    # Store in database
    return store_file_analysis(
        file_path=file_path,
        summary=summary,
        purpose=purpose,
        complexity=complexity,
        language=language,
        lines_of_code=lines,
        dependencies=[],
        functions=None
    )


def get_memory_stats() -> Dict:
    """Get statistics about stored memory. Wrapper for storage.get_memory_stats()."""
    return get_stats()


if __name__ == "__main__":
    # Test operations
    print("🧠 Testing memory operations...")
    print(get_memory_stats())
