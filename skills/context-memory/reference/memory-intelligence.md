# Memory Intelligence System

Advanced features for persistent, self-improving memory with decay, self-evaluation, and intelligent upsert.

## Overview

The PRISM Context Memory system implements research-backed techniques for AI memory management:

1. **Memory Decay**: Confidence scores decay following the Ebbinghaus forgetting curve
2. **Self-Evaluation**: System tracks retrieval success and adjusts confidence
3. **Intelligent Upsert**: Updates existing knowledge rather than creating duplicates
4. **Confidence Scoring**: Increases with successful use, decays over time
5. **Rich Tagging**: Automatically extracts semantic tags from content

## Core Concepts

### 1. Confidence Scoring

Every memory has a `confidence_score` (0-1) that represents reliability:

**Initial Confidence**: `0.5` (neutral start)

**Reinforcement**: Score increases when memory is successfully retrieved
```python
# After successful retrieval
new_confidence = old_confidence + (learning_rate * (1 - old_confidence))
# With learning_rate=0.1, 0.5 → 0.55 → 0.595 → 0.636 ...
```

**Decay**: Score decreases over time following exponential decay
```python
# Ebbinghaus forgetting curve
C(t) = C₀ * (0.5)^(t/h)
# Where h = half-life (default 30 days)
```

**After 20 successful retrievals**: Confidence reaches ~84% (similar to ReasoningBank)

### 2. Memory Decay Model

Memories fade unless reinforced through use:

```
Day 0:  Confidence = 0.80 (just created)
Day 15: Confidence = 0.76 (slight decay)
Day 30: Confidence = 0.40 (50% decay - half-life)
Day 60: Confidence = 0.20 (further decay)
Day 90: Confidence = 0.10 (minimum threshold)
```

**Reinforcement resets decay**:
- Each successful retrieval increases confidence
- Resets last_accessed timestamp
- Prevents valuable memories from fading

### 3. Intelligent Upsert

System updates existing notes rather than creating duplicates:

**Detection**: Checks for similar existing notes before creating
- Title similarity using word overlap
- Content similarity using Jaccard index
- Combined weighted score (title: 60%, content: 40%)

**Decision Logic**:
- Similarity ≥ 85%: Always update existing
- Similarity 70-85%: Update if new content isn't substantially longer
- Similarity < 70%: Create new note

**Merging Strategies**:
- **Sections**: Append new content with timestamp separator
- **Replace**: Overwrite old content entirely
- **Append**: Add to end with clear marker

### 4. Rich Tagging Strategy

Auto-generated tags for better discoverability:

**Concept Tags**: Domain-level categories
- `authentication`, `database`, `testing`, `api`, `security`

**Entity Tags**: Specific technologies
- `jwt`, `postgresql`, `react`, `docker`, `typescript`

**Relationship Tags**: Connections
- `implements`, `uses`, `extends`, `replaces`

**Hierarchical Organization**:
```yaml
tags:
  technology:
    - typescript
    - postgresql
  concept:
    - authentication
    - security
  pattern:
    - repository
```

### 5. Access Tracking

Every note tracks usage patterns:

```yaml
confidence_score: 0.75      # Current reliability
access_count: 12            # Times retrieved
last_accessed: 2025-11-04   # Most recent use
last_modified: 2025-11-01   # Last update
analyzed_at: 2025-10-15     # Original creation
relevance_score: 0.82       # Combined metric
```

**Relevance Score** combines:
- Recency: How recently accessed (exponential decay)
- Frequency: How often accessed (logarithmic scaling)
- Confidence: Current reliability score
- Formula: `0.3*recency + 0.3*frequency + 0.4*confidence`

## Usage

### Automatic Intelligence

Intelligence features work automatically:

```python
from storage_obsidian import store_file_analysis, recall_query

# Store analysis (intelligence automatically applied)
store_file_analysis(
    file_path="src/auth/jwt.ts",
    summary="JWT authentication service",
    purpose="Secure token-based auth",
    complexity="moderate",
    language="typescript",
    lines_of_code=150,
    dependencies=["jsonwebtoken"]
)
# Result: If similar note exists, updates it instead of creating duplicate
# Automatically extracts tags: ['authentication', 'jwt', 'security', 'typescript']
# Adds metadata: confidence=0.5, access_count=0, last_accessed=now

# Query with automatic tracking
results = recall_query("authentication")
# Result: Updates access_count and last_accessed for retrieved notes
# Reinforces confidence scores
# Applies decay to stale memories
```

### Explicit Intelligence Control

Advanced usage with direct control:

```python
from memory_intelligence import (
    calculate_decay,
    reinforce_confidence,
    find_similar_notes,
    evaluate_memory_health
)

# Check memory decay
from datetime import datetime, timedelta
confidence = 0.8
last_access = datetime.now() - timedelta(days=45)
decayed = calculate_decay(confidence, last_access)
print(f"Decayed from {confidence} to {decayed}")

# Find similar notes before creating
similar = find_similar_notes(
    title="JWT Authentication Pattern",
    content="Implementation using jsonwebtoken...",
    note_type="pattern",
    threshold=0.7
)

for path, similarity in similar:
    print(f"Found similar: {path} ({similarity:.2f})")

# Evaluate memory health
health = evaluate_memory_health()
print(f"Low confidence notes: {len(health['low_confidence'])}")
print(f"Stale memories: {len(health['stale_memories'])}")
print(f"Average confidence: {health['avg_confidence']:.2f}")
```

## Metadata Structure

### Enhanced File Analysis Note

```yaml
---
type: file-analysis
file_path: src/auth/jwt.ts
language: typescript
complexity: moderate

# Intelligence metadata
confidence_score: 0.75       # Reliability (0-1)
access_count: 8              # Retrieval count
last_accessed: 2025-11-04    # Last retrieval
last_modified: 2025-11-02    # Last update
analyzed_at: 2025-10-15      # Creation date
relevance_score: 0.82        # Combined metric

# Rich tagging
tags:
  - authentication
  - jwt
  - security
  - typescript
  - api
  - code-analysis
---

# src/auth/jwt.ts
...
```

### Enhanced Pattern Note

```yaml
---
type: pattern
category: architecture
name: Repository Pattern

# Intelligence metadata
confidence_score: 0.89       # High confidence after many uses
access_count: 23             # Frequently retrieved
usage_count: 15              # Times applied in code
last_accessed: 2025-11-04
created_at: 2025-09-01
updated_at: 2025-10-15

# Rich tagging
tags:
  technology:
    - typescript
    - postgresql
  concept:
    - architecture
    - data-access
  pattern:
    - repository
    - separation-of-concerns
---

# Repository Pattern
...
```

## Self-Evaluation

### Health Metrics

Run periodic health checks:

```python
from memory_intelligence import evaluate_memory_health

health = evaluate_memory_health()

# Total notes in system
print(f"Total: {health['total_notes']}")

# Low confidence (< 0.3)
for note in health['low_confidence']:
    print(f"Low confidence: {note}")

# Stale (not accessed in 90+ days)
for memory in health['stale_memories']:
    print(f"Stale: {memory['path']} ({memory['days_stale']} days)")

# Duplicate candidates
for path1, path2, similarity in health['duplicate_candidates']:
    print(f"Possible duplicate: {path1} ~ {path2} ({similarity:.2f})")

# System averages
print(f"Avg confidence: {health['avg_confidence']:.2f}")
print(f"Avg relevance: {health['avg_relevance']:.2f}")
```

### Consolidation

Merge duplicate or near-duplicate memories:

```python
from memory_intelligence import consolidate_duplicates

# Find and merge duplicates
duplicates = [
    (path1, path2, 0.95),  # High similarity
    (path3, path4, 0.92),
]

actions = consolidate_duplicates(
    duplicates,
    auto_merge_threshold=0.90  # Auto-merge above 90%
)

for action in actions:
    if action['action'] == 'merged':
        print(f"Merged: {action['secondary']} → {action['primary']}")
```

## Best Practices

### 1. Update Rather Than Create

Always check for existing knowledge:

```python
# BAD: Creates duplicate every time
store_pattern("Repository Pattern", "Data access pattern...")

# GOOD: System automatically checks and updates
# (handled automatically by storage layer)
```

### 2. Rich, Consistent Tags

Use hierarchical tags for better organization:

```python
tags = [
    'typescript',           # Technology
    'authentication',       # Concept
    'jwt',                 # Entity
    'security',            # Concept
    'repository',          # Pattern
]
```

### 3. Query to Reinforce

Regular queries strengthen valuable memories:

```python
# Query patterns before implementing
results = recall_query("authentication patterns")
# Each retrieval reinforces confidence of relevant memories
```

### 4. Periodic Maintenance

Run health checks monthly:

```python
# Monthly maintenance script
health = evaluate_memory_health()

# Archive low-confidence, stale memories
if len(health['low_confidence']) > 50:
    print("Consider consolidating or archiving low-confidence notes")

# Consolidate duplicates
if len(health['duplicate_candidates']) > 10:
    consolidate_duplicates(health['duplicate_candidates'])
```

### 5. Let Confidence Guide Decisions

Trust high-confidence memories more:

```python
results = recall_query("authentication")

for result in results:
    confidence = result['confidence']

    if confidence > 0.8:
        print(f"High confidence: {result['title']}")
        # Use this memory reliably
    elif confidence > 0.5:
        print(f"Medium confidence: {result['title']}")
        # Use with some caution
    else:
        print(f"Low confidence: {result['title']}")
        # Verify before using
```

## Configuration

Tune intelligence parameters in `.env`:

```bash
# Memory decay settings
PRISM_MEMORY_DECAY_HALF_LIFE=30       # Days for 50% decay
PRISM_MEMORY_MIN_CONFIDENCE=0.1       # Minimum confidence floor

# Reinforcement settings
PRISM_MEMORY_LEARNING_RATE=0.1        # How quickly confidence adjusts

# Upsert thresholds
PRISM_MEMORY_SIMILARITY_THRESHOLD=0.7  # Min similarity for update
PRISM_MEMORY_AUTO_MERGE_THRESHOLD=0.85 # Auto-merge above this

# Maintenance
PRISM_MEMORY_STALE_DAYS=90            # Days before considering stale
PRISM_MEMORY_HEALTH_CHECK_INTERVAL=30  # Days between health checks
```

## Research Background

This system implements concepts from:

1. **Ebbinghaus Forgetting Curve** (1885)
   - Memory decay follows exponential function
   - Reinforcement prevents forgetting

2. **Spaced Repetition Systems**
   - Successful retrieval strengthens memory
   - Confidence increases with each use

3. **ReasoningBank** (2025)
   - Patterns reach 84% confidence after 20 uses
   - Self-updating memory system

4. **OpenMemory** (2025)
   - Automatic decay unless reinforced
   - ~95% recall at scale

## Benefits

**Prevents Memory Bloat**: Updates existing knowledge rather than accumulating duplicates

**Quality Over Quantity**: High-confidence memories are more reliable

**Learns Over Time**: System gets smarter with use

**Self-Cleaning**: Low-value memories naturally fade

**Better Discovery**: Rich tags and relevance scoring

**Maintains Currency**: Recent memories have higher relevance

**Measurable Health**: Can track and optimize memory system

---

**Version**: 1.6.0 with Memory Intelligence and Post-Story Learning

**See Also**:
- [Obsidian Integration](./obsidian.md)
- [Architecture Overview](./architecture.md)
- [API Reference](./commands.md)
