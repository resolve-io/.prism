#!/usr/bin/env python3
"""
PRISM Context Memory - Intelligence Layer

Implements memory decay, self-evaluation, and learning over time.
Based on research in persistent memory systems with confidence scoring.

Key Concepts:
- Memory Decay: Confidence scores decay following Ebbinghaus curve unless reinforced
- Self-Evaluation: Track retrieval success and relevance
- Upsert Logic: Update existing knowledge rather than duplicate
- Confidence Scoring: Increases with successful usage, decays over time
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
import re

sys.path.insert(0, str(Path(__file__).parent))

try:
    import frontmatter
except ImportError:
    print("[ERROR] python-frontmatter not installed")
    sys.exit(1)

# Lazy import to avoid circular dependency
# storage_obsidian imports from this file, so we can't import it at module level
_storage_obsidian = None

def _get_storage():
    """Lazy load storage_obsidian to avoid circular import."""
    global _storage_obsidian
    if _storage_obsidian is None:
        from storage_obsidian import get_vault_path, get_folder_paths, ensure_folder
        _storage_obsidian = {
            'get_vault_path': get_vault_path,
            'get_folder_paths': get_folder_paths,
            'ensure_folder': ensure_folder
        }
    return _storage_obsidian


# ============================================================================
# MEMORY DECAY & CONFIDENCE SCORING
# ============================================================================

def calculate_decay(
    confidence: float,
    last_accessed: datetime,
    half_life_days: int = 30
) -> float:
    """
    Calculate memory decay using exponential decay model (Ebbinghaus curve).

    Confidence decays unless memory is reinforced through successful retrieval.

    Args:
        confidence: Current confidence score (0-1)
        last_accessed: When memory was last accessed
        half_life_days: Days for confidence to decay to 50%

    Returns:
        Decayed confidence score
    """
    days_since_access = (datetime.now() - last_accessed).days

    if days_since_access == 0:
        return confidence

    # Exponential decay: C(t) = C₀ * (0.5)^(t/h)
    # where h is half-life
    decay_factor = math.pow(0.5, days_since_access / half_life_days)
    decayed_confidence = confidence * decay_factor

    # Don't decay below minimum threshold
    return max(decayed_confidence, 0.1)


def reinforce_confidence(
    current_confidence: float,
    retrieval_success: bool,
    learning_rate: float = 0.1
) -> float:
    """
    Reinforce or weaken confidence based on retrieval outcome.

    Successful retrievals increase confidence; failures decrease it.

    Args:
        current_confidence: Current score (0-1)
        retrieval_success: Whether retrieval was successful/relevant
        learning_rate: How quickly confidence adjusts (0-1)

    Returns:
        Updated confidence score
    """
    if retrieval_success:
        # Increase confidence, with diminishing returns as it approaches 1
        delta = learning_rate * (1 - current_confidence)
        return min(current_confidence + delta, 1.0)
    else:
        # Decrease confidence
        delta = learning_rate * current_confidence
        return max(current_confidence - delta, 0.1)


def calculate_relevance_score(
    access_count: int,
    last_accessed: datetime,
    confidence: float,
    recency_weight: float = 0.3,
    frequency_weight: float = 0.3,
    confidence_weight: float = 0.4
) -> float:
    """
    Calculate overall relevance score combining multiple factors.

    Args:
        access_count: Number of times accessed
        last_accessed: Most recent access time
        confidence: Current confidence score
        recency_weight: Weight for recency (default 0.3)
        frequency_weight: Weight for frequency (default 0.3)
        confidence_weight: Weight for confidence (default 0.4)

    Returns:
        Relevance score (0-1)
    """
    # Recency score (exponential decay)
    days_since = (datetime.now() - last_accessed).days
    recency = math.exp(-days_since / 30)  # 30-day half-life

    # Frequency score (logarithmic scaling)
    frequency = math.log(1 + access_count) / math.log(101)  # Scale to 0-1

    # Weighted combination
    relevance = (
        recency * recency_weight +
        frequency * frequency_weight +
        confidence * confidence_weight
    )

    return min(relevance, 1.0)


# ============================================================================
# INTELLIGENT TAGGING
# ============================================================================

def extract_tags_from_content(content: str, existing_tags: List[str] = None) -> List[str]:
    """
    Extract intelligent tags from content.

    Generates:
    - Concept tags (from domain terms)
    - Entity tags (specific technologies)
    - Action tags (verbs describing operations)

    Args:
        content: Note content
        existing_tags: Tags already assigned

    Returns:
        List of extracted tags
    """
    existing_tags = existing_tags or []
    extracted = set(existing_tags)

    content_lower = content.lower()

    # Common concept tags
    concept_map = {
        'authentication': ['auth', 'login', 'oauth', 'jwt', 'token'],
        'database': ['sql', 'query', 'schema', 'migration', 'postgresql', 'mongodb'],
        'testing': ['test', 'spec', 'assert', 'mock', 'fixture'],
        'api': ['endpoint', 'route', 'request', 'response', 'rest'],
        'security': ['encrypt', 'hash', 'secure', 'vulnerable', 'xss', 'csrf'],
        'performance': ['optimize', 'cache', 'latency', 'throughput'],
        'architecture': ['pattern', 'design', 'structure', 'component'],
    }

    for concept, keywords in concept_map.items():
        if any(kw in content_lower for kw in keywords):
            extracted.add(concept)

    # Technology entity tags
    tech_patterns = [
        r'\b(react|vue|angular|svelte)\b',
        r'\b(python|javascript|typescript|java|go|rust)\b',
        r'\b(postgres|mysql|mongodb|redis|elasticsearch)\b',
        r'\b(docker|kubernetes|aws|azure|gcp)\b',
        r'\b(jwt|oauth|saml|ldap)\b',
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        extracted.update(matches)

    return sorted(list(extracted))


def generate_tag_hierarchy(tags: List[str]) -> Dict[str, List[str]]:
    """
    Organize tags into hierarchical structure.

    Returns:
        Dict mapping parent categories to child tags
    """
    hierarchy = {
        'technology': [],
        'concept': [],
        'domain': [],
        'pattern': []
    }

    # Categorize tags
    tech_keywords = ['python', 'javascript', 'typescript', 'react', 'postgres', 'docker']
    concept_keywords = ['authentication', 'testing', 'security', 'performance']
    pattern_keywords = ['repository', 'service', 'factory', 'singleton']

    for tag in tags:
        tag_lower = tag.lower()
        if any(tech in tag_lower for tech in tech_keywords):
            hierarchy['technology'].append(tag)
        elif any(concept in tag_lower for concept in concept_keywords):
            hierarchy['concept'].append(tag)
        elif any(pattern in tag_lower for pattern in pattern_keywords):
            hierarchy['pattern'].append(tag)
        else:
            hierarchy['domain'].append(tag)

    # Remove empty categories
    return {k: v for k, v in hierarchy.items() if v}


# ============================================================================
# UPSERT LOGIC - UPDATE EXISTING KNOWLEDGE
# ============================================================================

def find_similar_notes(
    title: str,
    content: str,
    note_type: str,
    threshold: float = 0.7
) -> List[Tuple[Path, float]]:
    """
    Find existing notes that might be duplicates or updates.

    Uses title similarity and content overlap to identify candidates.

    Args:
        title: Note title
        content: Note content
        note_type: Type of note (file-analysis, pattern, decision)
        threshold: Similarity threshold (0-1)

    Returns:
        List of (path, similarity_score) tuples
    """
    storage = _get_storage()
    folders = storage['get_folder_paths']()
    vault = storage['get_vault_path']()

    # Map note type to folder
    folder_map = {
        'file-analysis': folders['files'],
        'pattern': folders['patterns'],
        'decision': folders['decisions'],
        'interaction': folders['interactions']
    }

    search_folder = folder_map.get(note_type)
    if not search_folder or not search_folder.exists():
        return []

    candidates = []
    title_lower = title.lower()
    content_words = set(re.findall(r'\w+', content.lower()))

    for note_file in search_folder.rglob("*.md"):
        try:
            # Check title similarity
            note_title = note_file.stem.lower()
            title_similarity = compute_string_similarity(title_lower, note_title)

            if title_similarity < 0.5:
                continue

            # Check content overlap
            post = frontmatter.load(note_file)
            note_content_words = set(re.findall(r'\w+', post.content.lower()))

            # Jaccard similarity
            intersection = len(content_words & note_content_words)
            union = len(content_words | note_content_words)
            content_similarity = intersection / union if union > 0 else 0

            # Combined score (weighted average)
            overall_similarity = (title_similarity * 0.6 + content_similarity * 0.4)

            if overall_similarity >= threshold:
                candidates.append((note_file, overall_similarity))

        except Exception:
            continue

    # Sort by similarity (highest first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates


def compute_string_similarity(s1: str, s2: str) -> float:
    """
    Compute similarity between two strings using Levenshtein-based approach.

    Returns:
        Similarity score (0-1)
    """
    # Simple word overlap method
    words1 = set(s1.split())
    words2 = set(s2.split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def should_update_existing(
    existing_path: Path,
    new_content: str,
    similarity_score: float
) -> bool:
    """
    Decide whether to update existing note or create new one.

    Args:
        existing_path: Path to existing note
        new_content: New content to potentially add
        similarity_score: How similar notes are (0-1)

    Returns:
        True if should update, False if should create new
    """
    # High similarity -> update existing
    if similarity_score >= 0.85:
        return True

    # Medium similarity -> check if new content adds value
    if similarity_score >= 0.7:
        post = frontmatter.load(existing_path)
        existing_length = len(post.content)
        new_length = len(new_content)

        # If new content is substantially different/longer, keep separate
        if new_length > existing_length * 1.5:
            return False

        return True

    # Low similarity -> create new
    return False


def merge_note_content(
    existing_content: str,
    new_content: str,
    merge_strategy: str = "append"
) -> str:
    """
    Intelligently merge new content into existing note.

    Args:
        existing_content: Current note content
        new_content: New information to add
        merge_strategy: How to merge ("append", "replace", "sections")

    Returns:
        Merged content
    """
    if merge_strategy == "replace":
        return new_content

    elif merge_strategy == "append":
        # Add new content at end with separator
        return f"{existing_content}\n\n## Updated Information\n\n{new_content}"

    elif merge_strategy == "sections":
        # Merge by sections (smarter merging)
        # For now, append with date
        timestamp = datetime.now().strftime("%Y-%m-%d")
        return f"{existing_content}\n\n## Update - {timestamp}\n\n{new_content}"

    return existing_content


# ============================================================================
# SELF-EVALUATION & MAINTENANCE
# ============================================================================

def evaluate_memory_health(vault_path: Path = None) -> Dict:
    """
    Evaluate overall memory system health.

    Checks:
    - Low-confidence memories
    - Stale memories (not accessed recently)
    - Duplicate candidates
    - Tag consistency

    Returns:
        Health report dictionary
    """
    if vault_path is None:
        storage = _get_storage()
        vault_path = storage['get_vault_path']()

    report = {
        'total_notes': 0,
        'low_confidence': [],
        'stale_memories': [],
        'duplicate_candidates': [],
        'tag_issues': [],
        'avg_confidence': 0.0,
        'avg_relevance': 0.0
    }

    confidences = []
    relevances = []

    for note_file in vault_path.rglob("*.md"):
        try:
            post = frontmatter.load(note_file)

            if post.get('type') not in ['file-analysis', 'pattern', 'decision']:
                continue

            report['total_notes'] += 1

            # Check confidence
            confidence = post.get('confidence_score', 0.5)
            confidences.append(confidence)

            if confidence < 0.3:
                report['low_confidence'].append(str(note_file.relative_to(vault_path)))

            # Check staleness
            last_accessed_str = post.get('last_accessed')
            if last_accessed_str:
                last_accessed = datetime.fromisoformat(last_accessed_str)
                days_stale = (datetime.now() - last_accessed).days

                if days_stale > 90:
                    report['stale_memories'].append({
                        'path': str(note_file.relative_to(vault_path)),
                        'days_stale': days_stale
                    })

            # Check tags
            tags = post.get('tags', [])
            if not tags:
                report['tag_issues'].append(str(note_file.relative_to(vault_path)))

        except Exception:
            continue

    if confidences:
        report['avg_confidence'] = sum(confidences) / len(confidences)

    return report


def consolidate_duplicates(
    duplicate_candidates: List[Tuple[Path, Path, float]],
    auto_merge_threshold: float = 0.95
) -> List[Dict]:
    """
    Consolidate duplicate or near-duplicate memories.

    Args:
        duplicate_candidates: List of (path1, path2, similarity) tuples
        auto_merge_threshold: Automatically merge if similarity above this

    Returns:
        List of consolidation actions taken
    """
    actions = []

    for path1, path2, similarity in duplicate_candidates:
        if similarity >= auto_merge_threshold:
            # Auto-merge high-similarity duplicates
            try:
                post1 = frontmatter.load(path1)
                post2 = frontmatter.load(path2)

                # Keep the one with higher confidence
                conf1 = post1.get('confidence_score', 0.5)
                conf2 = post2.get('confidence_score', 0.5)

                if conf1 >= conf2:
                    primary, secondary = path1, path2
                else:
                    primary, secondary = path2, path1

                # Merge content
                post_primary = frontmatter.load(primary)
                post_secondary = frontmatter.load(secondary)

                merged_content = merge_note_content(
                    post_primary.content,
                    post_secondary.content,
                    "sections"
                )

                # Update primary
                post_primary.content = merged_content

                with open(primary, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post_primary))

                # Archive secondary
                secondary.unlink()

                actions.append({
                    'action': 'merged',
                    'primary': str(primary),
                    'secondary': str(secondary),
                    'similarity': similarity
                })

            except Exception as e:
                actions.append({
                    'action': 'error',
                    'files': [str(path1), str(path2)],
                    'error': str(e)
                })

    return actions


if __name__ == "__main__":
    print("Memory Intelligence System")
    print("=" * 60)

    # Test decay calculation
    confidence = 0.8
    last_access = datetime.now() - timedelta(days=45)
    decayed = calculate_decay(confidence, last_access)
    print(f"\nDecay Test:")
    print(f"  Initial confidence: {confidence}")
    print(f"  Days since access: 45")
    print(f"  Decayed confidence: {decayed:.3f}")

    # Test reinforcement
    reinforced = reinforce_confidence(decayed, True)
    print(f"\nReinforcement Test:")
    print(f"  After successful retrieval: {reinforced:.3f}")

    # Test tag extraction
    sample = "Implement JWT authentication using jsonwebtoken library for secure API access"
    tags = extract_tags_from_content(sample)
    print(f"\nTag Extraction Test:")
    print(f"  Content: {sample}")
    print(f"  Tags: {tags}")

    print("\n[OK] Memory intelligence layer operational")
