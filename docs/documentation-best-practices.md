# PRISM Documentation Best Practices

## Core Principle: Update, Don't Duplicate

**Problem:** Creating endless new documentation files leads to:
- Scattered knowledge across multiple docs
- Outdated information in old docs
- Difficulty finding the "source of truth"
- Wasted storage and indexing resources

**Solution:** Use Smart Connections to upsert existing documentation.

## Documentation Workflow with Smart Connections

### 1. Before Creating Any New Document

**Always check for existing content:**

```python
# Step 1: Query for similar content
existing = check_existing_documentation(
    topic="Authentication Patterns",
    description="JWT token validation and user session management"
)

# Step 2: If found (>70% similarity), offer to update
if existing and existing['score'] > 0.7:
    # Update existing doc instead of creating new
    update_existing_document(existing['path'], new_content)
else:
    # Create new doc only if truly unique
    create_new_document(topic, content)
```

### 2. Semantic Deduplication

Smart Connections finds documents that mean the same thing even if they use different words:

**Example:**
- Existing doc: "User Authentication System"
- New scan finds: "Login and Session Management"
- Smart Connections detects: 85% semantic overlap
- **Action:** Update existing doc, don't create duplicate

### 3. Merge Strategy for Updates

When updating existing documentation:

**A. Identify New Information**
```markdown
# Existing Doc (before)
## Overview
Basic JWT authentication

## Implementation
Using jsonwebtoken library

# New Information Found
- Refresh token rotation
- Token expiry handling
- Security best practices

# Updated Doc (after)
## Overview
Comprehensive JWT authentication with security best practices

## Implementation
Using jsonwebtoken library with refresh token rotation

## Security
- Token expiry: 15 minutes
- Refresh token rotation on each use
- Secure storage in HttpOnly cookies
```

**B. Preserve Historical Context**
- Keep "Last Updated" timestamps
- Add "Changelog" section for major updates
- Maintain frontmatter metadata

**C. Link Related Updates**
```markdown
## Related Documents
- Updated based on: [[project-scan-2025-01-05]]
- See also: [[api-security-patterns]]
```

### 4. Consolidation Opportunities

After documentation generation, check for merge candidates:

```python
# Find docs with >75% semantic overlap
opportunities = find_consolidation_opportunities()

for opp in opportunities:
    print(f"""
    Merge candidate:
    - {opp['doc1']} <-> {opp['doc2']}
    - Overlap: {opp['similarity']}%
    - Suggested: Combine into single comprehensive doc
    """)
```

**When to Consolidate:**
- Two docs cover nearly identical topics (>75% overlap)
- One doc is clearly a subset of another
- Multiple docs created from different scans of same code

**When to Keep Separate:**
- Different focus or audience (developer vs architect)
- Different time periods (historical vs current)
- Different perspectives (implementation vs design)

## Document Naming Strategy

### Use Canonical Names

Instead of:
- ❌ `auth-system-2025-01-05.md`
- ❌ `authentication-new.md`
- ❌ `jwt-auth-v2.md`

Use:
- ✅ `authentication-system.md` (single canonical doc)
- ✅ Update date in frontmatter
- ✅ Add version history in document

### Canonical Document Template

```markdown
---
type: reference
title: Authentication System
canonical: true
first_created: 2024-12-01
last_updated: 2025-01-05
version: 2.1.0
tags:
  - architecture/authentication
  - security/jwt
aliases:
  - JWT Authentication
  - Login System
  - User Auth
status: active
---

# Authentication System

> **Canonical documentation for authentication across the project**

## Changelog

### v2.1.0 (2025-01-05)
- Added refresh token rotation
- Improved security practices
- Updated from project scan

### v2.0.0 (2024-12-15)
- Migrated from session-based to JWT
- Initial JWT implementation

### v1.0.0 (2024-12-01)
- Initial session-based authentication

## Current Implementation

[Current state of authentication...]

## Historical Notes

[Important context from previous versions...]
```

## Smart Connections Integration

### Frontmatter for Intelligent Updates

```yaml
---
# Semantic metadata
type: reference
domain: architecture
topics:
  - authentication
  - security
  - user-management

# Update tracking
canonical: true              # This is the authoritative doc
supersedes:                   # Docs this replaces
  - [[old-auth-doc]]
related:                      # Related docs (not duplicates)
  - [[api-security]]
  - [[user-model]]

# Version control
version: 2.1.0
first_created: 2024-12-01
last_updated: 2025-01-05
update_frequency: quarterly  # How often to refresh

# Status
status: active              # active | draft | deprecated
review_date: 2025-04-05     # Next review
---
```

### Query Before Create Pattern

**Always use this pattern in tasks:**

```python
def document_topic(topic: str, content: str):
    """
    Document a topic, updating existing docs when possible.
    """
    # 1. Check for existing
    existing = query_smart_connections(topic)

    if existing:
        # 2. Ask user
        choice = ask_user_merge_or_create(existing, topic)

        if choice == 'merge':
            # 3. Intelligent merge
            merged_content = merge_documentation(
                existing_doc=read_file(existing['path']),
                new_content=content,
                preserve_metadata=True
            )
            write_file(existing['path'], merged_content)
            print(f"✅ Updated: {existing['path']}")
        elif choice == 'create':
            # 4. Create with cross-reference
            new_path = create_new_doc(topic, content)
            add_cross_reference(existing['path'], new_path)
            print(f"🆕 Created: {new_path} (related to {existing['path']})")
        else:  # skip
            print(f"⏭️ Skipped: Using existing {existing['path']}")
    else:
        # No existing doc found, safe to create new
        new_path = create_new_doc(topic, content)
        print(f"🆕 Created: {new_path}")
```

## Metrics to Track

### Documentation Efficiency Metrics

```python
metrics = {
    'documents_planned': 15,      # How many docs task planned to create
    'documents_updated': 8,       # How many existing docs updated
    'documents_created': 5,       # How many net new docs created
    'documents_skipped': 2,       # How many skipped (existing sufficient)
    'duplicates_prevented': 10,   # How many duplicates avoided

    # Efficiency calculation
    'reuse_rate': (8 + 2) / 15 = 67%,  # Higher is better
    'net_new_rate': 5 / 15 = 33%,      # Lower is better (means reusing existing)
}
```

**Target Metrics:**
- Reuse Rate: > 60% (updating existing docs)
- Duplicate Prevention: 100% (no accidental duplicates)
- Consolidation Opportunities: < 5% (minimal overlap between docs)

### Report at End of Documentation Task

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Documentation Efficiency Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Planned: 15 documents
✅ Updated: 8 existing docs (53%)
🆕 Created: 5 new docs (33%)
⏭️ Skipped: 2 docs (13%)
🚫 Duplicates Prevented: 10

📈 Reuse Rate: 67% (target: >60%) ✅
🎯 Efficiency: HIGH

**Benefits:**
- Kept knowledge centralized
- Avoided 10 duplicate documents
- Updated existing docs with fresh info
- Maintained single source of truth

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Best Practices Summary

### ✅ DO

- **Check existing docs** before creating new ones
- **Update canonical docs** with new information
- **Consolidate overlapping docs** when found
- **Use semantic search** to find related content
- **Track efficiency metrics** to measure improvement
- **Preserve historical context** in updates
- **Add cross-references** between related docs

### ❌ DON'T

- **Create date-stamped docs** (e.g., `auth-2025-01-05.md`)
- **Duplicate information** across multiple docs
- **Leave outdated docs** without deprecation notices
- **Skip similarity checks** to save time
- **Create new docs** when updates would suffice
- **Lose historical information** when updating

## Tools for Efficiency

### 1. Smart Connections Query

```python
# Find existing docs on topic
results = query_smart_connections("authentication patterns")
for result in results:
    print(f"{result['path']}: {result['score']}% match")
```

### 2. Similarity Checker

```python
# Check if two docs cover same topic
similarity = check_document_similarity("doc1.md", "doc2.md")
if similarity > 0.75:
    print("These docs should be merged")
```

### 3. Merge Assistant

```python
# Intelligent merge of two docs
merged = merge_documentation(
    base_doc="authentication-system.md",
    new_content=scan_results,
    strategy="append-new-sections",
    preserve=["metadata", "changelog"]
)
```

## Integration with PRISM Tasks

### All documentation tasks should:

1. **Enable Smart Connections check** in config
2. **Query before creating** each document
3. **Offer merge options** when similar docs found
4. **Track and report** efficiency metrics
5. **Suggest consolidations** at completion
6. **Update frontmatter** with version info
7. **Maintain changelog** in updated docs

### Example Task Flow

```
Step 1: Scan project ✓
Step 2: Plan documentation ✓
Step 3: Check existing docs ✓ <- SMART CONNECTIONS CHECK
    - Found 8/15 existing docs
    - Updated 8, Created 5, Skipped 2
Step 4: Generate index ✓
Step 5: Check consolidation opportunities ✓
    - Found 2 docs with 76% overlap
    - Merged into single doc
Step 6: Report efficiency ✓
    - Reuse rate: 67%
    - Net new: 5 docs (vs 15 planned)
```

---

**Remember:** The best documentation is **accurate, current, and easy to find**. Updating existing docs achieves all three better than creating new ones.

_Documentation best practices powered by PRISM™ System_
