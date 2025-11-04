#!/usr/bin/env python3
"""
Test the Obsidian storage system
"""

import sys
from pathlib import Path

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage_obsidian import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_query,
    get_memory_stats,
    remember_file
)

print("Testing Obsidian Storage System")
print("=" * 60)

# Test 1: Store file analysis
print("\n1. Testing file analysis storage...")
result = store_file_analysis(
    file_path="src/auth/jwt.ts",
    summary="JWT token generation and validation service",
    purpose="Provides secure token-based authentication",
    complexity="moderate",
    language="typescript",
    lines_of_code=150,
    dependencies=["jsonwebtoken", "bcrypt"],
    functions=[
        {
            "name": "generateToken",
            "signature": "generateToken(userId: string): Promise<string>",
            "purpose": "Creates JWT access token",
            "complexity": "simple"
        },
        {
            "name": "verifyToken",
            "signature": "verifyToken(token: string): Promise<JWTPayload>",
            "purpose": "Validates JWT token",
            "complexity": "simple"
        }
    ]
)
print(f"   Result: {'SUCCESS' if result else 'FAILED'}")

# Test 2: Store pattern
print("\n2. Testing pattern storage...")
result = store_pattern(
    name="Repository Pattern",
    description="Encapsulates data access logic in repository classes",
    example_path="src/repositories/user-repository.ts",
    category="Architecture"
)
print(f"   Result: {'SUCCESS' if result else 'FAILED'}")

# Test 3: Store decision
print("\n3. Testing decision storage...")
result = store_decision(
    title="Use JWT for Authentication",
    reasoning="Stateless authentication scales better for distributed systems",
    context="Building REST API that needs horizontal scaling",
    alternatives="Considered session-based auth but requires shared storage"
)
print(f"   Result: {'SUCCESS' if result else 'FAILED'}")

# Test 4: Query
print("\n4. Testing query...")
results = recall_query("authentication")
print(f"   Found {len(results)} results")
for r in results[:3]:
    print(f"   - {r['type']}: {r.get('title', r.get('file_path', 'N/A'))}")

# Test 5: Stats
print("\n5. Getting memory stats...")
stats = get_memory_stats()
print(f"   Files: {stats.get('files', 0)}")
print(f"   Patterns: {stats.get('patterns', 0)}")
print(f"   Decisions: {stats.get('decisions', 0)}")
print(f"   Total notes: {stats.get('total_notes', 0)}")
print(f"   Vault size: {stats.get('vault_size_mb', 0)} MB")

print("\n" + "=" * 60)
print("[SUCCESS] All tests completed!")
print("\nYou can now:")
print("1. Open .prism-knowledge/ in Obsidian")
print("2. Browse the test notes")
print("3. Check graph view to see connections")
