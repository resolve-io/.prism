#!/usr/bin/env python3
"""
PRISM Context Memory - Pure Storage Layer

This module ONLY handles database storage operations.
Analysis is done by the Claude Code agent, not here.

Architecture:
- Agent analyzes files/code (using native Read/Grep tools)
- Agent calls these storage functions to persist results
- No AI/LLM calls in this module - pure data storage
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys


def get_db_connection():
    """Get database connection."""
    db_path = os.environ.get("PRISM_MEMORY_DB", ".prism-memory.db")

    # Resolve relative paths from git root
    if not os.path.isabs(db_path):
        git_root = find_git_root()
        if git_root:
            db_path = os.path.join(git_root, db_path)

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        print("   Run: python .prism/skills/context-memory/utils/init_db.py")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def find_git_root():
    """Find git root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


# ============================================================================
# STORE operations (Agent provides analyzed data, we just store it)
# ============================================================================

def store_file_analysis(
    file_path: str,
    summary: str,
    purpose: str,
    complexity: str,
    language: str,
    lines_of_code: int,
    dependencies: List[str],
    functions: List[Dict[str, str]] = None
) -> bool:
    """
    Store file analysis results.

    NOTE: Agent does the analysis, this function just stores the results.

    Args:
        file_path: Path to file
        summary: One-sentence summary (from agent analysis)
        purpose: Main purpose (from agent analysis)
        complexity: 'simple', 'moderate', or 'complex'
        language: Programming language
        lines_of_code: Number of lines
        dependencies: List of imported files/modules
        functions: List of function analyses [{name, signature, purpose, complexity}, ...]

    Returns:
        True if successful
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Upsert file
        cursor.execute("""
            INSERT INTO files (path, language, summary, purpose, complexity, lines_of_code, dependencies)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                language = excluded.language,
                summary = excluded.summary,
                purpose = excluded.purpose,
                complexity = excluded.complexity,
                lines_of_code = excluded.lines_of_code,
                dependencies = excluded.dependencies,
                last_analyzed = CURRENT_TIMESTAMP
        """, (
            file_path,
            language,
            summary,
            purpose,
            complexity,
            lines_of_code,
            json.dumps(dependencies)
        ))

        file_id = cursor.lastrowid or cursor.execute("SELECT id FROM files WHERE path = ?", (file_path,)).fetchone()[0]

        # Store functions if provided
        if functions:
            # Clear old functions
            cursor.execute("DELETE FROM functions WHERE file_id = ?", (file_id,))

            # Insert new functions
            for func in functions:
                cursor.execute("""
                    INSERT INTO functions (file_id, name, signature, purpose, complexity)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    file_id,
                    func.get('name', ''),
                    func.get('signature', ''),
                    func.get('purpose', ''),
                    func.get('complexity', 'moderate')
                ))

        conn.commit()
        print(f"[OK] Stored analysis for {file_path}")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def store_pattern(name: str, description: str, example_path: Optional[str] = None, category: Optional[str] = None) -> bool:
    """
    Store a reusable code pattern.

    Args:
        name: Pattern name
        description: What the pattern does (from agent analysis)
        example_path: Optional example file path
        category: Optional category (e.g., 'authentication', 'error-handling')
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        examples = [example_path] if example_path else []

        cursor.execute("""
            INSERT INTO patterns (name, description, category, examples, usage_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(name) DO UPDATE SET
                description = excluded.description,
                category = excluded.category,
                usage_count = usage_count + 1,
                updated_at = CURRENT_TIMESTAMP
        """, (name, description, category, json.dumps(examples)))

        conn.commit()
        print(f"[OK] Stored pattern: {name}")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    finally:
        conn.close()


def store_decision(title: str, reasoning: str, context: Optional[str] = None, alternatives: Optional[str] = None) -> bool:
    """
    Store an architectural decision.

    Args:
        title: Decision title
        reasoning: Why this decision was made (from agent analysis)
        context: Background context
        alternatives: Alternatives that were considered
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO decisions (title, reasoning, context, alternatives_considered)
            VALUES (?, ?, ?, ?)
        """, (title, reasoning, context, alternatives))

        conn.commit()
        print(f"[OK] Stored decision: {title}")
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    finally:
        conn.close()


def store_interaction(skill: str, context: str, action: str, outcome: str, learned: str, effectiveness: str = "successful") -> bool:
    """
    Store agent interaction and learning.

    Args:
        skill: Skill/command used
        context: What was the situation
        action: What action was taken
        outcome: What happened
        learned: What did we learn
        effectiveness: 'successful', 'partial', 'failed'
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO interactions (skill_used, context, action_taken, outcome, learned, effectiveness)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (skill, context, action, outcome, learned, effectiveness))

        conn.commit()
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Database error: {e}")
        return False
    finally:
        conn.close()


# ============================================================================
# RECALL operations (retrieving stored context)
# ============================================================================

def recall_query(query: str, limit: int = 10) -> List[Dict]:
    """
    Full-text search across files, patterns, and decisions.

    Returns list of results with type and relevance.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    results = []

    # Sanitize query for FTS5 - remove special characters that cause syntax errors
    # FTS5 uses ? and - as special characters
    # Convert hyphens to spaces to handle "real-time" -> "real time"
    sanitized_query = query.replace('?', '').replace('"', '').replace('-', ' ').strip()
    if not sanitized_query:
        return results

    try:
        # Search files
        cursor.execute("""
            SELECT f.id, f.path, f.summary, f.purpose, f.complexity, f.last_analyzed,
                   rank AS relevance
            FROM files_fts
            JOIN files f ON files_fts.rowid = f.id
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (sanitized_query, limit))

        for row in cursor.fetchall():
            results.append({
                'type': 'file',
                'path': row['path'],
                'summary': row['summary'],
                'purpose': row['purpose'],
                'complexity': row['complexity'],
                'last_analyzed': row['last_analyzed'],
                'relevance': row['relevance']
            })

        # Search patterns
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.category, p.examples, p.usage_count,
                   rank AS relevance
            FROM patterns_fts
            JOIN patterns p ON patterns_fts.rowid = p.id
            WHERE patterns_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (sanitized_query, limit))

        for row in cursor.fetchall():
            results.append({
                'type': 'pattern',
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'examples': json.loads(row['examples']) if row['examples'] else [],
                'usage_count': row['usage_count'],
                'relevance': row['relevance']
            })

        # Search decisions
        cursor.execute("""
            SELECT d.id, d.title, d.reasoning, d.context, d.decision_date, d.status,
                   rank AS relevance
            FROM decisions_fts
            JOIN decisions d ON decisions_fts.rowid = d.id
            WHERE decisions_fts MATCH ? AND d.status = 'active'
            ORDER BY rank
            LIMIT ?
        """, (sanitized_query, limit))

        for row in cursor.fetchall():
            results.append({
                'type': 'decision',
                'title': row['title'],
                'reasoning': row['reasoning'],
                'context': row['context'],
                'decision_date': row['decision_date'],
                'status': row['status'],
                'relevance': row['relevance']
            })

        # Sort by relevance
        results.sort(key=lambda x: x.get('relevance', 0))

        return results[:limit]

    finally:
        conn.close()


def recall_file(path: str) -> Optional[Dict]:
    """Get detailed information about a specific file."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM files WHERE path = ?
        """, (path,))

        row = cursor.fetchone()
        if not row:
            return None

        file_data = dict(row)

        # Get functions
        cursor.execute("""
            SELECT name, signature, purpose, complexity
            FROM functions
            WHERE file_id = ?
        """, (file_data['id'],))

        file_data['functions'] = [dict(r) for r in cursor.fetchall()]
        file_data['dependencies'] = json.loads(file_data.get('dependencies', '[]'))

        return file_data

    finally:
        conn.close()


def recall_pattern(name: str) -> Optional[Dict]:
    """Get detailed information about a specific pattern."""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM patterns WHERE name = ?
        """, (name,))

        row = cursor.fetchone()
        if not row:
            return None

        pattern_data = dict(row)
        pattern_data['examples'] = json.loads(pattern_data.get('examples', '[]'))

        return pattern_data

    finally:
        conn.close()


def get_memory_stats() -> Dict:
    """Get statistics about stored memory."""
    conn = get_db_connection()
    cursor = conn.cursor()

    stats = {}

    try:
        tables = ['files', 'functions', 'patterns', 'decisions', 'interactions', 'git_context']

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

        # Get database size
        db_path = os.environ.get("PRISM_MEMORY_DB", ".prism-memory.db")
        if not os.path.isabs(db_path):
            git_root = find_git_root()
            if git_root:
                db_path = os.path.join(git_root, db_path)

        if os.path.exists(db_path):
            stats['database_size_mb'] = round(os.path.getsize(db_path) / (1024 * 1024), 2)

        return stats

    finally:
        conn.close()


if __name__ == "__main__":
    # Test connection and show stats
    print("Context Memory Storage")
    print("=" * 50)
    try:
        stats = get_memory_stats()
        print("\nMemory Stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print("\n[OK] Storage layer is operational")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
