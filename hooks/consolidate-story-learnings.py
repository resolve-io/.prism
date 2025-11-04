#!/usr/bin/env python3
"""
Post-Story Learning Consolidation Hook

Triggers after story completion to:
1. Review memories related to the story
2. Refresh decayed/low-confidence memories
3. Reinforce patterns and decisions that were used
4. Capture key learnings from the story

This ensures that coding knowledge doesn't decay - instead it gets
refreshed and updated as part of the learning cycle.
"""

import os
import sys
import json
from pathlib import Path

# Add skills directory to path
prism_root = Path(__file__).parent.parent
sys.path.insert(0, str(prism_root / "skills" / "context-memory" / "utils"))

try:
    from storage_obsidian import consolidate_story_learnings, get_memories_needing_review
except ImportError as e:
    print(f"[ERROR] Failed to import storage_obsidian: {e}")
    sys.exit(0)  # Don't fail the hook


def get_story_context():
    """Extract story context from environment or git."""
    story_id = os.environ.get('PRISM_STORY_ID', '')
    story_title = os.environ.get('PRISM_STORY_TITLE', '')

    # If not in env, try to read from .prism-current-story.txt
    story_file = prism_root / '.prism-current-story.txt'
    if not story_id and story_file.exists():
        try:
            with open(story_file, 'r') as f:
                story_data = json.loads(f.read())
                story_id = story_data.get('id', '')
                story_title = story_data.get('title', '')
        except Exception:
            pass

    return story_id, story_title


def get_changed_files():
    """Get list of files changed in recent commits."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1..HEAD'],
            capture_output=True,
            text=True,
            cwd=prism_root.parent
        )

        if result.returncode == 0:
            return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except Exception:
        pass

    return []


def main():
    """Run story learning consolidation."""

    # Only run if story context is available
    story_id, story_title = get_story_context()

    if not story_id:
        # No story context - skip consolidation
        sys.exit(0)

    print(f"\n=== Story Learning Consolidation ===")
    print(f"Story: {story_id} - {story_title}")

    # Get changed files
    files_changed = get_changed_files()

    # Run consolidation
    try:
        stats = consolidate_story_learnings(
            story_id=story_id,
            story_title=story_title,
            files_changed=files_changed,
            patterns_used=[],  # TODO: Extract from story metadata
            decisions_made=[],  # TODO: Extract from story metadata
            key_learnings=[]  # TODO: Extract from story metadata
        )

        if stats:
            print(f"\nConsolidation Results:")
            print(f"  Memories reviewed: {stats.get('memories_reviewed', 0)}")
            print(f"  Memories refreshed: {stats.get('memories_refreshed', 0)}")
            print(f"  Patterns reinforced: {stats.get('patterns_reinforced', 0)}")
            print(f"  Learnings captured: {stats.get('learnings_captured', 0)}")

        # Show memories that need review
        needs_review = get_memories_needing_review()
        if needs_review:
            print(f"\n⚠️  {len(needs_review)} memories need review:")
            for memory in needs_review[:5]:  # Show top 5
                print(f"  - {memory['title']} (confidence: {memory['confidence']:.2f})")

            if len(needs_review) > 5:
                print(f"  ... and {len(needs_review) - 5} more")

    except Exception as e:
        print(f"[ERROR] Consolidation failed: {e}")
        # Don't fail the hook

    print()


if __name__ == "__main__":
    main()
