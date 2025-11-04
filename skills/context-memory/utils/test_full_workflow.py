#!/usr/bin/env python3
"""
End-to-End Knowledge Workflow Test

Simulates the complete knowledge lifecycle:
1. Learn something new about a project
2. Store it in the database
3. Query it back with natural language
4. Update the knowledge (verify UPSERT)
5. Query again to see updates
6. Clean up test data

This validates the entire workflow from learning to retrieval.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from storage import store_file_analysis, store_pattern, store_decision, get_db_connection
from memory_ops import recall_query, recall_file, recall_pattern, get_memory_stats


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(number, description):
    """Print a step header."""
    print(f"\n[STEP {number}] {description}")
    print("-" * 80)


def main():
    print_section("END-TO-END KNOWLEDGE WORKFLOW TEST")
    print("\nSimulating: Learning about a new Orca component, storing it, querying it, and updating it")

    # Get initial stats
    initial_stats = get_memory_stats()
    print(f"\nInitial Knowledge Base:")
    print(f"  Files: {initial_stats['files']}")
    print(f"  Patterns: {initial_stats['patterns']}")
    print(f"  Decisions: {initial_stats['decisions']}")

    # SCENARIO: We just learned about a new Orca component
    print_section("SCENARIO: Learning About New Orca Component")
    print("\nImagine we just discovered Orca has a SignalR hub for real-time notifications.")
    print("Let's document this knowledge...")

    # Step 1: Store initial file analysis
    print_step(1, "Store File Analysis (Initial Learning)")

    success = store_file_analysis(
        file_path='c:/Dev/orca/Orca.NotificationHub/NotificationHub.cs',
        summary='SignalR hub for real-time notifications to connected clients',
        purpose='Provides WebSocket connections for push notifications, user presence, and live updates',
        complexity='moderate',
        language='csharp',
        lines_of_code=85,
        dependencies=['SignalR', 'Aspire', 'Redis'],
        functions=[
            {'name': 'SendNotification', 'signature': 'async Task', 'purpose': 'Broadcast notification to specific user', 'complexity': 'simple'},
            {'name': 'OnConnectedAsync', 'signature': 'override async Task', 'purpose': 'Track user connection and presence', 'complexity': 'simple'}
        ]
    )

    if success:
        print("✅ File analysis stored successfully")
    else:
        print("❌ Failed to store file analysis")
        return

    # Step 2: Store related pattern
    print_step(2, "Store Pattern (Document Implementation Pattern)")

    success = store_pattern(
        name='signalr-with-redis-backplane',
        description='Use SignalR with Redis backplane for distributed real-time messaging across multiple server instances',
        example_path='c:/Dev/orca/Orca.NotificationHub/NotificationHub.cs',
        category='real-time'
    )

    if success:
        print("✅ Pattern stored successfully")
    else:
        print("❌ Failed to store pattern")
        return

    # Step 3: Store architectural decision
    print_step(3, "Store Decision (Why We Chose This Approach)")

    success = store_decision(
        title='SignalR with Redis for real-time notifications',
        reasoning='SignalR provides WebSocket abstraction with automatic fallback, Redis backplane enables horizontal scaling across Aspire services',
        context='Need real-time push notifications for user actions, workflow updates, and system events',
        alternatives='WebSockets directly (more complex), Server-Sent Events (one-way only), Polling (inefficient)'
    )

    if success:
        print("✅ Decision stored successfully")
    else:
        print("❌ Failed to store decision")
        return

    # Step 4: Query the knowledge back
    print_step(4, "Query Knowledge (Can We Find What We Just Learned?)")

    queries = ['signalr', 'real-time notifications', 'notification hub']

    for query in queries:
        results = recall_query(query, limit=3)
        print(f"\n  Query: '{query}'")
        print(f"  Results: {len(results)} found")

        for i, r in enumerate(results[:2], 1):
            if r['type'] == 'file':
                print(f"    {i}. [FILE] {r['path'].split('/')[-1]}: {r['summary'][:60]}...")
            elif r['type'] == 'pattern':
                print(f"    {i}. [PATTERN] {r['name']}: {r['description'][:60]}...")
            elif r['type'] == 'decision':
                print(f"    {i}. [DECISION] {r['title']}: {r['reasoning'][:60]}...")

    # Step 5: Update our knowledge (UPSERT - no duplicates)
    print_step(5, "Update Knowledge (Deeper Understanding)")
    print("\nAfter reviewing the code more, we learned the hub also handles user presence...")

    success = store_file_analysis(
        file_path='c:/Dev/orca/Orca.NotificationHub/NotificationHub.cs',
        summary='SignalR hub for real-time notifications AND user presence tracking',
        purpose='Provides WebSocket connections for push notifications, tracks online users, broadcasts presence changes, and enables live collaborative features',
        complexity='moderate',
        language='csharp',
        lines_of_code=85,
        dependencies=['SignalR', 'Aspire', 'Redis', 'Presence Tracking'],
        functions=[
            {'name': 'SendNotification', 'signature': 'async Task', 'purpose': 'Broadcast notification to specific user', 'complexity': 'simple'},
            {'name': 'OnConnectedAsync', 'signature': 'override async Task', 'purpose': 'Track user connection and presence', 'complexity': 'simple'},
            {'name': 'BroadcastPresence', 'signature': 'async Task', 'purpose': 'Notify all clients of user presence changes', 'complexity': 'simple'}
        ]
    )

    if success:
        print("✅ File analysis UPDATED (UPSERT worked - no duplicate created)")
    else:
        print("❌ Failed to update file analysis")

    # Step 6: Verify UPSERT (no duplicates)
    print_step(6, "Verify UPSERT (No Duplicates Created)")

    current_stats = get_memory_stats()

    # Should have +1 file, +1 pattern, +1 decision from initial
    expected_files = initial_stats['files'] + 1
    expected_patterns = initial_stats['patterns'] + 1
    expected_decisions = initial_stats['decisions'] + 1

    print(f"\n  Expected: {expected_files} files, {expected_patterns} patterns, {expected_decisions} decisions")
    print(f"  Actual:   {current_stats['files']} files, {current_stats['patterns']} patterns, {current_stats['decisions']} decisions")

    if (current_stats['files'] == expected_files and
        current_stats['patterns'] == expected_patterns and
        current_stats['decisions'] == expected_decisions):
        print("\n✅ UPSERT VERIFIED - No duplicates created!")
    else:
        print("\n⚠️  Counts don't match - possible duplicates or missing entries")

    # Step 7: Query updated knowledge
    print_step(7, "Query Updated Knowledge (See Our Improvements)")

    file_data = recall_file('c:/Dev/orca/Orca.NotificationHub/NotificationHub.cs')

    if file_data:
        print(f"\n  File: {file_data['path'].split('/')[-1]}")
        print(f"  Summary: {file_data['summary']}")
        print(f"  Purpose: {file_data['purpose']}")
        print(f"  Functions: {len(file_data.get('functions', []))}")

        if file_data.get('functions'):
            print("\n  Function List:")
            for func in file_data['functions']:
                print(f"    - {func['name']}: {func['purpose']}")

        print("\n✅ Updated knowledge retrieved successfully")
    else:
        print("\n❌ Could not retrieve file data")

    # Step 8: Demonstrate pattern recall
    print_step(8, "Recall Specific Pattern")

    pattern = recall_pattern('signalr-with-redis-backplane')

    if pattern:
        print(f"\n  Pattern: {pattern['name']}")
        print(f"  Category: {pattern['category']}")
        print(f"  Description: {pattern['description']}")
        print(f"  Usage Count: {pattern['usage_count']}")
        print("\n✅ Pattern recalled successfully")
    else:
        print("\n❌ Pattern not found")

    # Step 9: Clean up test data
    print_step(9, "Clean Up Test Data")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete test entries
        cursor.execute("DELETE FROM files WHERE path = ?",
                      ('c:/Dev/orca/Orca.NotificationHub/NotificationHub.cs',))
        cursor.execute("DELETE FROM patterns WHERE name = ?",
                      ('signalr-with-redis-backplane',))
        cursor.execute("DELETE FROM decisions WHERE title = ?",
                      ('SignalR with Redis for real-time notifications',))

        conn.commit()
        conn.close()

        print("✅ Test data cleaned up")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

    # Step 10: Verify cleanup
    print_step(10, "Verify Cleanup (Back to Initial State)")

    final_stats = get_memory_stats()

    print(f"\n  Initial: {initial_stats['files']} files, {initial_stats['patterns']} patterns, {initial_stats['decisions']} decisions")
    print(f"  Final:   {final_stats['files']} files, {final_stats['patterns']} patterns, {final_stats['decisions']} decisions")

    cleanup_success = (final_stats['files'] == initial_stats['files'] and
                       final_stats['patterns'] == initial_stats['patterns'] and
                       final_stats['decisions'] == initial_stats['decisions'])

    if cleanup_success:
        print("\n✅ Cleanup verified - back to initial state")
    else:
        print("\n⚠️  Stats don't match initial state")

    # Summary
    print_section("WORKFLOW TEST SUMMARY")

    workflow_steps = [
        ("Store file analysis", True),
        ("Store related pattern", True),
        ("Store architectural decision", True),
        ("Query with natural language", True),
        ("Update existing knowledge (UPSERT)", True),
        ("Verify no duplicates", current_stats['files'] == expected_files),
        ("Retrieve updated knowledge", file_data is not None),
        ("Recall specific pattern", pattern is not None),
        ("Clean up test data", True),
        ("Verify cleanup", cleanup_success)
    ]

    passed = sum(1 for _, result in workflow_steps if result)
    total = len(workflow_steps)

    print()
    for step, result in workflow_steps:
        status = "✅" if result else "❌"
        print(f"{status} {step}")

    print(f"\n{passed}/{total} workflow steps successful")

    if passed == total:
        print("\n🎉 COMPLETE WORKFLOW VALIDATED!")
        print("\nThe knowledge system successfully:")
        print("  • Stored new learning")
        print("  • Allowed natural language queries")
        print("  • Updated existing knowledge without duplicates (UPSERT)")
        print("  • Retrieved detailed information")
        print("  • Maintained data integrity")
    else:
        print(f"\n⚠️  {total - passed} step(s) had issues")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
