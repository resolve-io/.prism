#!/usr/bin/env python3
"""
PRISM Context Memory - Obsidian Storage Layer

This module handles storage operations using Obsidian markdown notes.
Analysis is done by the Claude Code agent, not here.

Architecture:
- Agent analyzes files/code (using native Read/Grep tools)
- Agent calls these storage functions to persist results as markdown
- No AI/LLM calls in this module - pure data storage
- Uses YAML frontmatter for metadata
- Stores in Obsidian vault as markdown files
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import sys
from urllib.parse import quote

try:
    import frontmatter
except ImportError:
    print("[ERROR] python-frontmatter not installed")
    print("   Run: pip install python-frontmatter")
    sys.exit(1)

try:
    import yaml
except ImportError:
    yaml = None

# Import memory intelligence layer
try:
    from memory_intelligence import (
        calculate_decay,
        reinforce_confidence,
        calculate_relevance_score,
        extract_tags_from_content,
        find_similar_notes,
        should_update_existing,
        merge_note_content
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError:
    INTELLIGENCE_AVAILABLE = False

# Cache for core-config.yaml
_core_config_cache = None


def load_core_config() -> Dict:
    """
    Load core-config.yaml from PRISM root.

    Returns config dict with memory settings, or empty dict if not found.
    Uses caching to avoid repeated file reads.
    """
    global _core_config_cache

    if _core_config_cache is not None:
        return _core_config_cache

    if yaml is None:
        _core_config_cache = {}
        return _core_config_cache

    try:
        prism_root = get_prism_root()
        config_path = prism_root / "core-config.yaml"

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                _core_config_cache = yaml.safe_load(f) or {}
        else:
            _core_config_cache = {}
    except Exception:
        _core_config_cache = {}

    return _core_config_cache


def get_config_value(key: str, default: str) -> str:
    """
    Get configuration value from core-config.yaml or environment.

    Priority:
    1. Environment variable
    2. core-config.yaml
    3. Default value

    Args:
        key: Config key (e.g., 'vault' for memory.vault)
        default: Default value if not found

    Returns:
        Configuration value
    """
    # Check environment variable first (highest priority)
    env_key = f"PRISM_OBSIDIAN_{key.upper()}"
    if env_key in os.environ:
        return os.environ[env_key]

    # Check core-config.yaml
    config = load_core_config()
    memory_config = config.get('memory', {})

    if key in memory_config:
        return str(memory_config[key])

    # Return default
    return default


def find_git_root() -> Optional[str]:
    """
    Find git root directory (PRISM root).

    PRISM root is identified by the .git folder.
    This is the .prism directory where all PRISM skills live.

    Returns:
        Absolute path to .prism directory
    """
    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return str(current)
        current = current.parent
    return None


def get_prism_root() -> Path:
    """
    Get PRISM root directory (same as git root).

    This is the .prism folder where all PRISM skills and config live.
    The vault will be created relative to this directory.

    Returns:
        Path object for PRISM root
    """
    git_root = find_git_root()
    if git_root:
        return Path(git_root)

    # Fallback: assume we're running from within .prism
    return Path.cwd()


def get_vault_path() -> Path:
    """
    Get Obsidian vault path.

    Configuration Priority:
    1. PRISM_OBSIDIAN_VAULT environment variable
    2. memory.vault in core-config.yaml
    3. Default: ../docs/memory

    Path Resolution:
    - If relative path: resolves relative to PRISM root (.prism folder)
    - If absolute path: uses as-is

    Examples:
        PRISM_OBSIDIAN_VAULT="../docs/memory"
        → {PROJECT_ROOT}/docs/memory (e.g., C:/Dev/MyProject/docs/memory)

        memory.vault in core-config.yaml: "../docs/memory"
        → {PROJECT_ROOT}/docs/memory

        PRISM_OBSIDIAN_VAULT="docs/knowledge"
        → {PRISM_ROOT}/docs/knowledge (inside .prism folder)

        PRISM_OBSIDIAN_VAULT="/absolute/path/to/vault"
        → /absolute/path/to/vault

    Returns:
        Absolute path to vault
    """
    vault_path = get_config_value('vault', '../docs/memory')

    # Resolve relative paths from PRISM root (.prism folder)
    if not os.path.isabs(vault_path):
        prism_root = get_prism_root()
        vault_path = prism_root / vault_path

    return Path(vault_path).resolve()  # Normalize path (resolve .. references)


def get_folder_paths() -> Dict[str, Path]:
    """
    Get folder paths for different note types.

    Reads from core-config.yaml memory.folders or environment variables.
    Falls back to default PRISM-Memory structure.
    """
    vault = get_vault_path()

    # Get folders config from core-config or env vars
    config = load_core_config()
    memory_config = config.get('memory', {})
    folders_config = memory_config.get('folders', {})

    return {
        'files': vault / (
            os.environ.get("PRISM_MEMORY_FILES_FOLDER") or
            folders_config.get('files', 'PRISM-Memory/Files')
        ),
        'patterns': vault / (
            os.environ.get("PRISM_MEMORY_PATTERNS_FOLDER") or
            folders_config.get('patterns', 'PRISM-Memory/Patterns')
        ),
        'decisions': vault / (
            os.environ.get("PRISM_MEMORY_DECISIONS_FOLDER") or
            folders_config.get('decisions', 'PRISM-Memory/Decisions')
        ),
        'commits': vault / (
            os.environ.get("PRISM_MEMORY_COMMITS_FOLDER") or
            folders_config.get('commits', 'PRISM-Memory/Commits')
        ),
        'interactions': vault / (
            os.environ.get("PRISM_MEMORY_INTERACTIONS_FOLDER") or
            folders_config.get('interactions', 'PRISM-Memory/Interactions')
        ),
        'preferences': vault / (
            os.environ.get("PRISM_MEMORY_PREFERENCES_FOLDER") or
            folders_config.get('preferences', 'PRISM-Memory/Preferences')
        ),
        'learnings': vault / (
            os.environ.get("PRISM_MEMORY_LEARNINGS_FOLDER") or
            folders_config.get('learnings', 'PRISM-Memory/Learnings')
        ),
        'index': vault / "PRISM-Memory/Index"
    }


def ensure_folder(path: Path) -> None:
    """Ensure folder exists, create if needed."""
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Convert name to safe filename."""
    # Replace problematic characters
    name = name.replace('/', '-').replace('\\', '-')
    name = re.sub(r'[<>:"|?*]', '', name)
    return name


def to_wikilink(path: str) -> str:
    """Convert file path to Obsidian wikilink."""
    # Remove .md extension if present
    if path.endswith('.md'):
        path = path[:-3]
    return f"[[{path}]]"


def format_date(dt: Optional[datetime] = None) -> str:
    """Format datetime for frontmatter."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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
    Store file analysis results as markdown note with intelligent upsert.

    NOTE: Agent does the analysis, this function just stores the results.

    Features:
    - Checks for existing note and updates if found
    - Adds intelligence metadata (confidence, access tracking)
    - Extracts semantic tags from content
    - Tracks memory health over time

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
    try:
        folders = get_folder_paths()

        # Create file structure matching original path
        # e.g., src/auth/jwt.ts -> Files/src/auth/jwt.ts.md
        relative_path = Path(file_path)
        note_path = folders['files'] / f"{file_path}.md"

        # Check if note already exists (upsert logic)
        is_update = note_path.exists()

        # Ensure parent directories exist
        ensure_folder(note_path.parent)

        # Extract intelligent tags from content
        content_for_tags = f"{summary} {purpose} {language} {' '.join(dependencies)}"
        base_tags = [language, complexity, 'code-analysis']

        if INTELLIGENCE_AVAILABLE:
            intelligent_tags = extract_tags_from_content(content_for_tags, base_tags)
        else:
            intelligent_tags = base_tags

        # Prepare metadata with intelligence features
        now = format_date()
        metadata = {
            'type': 'file-analysis',
            'file_path': file_path,
            'language': language,
            'complexity': complexity,
            'lines_of_code': lines_of_code,
            'analyzed_at': now,
            'last_modified': now,
            'last_accessed': now,
            'dependencies': dependencies,
            'tags': intelligent_tags,
            # Intelligence metadata
            'confidence_score': 0.5 if not is_update else None,  # Will merge if update
            'access_count': 0 if not is_update else None,
            'relevance_score': 0.5 if not is_update else None
        }

        # Build content
        content_parts = [
            f"# {file_path}\n",
            f"## Summary\n{summary}\n",
            f"## Purpose\n{purpose}\n"
        ]

        # Add functions if provided
        if functions:
            content_parts.append("\n## Key Functions\n")
            for func in functions:
                name = func.get('name', 'unnamed')
                signature = func.get('signature', '')
                func_purpose = func.get('purpose', '')
                func_complexity = func.get('complexity', 'moderate')

                content_parts.append(f"\n### `{name}`")
                content_parts.append(f"- **Purpose:** {func_purpose}")
                content_parts.append(f"- **Complexity:** {func_complexity}")
                if signature:
                    content_parts.append(f"- **Signature:** `{signature}`")
                content_parts.append("")

        # Add related notes section
        content_parts.append("\n## Related Notes\n")
        content_parts.append("<!-- Add links to related patterns, decisions, and other files -->\n")

        # Add dependencies section if any
        if dependencies:
            content_parts.append("\n## Dependencies\n")
            content_parts.append("```")
            for dep in dependencies:
                content_parts.append(dep)
            content_parts.append("```")

        content = "\n".join(content_parts)

        # Handle updates intelligently
        if is_update:
            try:
                existing_post = frontmatter.load(note_path)

                # Preserve and update intelligence metadata
                old_confidence = existing_post.get('confidence_score', 0.5)
                old_access_count = existing_post.get('access_count', 0)

                # Update metadata (merge with existing)
                metadata['confidence_score'] = min(old_confidence + 0.1, 1.0)  # Increase slightly on update
                metadata['access_count'] = old_access_count
                metadata['analyzed_at'] = existing_post.get('analyzed_at', now)  # Keep original
                metadata['last_modified'] = now  # Update to now

                # Merge tags (keep unique)
                old_tags = existing_post.get('tags', [])
                metadata['tags'] = sorted(list(set(old_tags + intelligent_tags)))

                # Merge content if significantly different
                if len(content) > len(existing_post.content) * 1.2:
                    # New content is substantially longer - append
                    if INTELLIGENCE_AVAILABLE:
                        content = merge_note_content(existing_post.content, content, "sections")
                    else:
                        timestamp = datetime.now().strftime("%Y-%m-%d")
                        content = f"{existing_post.content}\n\n## Update - {timestamp}\n\n{content}"

                print(f"[OK] Updated analysis for {file_path}")
            except Exception as e:
                print(f"[WARN] Could not merge existing note, will overwrite: {e}")

        # Create or update frontmatter post
        post = frontmatter.Post(content, **metadata)

        # Write to file
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        if not is_update:
            print(f"[OK] Stored analysis for {file_path}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to store file analysis: {e}")
        return False


def store_pattern(
    name: str,
    description: str,
    example_path: Optional[str] = None,
    category: Optional[str] = None
) -> bool:
    """
    Store a reusable code pattern as markdown note.

    Args:
        name: Pattern name
        description: What the pattern does (from agent analysis)
        example_path: Optional example file path
        category: Optional category (e.g., 'Architecture', 'Testing', 'Security')
    """
    try:
        folders = get_folder_paths()

        # Organize by category if provided
        if category:
            pattern_folder = folders['patterns'] / category.capitalize()
        else:
            pattern_folder = folders['patterns']

        ensure_folder(pattern_folder)

        # Create filename from pattern name
        filename = sanitize_filename(name) + ".md"
        note_path = pattern_folder / filename

        # Check if pattern already exists
        existing_usage_count = 1
        if note_path.exists():
            existing_post = frontmatter.load(note_path)
            existing_usage_count = existing_post.get('usage_count', 0) + 1

        # Prepare metadata
        metadata = {
            'type': 'pattern',
            'category': category or 'general',
            'created_at': format_date(),
            'updated_at': format_date(),
            'usage_count': existing_usage_count,
            'tags': [category] if category else []
        }

        # Build content
        content_parts = [
            f"# {name}\n",
            f"## Description\n{description}\n"
        ]

        if example_path:
            content_parts.append(f"\n## Example Implementation")
            content_parts.append(to_wikilink(f"Files/{example_path}"))

        content_parts.extend([
            "\n## When to Use\n",
            "<!-- Describe when this pattern is appropriate -->\n",
            "\n## Benefits\n",
            "<!-- List key benefits -->\n",
            "\n## Trade-offs\n",
            "<!-- List potential drawbacks -->\n",
            "\n## Related Patterns\n",
            "<!-- Link to related patterns -->\n",
            "\n## Used In\n",
            "<!-- Link to files using this pattern -->\n"
        ])

        content = "\n".join(content_parts)

        # Create or update note
        post = frontmatter.Post(content, **metadata)

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        print(f"[OK] Stored pattern: {name}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to store pattern: {e}")
        return False


def store_decision(
    title: str,
    reasoning: str,
    context: Optional[str] = None,
    alternatives: Optional[str] = None
) -> bool:
    """
    Store an architectural decision as markdown note.

    Args:
        title: Decision title
        reasoning: Why this decision was made (from agent analysis)
        context: Background context
        alternatives: Alternatives that were considered
    """
    try:
        folders = get_folder_paths()
        ensure_folder(folders['decisions'])

        # Create filename with date prefix for chronological sorting
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str} {sanitize_filename(title)}.md"
        note_path = folders['decisions'] / filename

        # Prepare metadata
        metadata = {
            'type': 'decision',
            'decision_date': date_str,
            'status': 'accepted',
            'impact': 'medium',  # Can be updated later
            'tags': []
        }

        # Build content
        content_parts = [
            f"# {title}\n",
            f"## Decision\n{title}\n",
            f"## Context\n{context or 'N/A'}\n",
            f"## Reasoning\n{reasoning}\n"
        ]

        if alternatives:
            content_parts.extend([
                f"\n## Alternatives Considered\n",
                f"{alternatives}\n"
            ])

        content_parts.extend([
            "\n## Implementation\n",
            "<!-- Implementation details -->\n",
            "\n## Consequences\n",
            "### Positive\n",
            "<!-- Positive outcomes -->\n",
            "\n### Negative\n",
            "<!-- Negative outcomes or trade-offs -->\n",
            "\n## Related Notes\n",
            "<!-- Link to related files, patterns, decisions -->\n"
        ])

        content = "\n".join(content_parts)

        # Create note
        post = frontmatter.Post(content, **metadata)

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        print(f"[OK] Stored decision: {title}")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to store decision: {e}")
        return False


def store_interaction(
    skill: str,
    context: str,
    action: str,
    outcome: str,
    learned: str,
    effectiveness: str = "successful"
) -> bool:
    """
    Store agent interaction and learning as markdown note.

    Args:
        skill: Skill/command used
        context: What was the situation
        action: What action was taken
        outcome: What happened
        learned: What did we learn
        effectiveness: 'successful', 'partial', 'failed'
    """
    try:
        folders = get_folder_paths()
        ensure_folder(folders['interactions'])

        # Create filename with timestamp and topic
        timestamp = datetime.now().strftime("%Y-%m-%d")
        topic = sanitize_filename(context[:50])  # First 50 chars of context
        filename = f"{timestamp}-{topic}.md"
        note_path = folders['interactions'] / filename

        # Prepare metadata
        metadata = {
            'type': 'interaction',
            'date': format_date(),
            'outcome': effectiveness,
            'tags': [skill, effectiveness]
        }

        # Build content
        content = f"""# {context}

## Request
{context}

## Approach
{action}

## Outcome
{outcome}

## Key Learnings
{learned}

## Related Notes
<!-- Link to related files, patterns, decisions -->
"""

        # Create note
        post = frontmatter.Post(content, **metadata)

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        return True

    except Exception as e:
        print(f"[ERROR] Failed to store interaction: {e}")
        return False


def store_git_commit(
    commit_hash: str,
    author: str,
    date: str,
    message: str,
    files_changed: int,
    insertions: int,
    deletions: int
) -> bool:
    """
    Store git commit context as markdown note.

    Args:
        commit_hash: Git commit hash
        author: Commit author
        date: Commit date
        message: Commit message
        files_changed: Number of files changed
        insertions: Number of insertions
        deletions: Number of deletions
    """
    try:
        folders = get_folder_paths()

        # Organize by year-month
        commit_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
        year_month = commit_date.strftime("%Y-%m")
        commit_folder = folders['commits'] / year_month
        ensure_folder(commit_folder)

        # Create filename from hash and message
        short_hash = commit_hash[:7]
        slug = sanitize_filename(message.split('\n')[0][:50].lower().replace(' ', '-'))
        filename = f"{short_hash}-{slug}.md"
        note_path = commit_folder / filename

        # Prepare metadata
        metadata = {
            'type': 'git-commit',
            'commit_hash': commit_hash,
            'author': author,
            'date': date,
            'files_changed': files_changed,
            'insertions': insertions,
            'deletions': deletions,
            'tags': ['git-commit']
        }

        # Build content
        content = f"""# {message.split(chr(10))[0]}

## Commit
`{commit_hash}`

## Message
```
{message}
```

## Statistics
- Files changed: {files_changed}
- Insertions: {insertions}
- Deletions: {deletions}

## Context
<!-- Add context about why this change was made -->

## Related Notes
<!-- Link to related files, patterns, decisions -->
"""

        # Create note
        post = frontmatter.Post(content, **metadata)

        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(frontmatter.dumps(post))

        return True

    except Exception as e:
        print(f"[ERROR] Failed to store commit: {e}")
        return False


# ============================================================================
# RECALL operations (retrieving stored context)
# ============================================================================

def recall_query(query: str, limit: int = 10, update_access: bool = True) -> List[Dict]:
    """
    Full-text search across all markdown notes with intelligent tracking.

    Features:
    - Updates access metadata on retrieval
    - Applies confidence decay
    - Calculates relevance scores
    - Tracks successful retrievals

    Args:
        query: Search query
        limit: Maximum results to return
        update_access: Whether to update access metadata (default True)

    Returns:
        List of results with type and relevance scores
    """
    results = []
    folders = get_folder_paths()
    vault = get_vault_path()

    # Sanitize query
    query_lower = query.lower()

    try:
        # Search all markdown files in vault
        for md_file in vault.rglob("*.md"):
            try:
                post = frontmatter.load(md_file)

                # Calculate relevance score
                relevance = 0
                content_lower = post.content.lower()

                # Title match (highest weight)
                title = md_file.stem
                if query_lower in title.lower():
                    relevance += 10

                # Frontmatter match
                for key, value in post.metadata.items():
                    if isinstance(value, str) and query_lower in value.lower():
                        relevance += 5
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str) and query_lower in item.lower():
                                relevance += 3

                # Content match
                if query_lower in content_lower:
                    relevance += content_lower.count(query_lower)

                if relevance > 0:
                    note_type = post.get('type', 'unknown')
                    relative_path = md_file.relative_to(vault)

                    # Apply memory decay if intelligence available
                    confidence = post.get('confidence_score', 0.5)
                    if INTELLIGENCE_AVAILABLE and 'last_accessed' in post.metadata:
                        try:
                            last_accessed = datetime.fromisoformat(post.get('last_accessed'))
                            confidence = calculate_decay(confidence, last_accessed)
                        except:
                            pass

                    result = {
                        'type': note_type,
                        'path': str(relative_path),
                        'title': title,
                        'relevance': relevance,
                        'confidence': confidence,
                        'metadata': post.metadata
                    }

                    # Add type-specific fields
                    if note_type == 'file-analysis':
                        result.update({
                            'file_path': post.get('file_path', ''),
                            'summary': post.content.split('\n## Summary\n')[1].split('\n##')[0].strip() if '\n## Summary\n' in post.content else '',
                            'complexity': post.get('complexity', ''),
                            'language': post.get('language', '')
                        })
                    elif note_type == 'pattern':
                        result.update({
                            'name': title,
                            'description': post.content.split('\n## Description\n')[1].split('\n##')[0].strip() if '\n## Description\n' in post.content else '',
                            'category': post.get('category', '')
                        })
                    elif note_type == 'decision':
                        result.update({
                            'title': title,
                            'reasoning': post.content.split('\n## Reasoning\n')[1].split('\n##')[0].strip() if '\n## Reasoning\n' in post.content else '',
                            'decision_date': post.get('decision_date', '')
                        })

                    results.append(result)

            except Exception as e:
                # Skip files that can't be parsed
                continue

        # Sort by relevance and limit
        results.sort(key=lambda x: x['relevance'], reverse=True)
        top_results = results[:limit]

        # Update access metadata for retrieved notes (if enabled)
        if update_access and INTELLIGENCE_AVAILABLE:
            for result in top_results:
                try:
                    note_path = vault / result['path']
                    if not note_path.exists():
                        continue

                    post = frontmatter.load(note_path)

                    # Update access tracking
                    old_confidence = post.get('confidence_score', 0.5)
                    old_access_count = post.get('access_count', 0)

                    # Reinforce confidence on successful retrieval
                    new_confidence = reinforce_confidence(old_confidence, True)

                    post.metadata['confidence_score'] = new_confidence
                    post.metadata['access_count'] = old_access_count + 1
                    post.metadata['last_accessed'] = format_date()

                    # Write updated metadata
                    with open(note_path, 'w', encoding='utf-8') as f:
                        f.write(frontmatter.dumps(post))

                except Exception:
                    # Don't fail query if update fails
                    continue

        return top_results

    except Exception as e:
        print(f"[ERROR] Search failed: {e}")
        return []


def recall_file(path: str) -> Optional[Dict]:
    """Get detailed information about a specific file analysis note."""
    try:
        folders = get_folder_paths()
        note_path = folders['files'] / f"{path}.md"

        if not note_path.exists():
            return None

        post = frontmatter.load(note_path)

        result = {
            'path': path,
            'metadata': post.metadata,
            'content': post.content,
            'summary': post.content.split('\n## Summary\n')[1].split('\n##')[0].strip() if '\n## Summary\n' in post.content else '',
            'purpose': post.content.split('\n## Purpose\n')[1].split('\n##')[0].strip() if '\n## Purpose\n' in post.content else ''
        }

        return result

    except Exception as e:
        print(f"[ERROR] Failed to recall file: {e}")
        return None


def recall_pattern(name: str) -> Optional[Dict]:
    """Get detailed information about a specific pattern note."""
    try:
        folders = get_folder_paths()

        # Search in all category subfolders
        for pattern_file in folders['patterns'].rglob(f"{sanitize_filename(name)}.md"):
            post = frontmatter.load(pattern_file)

            return {
                'name': name,
                'metadata': post.metadata,
                'content': post.content,
                'description': post.content.split('\n## Description\n')[1].split('\n##')[0].strip() if '\n## Description\n' in post.content else ''
            }

        return None

    except Exception as e:
        print(f"[ERROR] Failed to recall pattern: {e}")
        return None


def get_memory_stats() -> Dict:
    """Get statistics about stored memory."""
    try:
        folders = get_folder_paths()
        vault = get_vault_path()

        stats = {
            'files': 0,
            'patterns': 0,
            'decisions': 0,
            'interactions': 0,
            'commits': 0,
            'total_notes': 0,
            'vault_size_mb': 0
        }

        # Count by type
        for md_file in vault.rglob("*.md"):
            try:
                post = frontmatter.load(md_file)
                note_type = post.get('type', 'unknown')

                if note_type == 'file-analysis':
                    stats['files'] += 1
                elif note_type == 'pattern':
                    stats['patterns'] += 1
                elif note_type == 'decision':
                    stats['decisions'] += 1
                elif note_type == 'interaction':
                    stats['interactions'] += 1
                elif note_type == 'git-commit':
                    stats['commits'] += 1

                stats['total_notes'] += 1
            except:
                continue

        # Calculate vault size
        total_size = sum(f.stat().st_size for f in vault.rglob("*") if f.is_file())
        stats['vault_size_mb'] = round(total_size / (1024 * 1024), 2)

        return stats

    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")
        return {}


# ============================================================================
# CONVENIENCE HELPERS (simplified APIs)
# ============================================================================

def remember_file(file_path: str, summary: str = None, purpose: str = None,
                  complexity: str = None, note: str = None) -> bool:
    """
    Store file analysis with automatic language detection and defaults.

    Simplified API for hooks and quick captures.

    Args:
        file_path: Path to file
        summary: One-sentence summary (auto-generated if missing)
        purpose: Main purpose (defaults to "Pending analysis")
        complexity: 'simple', 'moderate', or 'complex' (defaults to 'moderate')
        note: Additional note (e.g., "Modified via Edit")

    Returns:
        True if successful
    """
    import os

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


def recall_decisions(days: Optional[int] = None) -> List[Dict]:
    """
    Get architectural decisions, optionally filtered by timeframe.

    Args:
        days: Only return decisions from last N days (None = all)

    Returns:
        List of decision dictionaries
    """
    from datetime import datetime, timedelta

    try:
        folders = get_folder_paths()
        decisions_folder = folders['decisions']

        if not decisions_folder.exists():
            return []

        decisions = []
        cutoff = None
        if days:
            cutoff = datetime.now() - timedelta(days=days)

        for md_file in decisions_folder.glob("*.md"):
            try:
                post = frontmatter.load(md_file)

                # Filter by date if specified
                if cutoff:
                    decision_date = post.get('decision_date')
                    if decision_date:
                        file_date = datetime.fromisoformat(decision_date)
                        if file_date < cutoff:
                            continue

                # Only include accepted decisions
                if post.get('status') == 'accepted':
                    decisions.append({
                        'title': md_file.stem,
                        'decision_date': post.get('decision_date'),
                        'status': post.get('status'),
                        'impact': post.get('impact'),
                        'content': post.content,
                        'metadata': post.metadata
                    })
            except Exception:
                continue

        # Sort by date (newest first)
        decisions.sort(key=lambda x: x.get('decision_date', ''), reverse=True)
        return decisions

    except Exception as e:
        print(f"[ERROR] Failed to recall decisions: {e}")
        return []


def consolidate_story_learnings(
    story_id: str,
    story_title: str,
    files_changed: List[str] = None,
    patterns_used: List[str] = None,
    decisions_made: List[str] = None,
    key_learnings: List[str] = None
) -> Dict[str, int]:
    """
    Consolidate learnings after story completion.

    This function:
    1. Finds memories related to the story
    2. Reviews confidence scores and identifies decayed memories
    3. Refreshes low-confidence memories with updated context
    4. Creates learning notes capturing what was learned
    5. Reinforces patterns/decisions that were successfully used

    Args:
        story_id: Story identifier (e.g., "PLAT-123")
        story_title: Human-readable story title
        files_changed: List of file paths that were modified
        patterns_used: List of patterns that were applied
        decisions_made: List of decisions that were made
        key_learnings: List of key takeaways from the story

    Returns:
        Dict with counts: {
            'memories_reviewed': int,
            'memories_refreshed': int,
            'patterns_reinforced': int,
            'learnings_captured': int
        }
    """
    if not INTELLIGENCE_AVAILABLE:
        print("[WARNING] Memory intelligence not available, skipping consolidation")
        return {}

    config = load_core_config()
    memory_config = config.get('memory', {})

    # Check if consolidation is enabled
    if not memory_config.get('consolidate_on_story_complete', True):
        return {}

    review_threshold = memory_config.get('review_threshold', 0.3)

    stats = {
        'memories_reviewed': 0,
        'memories_refreshed': 0,
        'patterns_reinforced': 0,
        'learnings_captured': 0
    }

    try:
        vault = get_vault_path()
        folders = get_folder_paths()

        # 1. Review and refresh file memories
        if files_changed and memory_config.get('refresh_related_memories', True):
            for file_path in files_changed:
                note_path = folders['files'] / f"{file_path}.md"
                if note_path.exists():
                    post = frontmatter.load(note_path)
                    confidence = post.get('confidence_score', 0.5)
                    stats['memories_reviewed'] += 1

                    # If confidence is low, it needs refresh
                    if confidence < review_threshold:
                        # Mark for review by adding tag
                        tags = post.get('tags', [])
                        if 'needs-review' not in tags:
                            tags.append('needs-review')
                        post.metadata['tags'] = tags
                        post.metadata['review_reason'] = f'Low confidence ({confidence:.2f}) after story {story_id}'
                        post.metadata['last_story'] = story_id

                        with open(note_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))

                        stats['memories_refreshed'] += 1
                    else:
                        # Reinforce successful memory
                        new_confidence = reinforce_confidence(confidence, True)
                        post.metadata['confidence_score'] = new_confidence
                        post.metadata['last_story'] = story_id
                        post.metadata['last_accessed'] = format_date()

                        with open(note_path, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))

        # 2. Reinforce patterns that were used
        if patterns_used:
            for pattern_name in patterns_used:
                # Find pattern note by searching
                pattern_files = list(folders['patterns'].rglob('*.md'))
                for pattern_file in pattern_files:
                    post = frontmatter.load(pattern_file)
                    if post.get('name') == pattern_name or post.get('pattern') == pattern_name:
                        # Reinforce confidence
                        old_confidence = post.get('confidence_score', 0.5)
                        new_confidence = reinforce_confidence(old_confidence, True)

                        post.metadata['confidence_score'] = new_confidence
                        post.metadata['usage_count'] = post.get('usage_count', 0) + 1
                        post.metadata['last_used_story'] = story_id
                        post.metadata['last_accessed'] = format_date()

                        with open(pattern_file, 'w', encoding='utf-8') as f:
                            f.write(frontmatter.dumps(post))

                        stats['patterns_reinforced'] += 1
                        break

        # 3. Create learning note for the story
        if key_learnings:
            learning_folder = folders.get('learnings')
            if learning_folder:
                ensure_folder(learning_folder)

                # Create dated learning note
                date_str = datetime.now().strftime('%Y-%m-%d')
                learning_note = learning_folder / f"{date_str}_{sanitize_filename(story_id)}.md"

                metadata = {
                    'type': 'story-learning',
                    'story_id': story_id,
                    'story_title': story_title,
                    'completed_at': format_date(),
                    'files_changed': files_changed or [],
                    'patterns_used': patterns_used or [],
                    'decisions_made': decisions_made or [],
                    'confidence_score': 0.8,  # High confidence - fresh learning
                    'tags': ['learning', 'story-complete', story_id]
                }

                content = f"# Story Learning: {story_title}\n\n"
                content += f"**Story:** {story_id}\n"
                content += f"**Completed:** {format_date()}\n\n"
                content += "## Key Learnings\n\n"

                for learning in key_learnings:
                    content += f"- {learning}\n"

                content += "\n## Context\n\n"
                if files_changed:
                    content += f"**Files Changed:** {len(files_changed)}\n"
                if patterns_used:
                    content += f"**Patterns Used:** {', '.join(patterns_used)}\n"
                if decisions_made:
                    content += f"**Decisions Made:** {', '.join(decisions_made)}\n"

                content += "\n## Related Notes\n\n"
                content += "<!-- Links to related files, patterns, and decisions -->\n"

                post = frontmatter.Post(content, **metadata)
                with open(learning_note, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))

                stats['learnings_captured'] = 1

        return stats

    except Exception as e:
        print(f"[ERROR] Story consolidation failed: {e}")
        return stats


def get_memories_needing_review() -> List[Dict]:
    """
    Get list of memories that need review due to low confidence.

    Returns list of dicts with:
    - path: Path to note file
    - title: Note title
    - confidence: Current confidence score
    - last_accessed: Last access date
    - type: Note type (file, pattern, decision, etc.)
    """
    if not INTELLIGENCE_AVAILABLE:
        return []

    config = load_core_config()
    memory_config = config.get('memory', {})
    review_threshold = memory_config.get('review_threshold', 0.3)

    needs_review = []

    try:
        vault = get_vault_path()

        # Search all markdown files
        for note_path in vault.rglob('*.md'):
            if note_path.name in ['README.md', 'File Index.md', 'Pattern Index.md', 'Decision Log.md']:
                continue

            try:
                post = frontmatter.load(note_path)
                confidence = post.get('confidence_score', 0.5)

                if confidence < review_threshold:
                    needs_review.append({
                        'path': str(note_path.relative_to(vault)),
                        'title': post.get('file_path') or post.get('name') or post.get('decision') or note_path.stem,
                        'confidence': confidence,
                        'last_accessed': post.get('last_accessed', 'never'),
                        'type': post.get('type', 'unknown')
                    })

            except Exception:
                continue

        # Sort by confidence (lowest first)
        needs_review.sort(key=lambda x: x['confidence'])

        return needs_review

    except Exception as e:
        print(f"[ERROR] Failed to get review list: {e}")
        return []


if __name__ == "__main__":
    # Test connection and show stats
    print("Context Memory Storage (Obsidian)")
    print("=" * 50)
    try:
        vault = get_vault_path()
        print(f"\nVault path: {vault}")

        if not vault.exists():
            print(f"\n[WARNING] Vault does not exist: {vault}")
            print("   Run: python skills/context-memory/utils/init_vault.py")
        else:
            stats = get_memory_stats()
            print("\nMemory Stats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print("\n[OK] Storage layer is operational")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
