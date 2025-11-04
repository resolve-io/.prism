#!/usr/bin/env python3
"""
PRISM Context Memory Database Initialization

Creates and initializes the SQLite database for storing long-term context.
Uses Claude API for generating summaries and analysis.
"""

import sqlite3
import os
import sys
import io
import argparse
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

DB_NAME = ".prism-memory.db"
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


def get_db_path():
    """Get the database path from env or use default in project root."""
    db_path = os.environ.get("PRISM_MEMORY_DB", DB_NAME)

    # If relative path, resolve from git root
    if not os.path.isabs(db_path):
        # Find git root
        git_root = find_git_root()
        if git_root:
            db_path = os.path.join(git_root, db_path)
        else:
            # Fall back to current directory
            db_path = os.path.abspath(db_path)

    return db_path


def find_git_root():
    """Find the git root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def init_database(db_path, rebuild=False):
    """Initialize the database with schema."""

    if rebuild and os.path.exists(db_path):
        print(f"🗑️  Removing existing database: {db_path}")
        os.remove(db_path)

    # Check if database already exists
    exists = os.path.exists(db_path)

    if exists and not rebuild:
        print(f"[OK] Database already exists: {db_path}")
        return

    print(f"[CREATE] Creating database: {db_path}")

    # Read schema
    if not SCHEMA_PATH.exists():
        print(f"[ERROR] Schema file not found: {SCHEMA_PATH}")
        sys.exit(1)

    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()

    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Execute schema
        cursor.executescript(schema_sql)
        conn.commit()
        print("[OK] Database schema created successfully")

        # Add initial metadata
        cursor.execute("""
            INSERT INTO user_preferences (preference_key, preference_value, context, confidence)
            VALUES ('memory_version', '1.0.0', 'PRISM Context Memory System', 10)
        """)
        conn.commit()

        # Show table count
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"[OK] Created {len(tables)} tables")

        # Show stats
        print_stats(cursor)

    except sqlite3.Error as e:
        print(f"[ERROR] Error creating database: {e}")
        sys.exit(1)
    finally:
        conn.close()

    # Add to .gitignore if in git repo
    add_to_gitignore(db_path)

    print(f"\n[SUCCESS] Memory system initialized!")
    print(f"   Database: {db_path}")
    print(f"   Size: {os.path.getsize(db_path)} bytes")


def print_stats(cursor):
    """Print database statistics."""
    print("\n[STATS] Database Statistics:")

    tables = [
        'files', 'functions', 'patterns', 'decisions',
        'interactions', 'git_context', 'loaded_docs',
        'context_chains', 'user_preferences'
    ]

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {table}: {count} records")


def add_to_gitignore(db_path):
    """Add database to .gitignore."""
    git_root = find_git_root()
    if not git_root:
        return

    gitignore_path = os.path.join(git_root, ".gitignore")
    db_name = os.path.basename(db_path)

    # Check if already in gitignore
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            if db_name in f.read():
                print(f"[OK] {db_name} already in .gitignore")
                return

    # Add to gitignore
    with open(gitignore_path, 'a') as f:
        f.write(f"\n# PRISM Context Memory Database\n{db_name}\n")

    print(f"[OK] Added {db_name} to .gitignore")


def verify_database(db_path):
    """Verify database integrity."""
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        if result != "ok":
            print(f"[ERROR] Database integrity check failed: {result}")
            return False

        print(f"[OK] Database integrity: OK")
        print_stats(cursor)

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"[ERROR] Error verifying database: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize PRISM Context Memory Database"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild database (deletes existing)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify database integrity"
    )
    parser.add_argument(
        "--db-path",
        help="Custom database path"
    )

    args = parser.parse_args()

    # Get database path
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = get_db_path()

    print("PRISM Context Memory System")
    print("   Version: 1.0.0")
    print(f"   Database: {db_path}\n")

    if args.verify:
        verify_database(db_path)
    else:
        init_database(db_path, rebuild=args.rebuild)


if __name__ == "__main__":
    main()
