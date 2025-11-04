#!/usr/bin/env python3
"""
Migrate PRISM Context Memory from SQLite to Obsidian

Reads all data from SQLite database and converts to Obsidian markdown notes.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import both storage layers
try:
    from storage import (
        get_db_connection,
        find_git_root
    )
    from storage_obsidian import (
        store_file_analysis,
        store_pattern,
        store_decision,
        store_interaction,
        store_git_commit,
        get_vault_path
    )
except ImportError as e:
    print(f"[ERROR] Failed to import storage modules: {e}")
    print("   Ensure both storage.py and storage_obsidian.py exist")
    sys.exit(1)


def migrate_files(conn):
    """Migrate file analyses from SQLite to Obsidian."""
    cursor = conn.cursor()

    print("\n📁 Migrating file analyses...")

    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]

    if total == 0:
        print("  No files to migrate")
        return 0

    cursor.execute("SELECT * FROM files")
    files = cursor.fetchall()

    success = 0
    for file_row in files:
        file_data = dict(file_row)
        file_id = file_data['id']
        file_path = file_data['path']

        # Get functions for this file
        cursor.execute("""
            SELECT name, signature, purpose, complexity
            FROM functions
            WHERE file_id = ?
        """, (file_id,))

        functions = [dict(row) for row in cursor.fetchall()]

        # Parse dependencies
        dependencies = json.loads(file_data.get('dependencies', '[]'))

        # Store in Obsidian
        try:
            result = store_file_analysis(
                file_path=file_path,
                summary=file_data.get('summary', 'N/A'),
                purpose=file_data.get('purpose', 'N/A'),
                complexity=file_data.get('complexity', 'moderate'),
                language=file_data.get('language', 'unknown'),
                lines_of_code=file_data.get('lines_of_code', 0),
                dependencies=dependencies,
                functions=functions if functions else None
            )

            if result:
                success += 1
                print(f"  ✓ {file_path}")
            else:
                print(f"  ✗ {file_path} - Failed")

        except Exception as e:
            print(f"  ✗ {file_path} - Error: {e}")

    print(f"\n  Migrated {success}/{total} files")
    return success


def migrate_patterns(conn):
    """Migrate patterns from SQLite to Obsidian."""
    cursor = conn.cursor()

    print("\n📋 Migrating patterns...")

    cursor.execute("SELECT COUNT(*) FROM patterns")
    total = cursor.fetchone()[0]

    if total == 0:
        print("  No patterns to migrate")
        return 0

    cursor.execute("SELECT * FROM patterns")
    patterns = cursor.fetchall()

    success = 0
    for pattern_row in patterns:
        pattern = dict(pattern_row)

        # Parse examples
        examples = json.loads(pattern.get('examples', '[]'))
        example_path = examples[0] if examples else None

        try:
            result = store_pattern(
                name=pattern['name'],
                description=pattern.get('description', 'N/A'),
                example_path=example_path,
                category=pattern.get('category', 'general')
            )

            if result:
                success += 1
                print(f"  ✓ {pattern['name']}")
            else:
                print(f"  ✗ {pattern['name']} - Failed")

        except Exception as e:
            print(f"  ✗ {pattern['name']} - Error: {e}")

    print(f"\n  Migrated {success}/{total} patterns")
    return success


def migrate_decisions(conn):
    """Migrate decisions from SQLite to Obsidian."""
    cursor = conn.cursor()

    print("\n⚖️  Migrating decisions...")

    cursor.execute("SELECT COUNT(*) FROM decisions")
    total = cursor.fetchone()[0]

    if total == 0:
        print("  No decisions to migrate")
        return 0

    cursor.execute("SELECT * FROM decisions")
    decisions = cursor.fetchall()

    success = 0
    for decision_row in decisions:
        decision = dict(decision_row)

        try:
            result = store_decision(
                title=decision['title'],
                reasoning=decision.get('reasoning', 'N/A'),
                context=decision.get('context'),
                alternatives=decision.get('alternatives_considered')
            )

            if result:
                success += 1
                print(f"  ✓ {decision['title']}")
            else:
                print(f"  ✗ {decision['title']} - Failed")

        except Exception as e:
            print(f"  ✗ {decision['title']} - Error: {e}")

    print(f"\n  Migrated {success}/{total} decisions")
    return success


def migrate_interactions(conn):
    """Migrate interactions from SQLite to Obsidian."""
    cursor = conn.cursor()

    print("\n💡 Migrating interactions...")

    cursor.execute("SELECT COUNT(*) FROM interactions")
    total = cursor.fetchone()[0]

    if total == 0:
        print("  No interactions to migrate")
        return 0

    cursor.execute("SELECT * FROM interactions")
    interactions = cursor.fetchall()

    success = 0
    for interaction_row in interactions:
        interaction = dict(interaction_row)

        try:
            result = store_interaction(
                skill=interaction.get('skill_used', 'unknown'),
                context=interaction.get('context', 'N/A'),
                action=interaction.get('action_taken', 'N/A'),
                outcome=interaction.get('outcome', 'N/A'),
                learned=interaction.get('learned', 'N/A'),
                effectiveness=interaction.get('effectiveness', 'successful')
            )

            if result:
                success += 1
            else:
                print(f"  ✗ Interaction {interaction['id']} - Failed")

        except Exception as e:
            print(f"  ✗ Interaction {interaction['id']} - Error: {e}")

    print(f"\n  Migrated {success}/{total} interactions")
    return success


def migrate_commits(conn):
    """Migrate git commits from SQLite to Obsidian."""
    cursor = conn.cursor()

    print("\n🔀 Migrating git commits...")

    cursor.execute("SELECT COUNT(*) FROM git_context")
    total = cursor.fetchone()[0]

    if total == 0:
        print("  No commits to migrate")
        return 0

    cursor.execute("SELECT * FROM git_context")
    commits = cursor.fetchall()

    success = 0
    for commit_row in commits:
        commit = dict(commit_row)

        # Parse files
        files_changed = 0
        try:
            files = json.loads(commit.get('files_changed', '[]'))
            files_changed = len(files)
        except:
            pass

        try:
            result = store_git_commit(
                commit_hash=commit['commit_hash'],
                author=commit.get('author', 'Unknown'),
                date=commit.get('commit_date', datetime.now().isoformat()),
                message=commit.get('commit_message', 'N/A'),
                files_changed=files_changed,
                insertions=0,  # Not stored in old schema
                deletions=0    # Not stored in old schema
            )

            if result:
                success += 1
            else:
                print(f"  ✗ Commit {commit['commit_hash'][:7]} - Failed")

        except Exception as e:
            print(f"  ✗ Commit {commit['commit_hash'][:7]} - Error: {e}")

    print(f"\n  Migrated {success}/{total} commits")
    return success


def main():
    """Main migration function."""
    print("=" * 70)
    print("PRISM Context Memory: SQLite → Obsidian Migration")
    print("=" * 70)

    # Check if database exists
    db_path = os.environ.get("PRISM_MEMORY_DB", ".prism-memory.db")
    if not os.path.isabs(db_path):
        git_root = find_git_root()
        if git_root:
            db_path = os.path.join(git_root, db_path)

    if not os.path.exists(db_path):
        print(f"\n❌ Database not found: {db_path}")
        print("   Nothing to migrate")
        sys.exit(0)

    print(f"\nSource: {db_path}")

    # Check if vault exists
    vault = get_vault_path()
    print(f"Target: {vault}")

    if not vault.exists():
        print(f"\n❌ Vault not initialized!")
        print("   Run: python skills/context-memory/utils/init_vault.py")
        sys.exit(1)

    # Connect to database
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"\n❌ Failed to connect to database: {e}")
        sys.exit(1)

    print("\nStarting migration...")

    # Migrate each table
    stats = {
        'files': migrate_files(conn),
        'patterns': migrate_patterns(conn),
        'decisions': migrate_decisions(conn),
        'interactions': migrate_interactions(conn),
        'commits': migrate_commits(conn)
    }

    conn.close()

    # Summary
    print("\n" + "=" * 70)
    print("Migration Complete!")
    print("=" * 70)
    print("\nSummary:")
    for category, count in stats.items():
        print(f"  {category}: {count}")

    total = sum(stats.values())
    print(f"\n  Total: {total} items migrated")

    print("\nNext steps:")
    print("1. Open the vault in Obsidian and verify the migrated data")
    print(f"   File → Open vault → {vault}")
    print("2. Update your hooks configuration to use Obsidian hooks:")
    print("   - capture-file-context-obsidian.py")
    print("   - capture-commit-context-obsidian.py")
    print("3. Test the new system with a few file edits")
    print("4. Once verified, you can archive or delete the SQLite database")
    print(f"   Database location: {db_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
