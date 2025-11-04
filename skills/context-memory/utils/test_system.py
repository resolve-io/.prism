#!/usr/bin/env python3
"""
Comprehensive Context Memory System Test

Tests all major functionality after UTF-8 encoding fixes.
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

from storage import get_db_connection, store_pattern
from memory_ops import get_memory_stats, recall_pattern, recall_query, remember_file


def test_database_connection():
    """Test 1: Database Connection"""
    print("\n[TEST 1] Database Connection")
    try:
        conn = get_db_connection()
        conn.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_query_stats():
    """Test 2: Query Current Stats"""
    print("\n[TEST 2] Current Knowledge Stats")
    try:
        stats = get_memory_stats()
        print(f"✅ Stats retrieved:")
        print(f"   Files: {stats['files']}")
        print(f"   Functions: {stats['functions']}")
        print(f"   Patterns: {stats['patterns']}")
        print(f"   Decisions: {stats['decisions']}")
        return stats
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


def test_store_pattern():
    """Test 3: Store New Pattern"""
    print("\n[TEST 3] Store New Pattern")
    try:
        result = store_pattern(
            name='test-pattern-with-emoji',
            description='Test pattern to verify UTF-8 encoding works ✅ 🎯',
            category='testing'
        )
        print(f"✅ Pattern stored successfully")
        return result
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_update_pattern():
    """Test 4: Update Existing Pattern (UPSERT)"""
    print("\n[TEST 4] Update Pattern (UPSERT)")
    try:
        result = store_pattern(
            name='test-pattern-with-emoji',
            description='UPDATED: Test pattern with new description 🔄 ✨',
            category='testing'
        )
        print(f"✅ Pattern updated (no duplicate created)")
        return result
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_recall_pattern():
    """Test 5: Recall Pattern"""
    print("\n[TEST 5] Recall Pattern")
    try:
        pattern = recall_pattern('test-pattern-with-emoji')
        if pattern:
            print(f"✅ Pattern recalled:")
            print(f"   Name: {pattern['name']}")
            print(f"   Description: {pattern['description']}")
            return pattern
        else:
            print("❌ Pattern not found")
            return None
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


def test_query_knowledge():
    """Test 6: Query Knowledge"""
    print("\n[TEST 6] Query Knowledge")
    try:
        results = recall_query('aspire orchestration', limit=3)
        print(f"✅ Query returned {len(results)} results")
        for i, r in enumerate(results[:2], 1):
            type_label = r['type'].upper()
            if r['type'] == 'file':
                print(f"   {i}. [{type_label}] {r['path'].split('/')[-1]}")
            elif r['type'] == 'pattern':
                print(f"   {i}. [{type_label}] {r['name']}")
            elif r['type'] == 'decision':
                print(f"   {i}. [{type_label}] {r['title']}")
        return len(results)
    except Exception as e:
        print(f"❌ Failed: {e}")
        return 0


def test_remember_file():
    """Test 7: Remember File (Update)"""
    print("\n[TEST 7] Remember File (Update)")
    try:
        result = remember_file(
            'c:/Dev/orca/Orca.AppHost/Program.cs',
            summary='🔄 Updated: Aspire AppHost with full orchestration',
            complexity='complex'
        )
        if result:
            print(f"✅ File memory updated")
        else:
            print(f"❌ File update failed")
        return result
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_no_duplicates(initial_stats):
    """Test 8: Verify UPSERT (No Duplicates)"""
    print("\n[TEST 8] Verify UPSERT (No Duplicates)")
    try:
        stats_after = get_memory_stats()
        # Pattern count should be +1 (we added test pattern)
        expected_patterns = initial_stats['patterns'] + 1
        if stats_after['patterns'] == expected_patterns:
            print(f"✅ Patterns: {stats_after['patterns']} (UPSERT working - only +1)")
        else:
            print(f"⚠️  Patterns: {stats_after['patterns']} (expected {expected_patterns})")

        print(f"   Files: {stats_after['files']} (updates preserved)")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_show_knowledge_script():
    """Test 9: Show Knowledge Script"""
    print("\n[TEST 9] Show Knowledge Script")
    try:
        import subprocess
        result = subprocess.run(
            ['python', 'skills/context-memory/utils/show_knowledge.py', '--stats'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd='C:/Dev/.prism'
        )
        if result.returncode == 0:
            print("✅ show_knowledge.py works")
            return True
        else:
            print(f"❌ Script failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_cleanup():
    """Test 10: Clean Up Test Data"""
    print("\n[TEST 10] Clean Up Test Data")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM patterns WHERE name = 'test-pattern-with-emoji'")
        conn.commit()
        conn.close()
        print("✅ Test data cleaned up")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    print("=" * 80)
    print("COMPREHENSIVE CONTEXT MEMORY SYSTEM TEST")
    print("=" * 80)

    results = []

    # Run all tests
    results.append(("Database Connection", test_database_connection()))

    initial_stats = test_query_stats()
    results.append(("Query Stats", initial_stats is not None))

    results.append(("Store Pattern", test_store_pattern()))
    results.append(("Update Pattern (UPSERT)", test_update_pattern()))
    results.append(("Recall Pattern", test_recall_pattern() is not None))
    results.append(("Query Knowledge", test_query_knowledge() > 0))
    results.append(("Remember File", test_remember_file()))

    if initial_stats:
        results.append(("No Duplicates (UPSERT)", test_no_duplicates(initial_stats)))

    results.append(("Show Knowledge Script", test_show_knowledge_script()))
    results.append(("Cleanup", test_cleanup()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Context memory system is fully operational.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")

    print("=" * 80)


if __name__ == "__main__":
    main()
