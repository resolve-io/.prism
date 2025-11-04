#!/usr/bin/env python3
"""
PRISM Context Memory: Agent-Native Example

This example shows how Claude Code agent uses the memory system.
The agent analyzes files using native tools (Read/Grep) and stores results.

No external API calls - the agent IS Claude, so analysis happens natively.
"""

import sys
import io
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from storage import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_query,
    recall_file,
    get_memory_stats
)


def example_agent_workflow():
    """
    Example workflow showing how agent uses memory system.

    In practice, the agent (Claude Code) does this:
    1. User asks to analyze a file
    2. Agent reads file using Read tool
    3. Agent analyzes file content using native understanding
    4. Agent calls store_file_analysis() with results
    """

    print("🧠 Agent-Native Memory System Example\n")

    # Example 1: Agent analyzes and stores a file
    print("1️⃣  Agent analyzes file (using native Read tool)")
    print("   Agent reads: storage.py")
    print("   Agent understands: 'Pure storage layer for PRISM memory system'")
    print("   Agent identifies: functions, dependencies, complexity")
    print()

    # Agent stores analysis results
    print("2️⃣  Agent stores analysis in memory")
    result = store_file_analysis(
        file_path=".prism/skills/context-memory/utils/storage.py",
        summary="Pure storage layer for PRISM context memory system",
        purpose="Provides data-only storage functions without AI/analysis",
        complexity="moderate",
        language="python",
        lines_of_code=430,
        dependencies=["sqlite3", "json", "os", "datetime"],
        functions=[
            {
                "name": "store_file_analysis",
                "signature": "store_file_analysis(file_path, summary, purpose, ...)",
                "purpose": "Store file analysis results in database",
                "complexity": "moderate"
            },
            {
                "name": "recall_query",
                "signature": "recall_query(query, limit=10)",
                "purpose": "Full-text search across stored context",
                "complexity": "simple"
            }
        ]
    )
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")
    print()

    # Example 2: Agent stores a pattern
    print("3️⃣  Agent stores discovered pattern")
    result = store_pattern(
        name="Agent-Native Storage",
        description="Agent analyzes files natively, then calls pure storage functions",
        example_path=".prism/skills/context-memory/utils/storage.py",
        category="architecture"
    )
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")
    print()

    # Example 3: Agent stores architectural decision
    print("4️⃣  Agent stores architectural decision")
    result = store_decision(
        title="Remove External Claude API Dependency",
        reasoning="We ARE Claude Code, so making external API calls is redundant and costly",
        context="Memory system was calling Anthropic API separately",
        alternatives="Keep external API (rejected: doubles cost, adds latency)"
    )
    print(f"   Result: {'✅ Success' if result else '❌ Failed'}")
    print()

    # Example 4: Agent recalls context
    print("5️⃣  Agent recalls context before implementing")
    print("   Query: 'storage layer pattern'")
    results = recall_query("storage layer pattern", limit=3)
    print(f"   Found {len(results)} results:")
    for r in results[:3]:
        print(f"     - {r['type']}: {r.get('path') or r.get('name') or r.get('title')}")
    print()

    # Show stats
    print("6️⃣  Memory system statistics")
    stats = get_memory_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()

    print("✅ Agent-native workflow complete!")
    print()
    print("Key Points:")
    print("  • Agent analyzes using native tools (Read, Grep)")
    print("  • Agent stores results using storage functions")
    print("  • No external API calls needed")
    print("  • More efficient and cost-effective")


if __name__ == "__main__":
    example_agent_workflow()
