<!-- Powered by PRISM™ System -->

# Optimize PRISM for Smart Connections Task

## Purpose

Optimize all PRISM documentation, skills, tasks, and context memory for Smart Connections plugin, enabling AI-powered semantic search and relationship discovery across all project knowledge.

## What is Smart Connections?

Smart Connections is an Obsidian plugin that:
- Uses AI embeddings to find semantically related notes
- Discovers connections between concepts across your vault
- Enables natural language search across all documentation
- Surfaces relevant context automatically based on what you're viewing

## Benefits for PRISM

1. **Enhanced Developer Experience**: Find relevant patterns, decisions, and code examples instantly
2. **Better Context Retrieval**: Skills can leverage semantic search to find related knowledge
3. **Knowledge Discovery**: Uncover hidden relationships between architecture decisions, patterns, and code
4. **Faster Onboarding**: New team members can explore relationships between concepts
5. **Improved Memory System**: Context memory becomes more intelligent and interconnected

## SEQUENTIAL Task Execution

### 1. Install and Configure Smart Connections

**[[AGENT: Execute this step first]]**

**Announce to user:** "━━━ Step 1: Smart Connections Setup ━━━"

**1.1 Verify Obsidian Installation**
- Check if Obsidian is installed
- If not, guide user to download from https://obsidian.md

**1.2 Install Smart Connections Plugin**
- Open Obsidian
- Go to Settings → Community plugins
- Search for "Smart Connections"
- Install and Enable

**1.3 Configure Smart Connections**

Recommended settings:
```yaml
Embeddings Model: OpenAI (text-embedding-3-small)
Max Results: 20
Excluded Folders:
  - .git
  - node_modules
  - .prism/.claude-temp
  - dist
  - build
```

**1.4 Create Smart Connections Config in PRISM**

Add to `.prism/core-config.yaml`:

```yaml
# Smart Connections Integration
smart_connections:
  enabled: true
  vault_path: ../docs/memory          # Main knowledge vault
  additional_vaults:                   # Additional vaults to index
    - path: ./.prism
      name: PRISM System
      include_patterns:
        - "**/*.md"
      exclude_patterns:
        - "**/node_modules/**"
        - "**/.git/**"

  # Semantic optimization settings
  semantic_tags:
    enabled: true
    auto_generate: false              # Manual tagging preferred

  frontmatter_template:
    tags: []                          # Semantic tags
    aliases: []                       # Alternative names
    related: []                       # Related document links
    type: null                        # Document type (task|checklist|skill|doc)
    domain: null                      # Domain area (architecture|development|qa)
    complexity: null                  # simple|moderate|complex
    status: draft                     # draft|active|deprecated
```

**Announce to user:** "✓ Step 1 Complete: Smart Connections configured"

### 2. Add Semantic Frontmatter to All Documents

**[[AGENT: Execute this step only after Step 1 is complete]]**

**Announce to user:** "━━━ Step 2: Adding Semantic Frontmatter ━━━"

Smart Connections uses frontmatter for enhanced semantic understanding. Add structured frontmatter to all PRISM documents.

**2.1 Frontmatter Template for Tasks**

```yaml
---
type: task
domain: [architecture|development|qa|planning]
complexity: [simple|moderate|complex]
tags:
  - prism/task
  - [domain-specific-tags]
aliases:
  - [alternative names for this task]
related:
  - [[related-task-1]]
  - [[related-checklist]]
prerequisites:
  - [prerequisite tasks or skills]
outputs:
  - [what this task produces]
status: active
last_updated: {{date}}
---
```

**Example - document-project.md:**
```yaml
---
type: task
domain: architecture
complexity: complex
tags:
  - prism/task
  - architecture/documentation
  - brownfield/analysis
  - knowledge-capture
aliases:
  - Document Project
  - Project Documentation Task
  - Brownfield Documentation
  - Codebase Analysis Task
related:
  - [[initialize-architecture]]
  - [[create-deep-research-prompt]]
  - [[architect-checklist]]
prerequisites:
  - core-config.yaml configured
  - Project root identified
outputs:
  - docs/project/index.md
  - Project structure documentation
  - Technology inventory
  - Architecture overview
status: active
last_updated: 2025-01-05
---
```

**2.2 Frontmatter Template for Checklists**

```yaml
---
type: checklist
domain: [architecture|development|qa|process]
applies_to:
  - [tasks this checklist validates]
tags:
  - prism/checklist
  - [domain-specific-tags]
aliases:
  - [alternative names]
related:
  - [[related-tasks]]
  - [[related-checklists]]
validation_level: [quick|thorough|exhaustive]
status: active
last_updated: {{date}}
---
```

**Example - architecture-validation-checklist.md:**
```yaml
---
type: checklist
domain: architecture
applies_to:
  - initialize-architecture
  - create-architecture
tags:
  - prism/checklist
  - architecture/validation
  - documentation/quality
  - completeness-check
aliases:
  - Architecture Validation
  - Architecture Quality Check
  - Architecture Completeness Checklist
related:
  - [[initialize-architecture]]
  - [[architect-checklist]]
  - [[architecture documentation]]
validation_level: exhaustive
total_items: 98
status: active
last_updated: 2025-01-05
---
```

**2.3 Frontmatter Template for Skills**

```yaml
---
type: skill
domain: [memory|planning|development|architecture]
capabilities:
  - [what this skill does]
tags:
  - prism/skill
  - [domain-specific-tags]
aliases:
  - [alternative names]
related:
  - [[related-skills]]
  - [[related-tasks]]
dependencies:
  - [required tools or libraries]
status: active
version: {{version}}
last_updated: {{date}}
---
```

**Example - context-memory/SKILL.md:**
```yaml
---
type: skill
domain: memory
capabilities:
  - Semantic memory storage
  - Context capture and retrieval
  - Pattern recognition
  - Decision logging
  - Learning consolidation
tags:
  - prism/skill
  - memory/obsidian
  - knowledge-management
  - context-capture
  - semantic-search
aliases:
  - Context Memory
  - Project Memory
  - Obsidian Memory System
  - Knowledge Vault
related:
  - [[initialize-project-memory]]
  - [[consolidate-story-learnings]]
  - [[memory-intelligence]]
dependencies:
  - python-frontmatter
  - Obsidian (optional)
status: active
version: 2.0.0
last_updated: 2025-01-05
---
```

**2.4 Frontmatter Template for Reference Docs**

```yaml
---
type: reference
domain: [architecture|development|process]
audience: [developers|architects|qa|all]
tags:
  - prism/reference
  - [topic-tags]
aliases:
  - [alternative names]
related:
  - [[related-docs]]
topics:
  - [key topics covered]
status: active
last_updated: {{date}}
---
```

**2.5 Execute Bulk Frontmatter Addition**

For each document type:
1. Scan all markdown files in respective directories
2. Check if frontmatter exists
3. If missing or incomplete, prepend frontmatter template
4. Populate with appropriate values based on document content
5. Preserve existing content

**Announce to user:** "✓ Step 2 Complete: Frontmatter added to {{count}} documents"

### 3. Create Semantic Tag Taxonomy

**[[AGENT: Execute this step only after Step 2 is complete]]**

**Announce to user:** "━━━ Step 3: Creating Tag Taxonomy ━━━"

Create a hierarchical tag system that Smart Connections can use for semantic relationships.

**3.1 Create Tag Documentation**

Create `.prism/docs/tag-taxonomy.md`:

```markdown
# PRISM Tag Taxonomy

## Document Type Tags

- `prism/task` - Executable task definitions
- `prism/checklist` - Validation checklists
- `prism/skill` - PRISM skills
- `prism/template` - Document templates
- `prism/reference` - Reference documentation
- `prism/command` - Command definitions

## Domain Tags

### Architecture
- `architecture/documentation` - Architecture docs
- `architecture/validation` - Architecture validation
- `architecture/design` - System design
- `architecture/patterns` - Architectural patterns
- `architecture/decisions` - ADRs

### Development
- `development/implementation` - Implementation tasks
- `development/testing` - Testing tasks
- `development/debugging` - Debugging processes
- `development/code-quality` - Code quality tasks
- `development/patterns` - Code patterns

### Memory & Knowledge
- `memory/storage` - Memory storage operations
- `memory/retrieval` - Memory retrieval
- `memory/obsidian` - Obsidian-specific
- `knowledge-management` - Knowledge processes
- `context-capture` - Context capturing

### Process & Workflow
- `process/initialization` - Setup tasks
- `process/validation` - Validation processes
- `process/documentation` - Documentation processes
- `workflow/git` - Git workflows
- `workflow/cicd` - CI/CD processes

### Quality Assurance
- `qa/validation` - QA validation
- `qa/testing` - Test processes
- `qa/review` - Review processes
- `qa/standards` - Quality standards

### Planning
- `planning/estimation` - Estimation tasks
- `planning/story` - Story management
- `planning/epic` - Epic management

## Complexity Tags

- `complexity/simple` - Simple, straightforward tasks
- `complexity/moderate` - Moderate complexity
- `complexity/complex` - Complex, multi-step tasks

## Status Tags

- `status/active` - Currently active and maintained
- `status/draft` - Work in progress
- `status/deprecated` - Deprecated, use alternatives

## Integration Tags

- `integration/jira` - JIRA integration
- `integration/git` - Git integration
- `integration/obsidian` - Obsidian integration
- `integration/smart-connections` - Smart Connections optimized

## Usage Guidelines

1. **Use Multiple Tags**: Documents should have 3-5 tags minimum
2. **Use Hierarchy**: Use parent/child structure (e.g., `architecture/documentation`)
3. **Be Specific**: Prefer specific tags over generic ones
4. **Consistent Naming**: Use kebab-case for multi-word tags
5. **Semantic Meaning**: Tags should represent semantic concepts, not just categories
```

**3.2 Apply Tags to All Documents**

Go through each document and apply appropriate tags based on:
- Document purpose
- Domain area
- Complexity level
- Related concepts
- Integration points

**Announce to user:** "✓ Step 3 Complete: Tag taxonomy created and applied"

### 4. Create Cross-Reference Links

**[[AGENT: Execute this step only after Step 3 is complete]]**

**Announce to user:** "━━━ Step 4: Creating Cross-References ━━━"

Smart Connections uses both explicit links and semantic similarity. Adding explicit cross-references enhances its understanding.

**4.1 Add "Related Documents" Sections**

For every major document, add a "Related Documents" section at the bottom:

```markdown
## Related Documents

### Tasks
- [[initialize-architecture]] - Create architecture documents
- [[document-project]] - Document existing projects

### Checklists
- [[architecture-validation-checklist]] - Validate architecture completeness

### Skills
- [[context-memory]] - Memory and knowledge management

### Reference
- [[tag-taxonomy]] - Tag system documentation
```

**4.2 Create Map of Content (MOC) Files**

Create high-level index files that link related documents:

**`.prism/docs/tasks-moc.md`:**
```markdown
# Tasks Map of Content

## Architecture Tasks
- [[initialize-architecture]] - Create all architecture documents
- [[document-project]] - Analyze and document projects
- [[create-architecture]] - Create architecture from PRD

## Documentation Tasks
- [[create-doc]] - Generate documents from templates
- [[shard-doc]] - Shard documents into multiple files

## Research Tasks
- [[create-deep-research-prompt]] - Generate research prompts

## Integration Tasks
- [[fetch-jira-issue]] - Fetch JIRA issue details

## Memory Tasks
- [[initialize-project-memory]] - Setup memory vault
```

**`.prism/docs/checklists-moc.md`:**
```markdown
# Checklists Map of Content

## Architecture Checklists
- [[architecture-validation-checklist]] - Validate architecture docs (98 items)
- [[architect-checklist]] - General architecture review

## Quality Checklists
- [[code-review-checklist]] - Code review validation
```

**`.prism/docs/skills-moc.md`:**
```markdown
# Skills Map of Content

## Memory & Knowledge
- [[context-memory]] - Obsidian-based context memory system

## Development
- [[dev]] - Development skill (if exists)

## Architecture
- [[architect]] - Architecture skill command
```

**4.3 Link from Root README**

Update `.prism/README.md` to reference MOC files:

```markdown
## Documentation Maps

Explore PRISM documentation by domain:

- 📋 [Tasks Map of Content](./docs/tasks-moc.md)
- ✅ [Checklists Map of Content](./docs/checklists-moc.md)
- 🎯 [Skills Map of Content](./docs/skills-moc.md)
- 📚 [Architecture Documentation](../docs/architecture/README.md)
- 🧠 [Memory System](../docs/memory/README.md)
```

**Announce to user:** "✓ Step 4 Complete: Cross-references and MOC files created"

### 5. Optimize Context Memory for Smart Connections

**[[AGENT: Execute this step only after Step 4 is complete]]**

**Announce to user:** "━━━ Step 5: Optimizing Context Memory ━━━"

The context-memory skill already uses Obsidian. Optimize its notes for Smart Connections.

**5.1 Update storage_obsidian.py Frontmatter**

Enhance the frontmatter generated by `storage_obsidian.py` to include Smart Connections-friendly metadata:

```python
# Add to frontmatter in store_file_analysis()
metadata = {
    # Existing metadata...

    # Smart Connections optimization
    'aliases': [
        file_path.replace('/', ' '),  # "src/auth/jwt.ts" → "src auth jwt.ts"
        Path(file_path).stem,          # "jwt"
        f"{language} {Path(file_path).stem}"  # "typescript jwt"
    ],
    'semantic_tags': [
        f'lang/{language}',
        f'complexity/{complexity}',
        f'file/{Path(file_path).parent.name}'  # Parent directory
    ] + [f'pattern/{p}' for p in patterns],
    'relationships': {
        'imports': dependencies,
        'patterns_used': patterns,
        'related_files': related_files
    }
}
```

**5.2 Add Semantic Connections to Patterns**

When storing patterns, include semantic relationship hints:

```python
# In store_pattern()
metadata = {
    # ... existing metadata ...
    'aliases': [
        name,
        name.replace(' ', '-').lower(),  # "Repository Pattern" → "repository-pattern"
        category + ' ' + name if category else name
    ],
    'semantic_context': {
        'category': category,
        'related_patterns': related_patterns,  # NEW
        'anti_patterns': anti_patterns,        # NEW
        'use_cases': use_cases                 # NEW
    }
}
```

**5.3 Create Pattern Relationship Map**

Create `docs/memory/PRISM-Memory/pattern-relationships.md`:

```markdown
# Pattern Relationships

## Architectural Patterns

### Repository Pattern
**Related To:**
- [[Data Access Layer]]
- [[Dependency Injection]]
- [[Unit of Work Pattern]]

**Conflicts With:**
- [[Active Record Pattern]]

**Use Cases:**
- Complex data access logic
- Multiple data sources
- Testability requirements
```

**Announce to user:** "✓ Step 5 Complete: Context memory optimized for Smart Connections"

### 6. Create Semantic Embeddings Index

**[[AGENT: Execute this step only after Step 5 is complete]]**

**Announce to user:** "━━━ Step 6: Building Semantic Index ━━━"

**6.1 Trigger Smart Connections Indexing**

In Obsidian:
1. Open Command Palette (Ctrl/Cmd + P)
2. Run: "Smart Connections: Rebuild Embeddings"
3. Wait for indexing to complete

**6.2 Verify Index Quality**

Test semantic search with sample queries:
- "How do I document a project?"
- "What validation checks exist for architecture?"
- "How does context memory work?"
- "Show me tasks related to initialization"

**6.3 Create Search Examples**

Create `.prism/docs/smart-connections-examples.md`:

```markdown
# Smart Connections Search Examples

## Finding Related Tasks

**Query:** "tasks for setting up project documentation"
**Expected Results:**
- [[initialize-architecture]]
- [[document-project]]
- [[initialize-project-memory]]

## Finding Validation Checklists

**Query:** "how to validate architecture is complete"
**Expected Results:**
- [[architecture-validation-checklist]]
- [[architect-checklist]]

## Finding Patterns and Decisions

**Query:** "architecture decisions about authentication"
**Expected Results:**
- Files in PRISM-Memory/Decisions/ tagged with "authentication"
- Patterns related to auth

## Cross-Domain Queries

**Query:** "how memory system integrates with development workflow"
**Expected Results:**
- [[context-memory]]
- [[consolidate-story-learnings]]
- Hooks related to memory capture
```

**Announce to user:** "✓ Step 6 Complete: Semantic index built and verified"

### 7. Integrate Smart Connections into PRISM Skills

**[[AGENT: Execute this step only after Step 6 is complete]]**

**Announce to user:** "━━━ Step 7: Integrating with PRISM Skills ━━━"

**7.1 Update Skills to Leverage Smart Connections**

Skills can use Smart Connections API to find relevant context:

```python
# Example integration in a PRISM skill
import requests
import json

def query_smart_connections(query: str, limit: int = 10) -> List[Dict]:
    """
    Query Smart Connections for semantically related notes.

    Requires: Smart Connections plugin with REST API enabled
    """
    api_url = "http://localhost:27123/api/search"  # Smart Connections API

    response = requests.post(api_url, json={
        "query": query,
        "limit": limit
    })

    if response.status_code == 200:
        return response.json()['results']
    return []

# Use in skills:
related_patterns = query_smart_connections("authentication patterns")
for pattern in related_patterns:
    print(f"- {pattern['title']}: {pattern['excerpt']}")
```

**7.2 Add Smart Connections Query Command**

Update `commands/architect.md`:

```yaml
commands:
  # ... existing commands ...
  - search {query}: |
      Semantic search across all PRISM documentation and memory using Smart Connections.
      Returns most relevant tasks, checklists, patterns, and decisions.
```

**Announce to user:** "✓ Step 7 Complete: Smart Connections integrated into PRISM skills"

### 8. Create Usage Documentation

**[[AGENT: Execute this step as the final step]]**

**Announce to user:** "━━━ Step 8: Creating Documentation ━━━"

Create `.prism/docs/smart-connections-guide.md`:

```markdown
# Smart Connections Integration Guide

## What is Smart Connections?

Smart Connections uses AI to find semantic relationships between notes in your PRISM documentation and memory vaults.

## Quick Start

### 1. Open Obsidian
- Navigate to your project's memory vault: `docs/memory/`
- Or open `.prism/` folder as a vault

### 2. Use Smart Connections Panel
- Click Smart Connections icon in sidebar
- View related notes for current document
- See semantic connections automatically

### 3. Semantic Search
- Press Ctrl/Cmd + P
- Type "Smart Connections: Search"
- Enter natural language query

## Common Use Cases

### Finding Related Tasks
**Scenario:** You're working on architecture and want to find related tasks.

**Method:**
1. Open any architecture document
2. Look at Smart Connections panel
3. See related tasks automatically

**Or search:** "tasks for architecture documentation"

### Discovering Patterns
**Scenario:** You're implementing authentication and want to see existing patterns.

**Method:**
1. Search: "authentication patterns in this project"
2. Smart Connections finds:
   - Stored patterns in memory
   - Related code files
   - Architecture decisions
   - Similar implementations

### Cross-Domain Discovery
**Scenario:** You want to understand how different parts of PRISM connect.

**Method:**
1. Open `.prism/docs/tasks-moc.md`
2. View Smart Connections panel
3. Discover relationships between tasks, checklists, and skills

## Advanced Usage

### Custom Queries
- "Show me all validation checklists"
- "What tasks involve Obsidian integration?"
- "Find architecture decisions about data storage"
- "Similar patterns to repository pattern"

### Graph View Integration
- Open Obsidian Graph View (Ctrl/Cmd + G)
- See visual connections between documents
- Filter by tags, types, or domains

## Tips for Best Results

1. **Keep Notes Atomic**: One concept per note works best
2. **Use Consistent Terminology**: Same terms across documents improve connections
3. **Add Rich Metadata**: More frontmatter = better semantic understanding
4. **Cross-Reference**: Explicit links enhance AI discovery
5. **Regular Indexing**: Rebuild embeddings after major changes

## Troubleshooting

### Connections Not Appearing
- Rebuild embeddings: Cmd+P → "Smart Connections: Rebuild Embeddings"
- Check frontmatter is properly formatted
- Verify files are included (not in excluded folders)

### Irrelevant Results
- Add more specific tags
- Use more descriptive titles
- Add aliases for alternative names
- Refine your query with more context

## Integration with PRISM Workflows

### During Development
- Auto-discover relevant patterns before coding
- Find similar implementations
- Locate architectural decisions

### During Architecture
- Surface related decisions
- Find connected architecture docs
- Discover pattern relationships

### During Planning
- Find similar stories
- Locate estimation patterns
- Discover related epics

## API Integration

Smart Connections provides REST API for programmatic access:

```python
# Example: Find related patterns
import requests

response = requests.post('http://localhost:27123/api/search', json={
    'query': 'authentication patterns',
    'limit': 5
})

results = response.json()['results']
for result in results:
    print(f"{result['title']}: {result['score']}")
```

## Resources

- [Smart Connections Documentation](https://smartconnections.app/)
- [Obsidian Plugin Page](https://obsidian.md/plugins?id=smart-connections)
- [PRISM Tag Taxonomy](./tag-taxonomy.md)
- [Memory System Guide](../skills/context-memory/SKILL.md)
```

**Announce to user:** "✓ Step 8 Complete: Documentation created"

### 9. Validation and Testing

**[[AGENT: Final validation step]]**

**Announce to user:** "━━━ Step 9: Validation ━━━"

**9.1 Verify All Enhancements**

- [ ] Smart Connections installed and configured
- [ ] Frontmatter added to all tasks ({{task_count}} files)
- [ ] Frontmatter added to all checklists ({{checklist_count}} files)
- [ ] Frontmatter added to all skills ({{skill_count}} files)
- [ ] Tag taxonomy created
- [ ] MOC files created (tasks, checklists, skills)
- [ ] Context memory optimized
- [ ] Semantic index built
- [ ] Integration documented
- [ ] Usage guide created

**9.2 Display Completion Summary**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Smart Connections Optimization Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Documents Enhanced:
✅ {{task_count}} tasks
✅ {{checklist_count}} checklists
✅ {{skill_count}} skills
✅ {{doc_count}} reference docs

Created:
✅ Tag taxonomy
✅ 3 MOC files
✅ Smart Connections guide
✅ Search examples

**Next Steps:**

1. 🔍 Try semantic search in Obsidian
2. 📊 View graph connections
3. 🧠 Explore related documents automatically
4. 🔗 Discover hidden relationships

**Test Queries:**
- "How do I initialize architecture?"
- "Show validation checklists"
- "What patterns exist for authentication?"
- "Find memory-related tasks"

**Resources:**
📖 Guide: .prism/docs/smart-connections-guide.md
🏷️ Tags: .prism/docs/tag-taxonomy.md
🗺️ Maps: .prism/docs/*-moc.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PRISM is now Smart Connections optimized!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Announce to user:** "✓ Step 9 Complete: Optimization validated"

## Success Criteria

- [ ] Smart Connections plugin installed
- [ ] All documents have semantic frontmatter
- [ ] Tag taxonomy created and documented
- [ ] Cross-references added throughout
- [ ] MOC files created
- [ ] Context memory optimized
- [ ] Semantic index built
- [ ] Documentation created
- [ ] Integration tested

## Maintenance

**Monthly:**
- Rebuild embeddings after major doc changes
- Review and update tag taxonomy
- Add cross-references to new documents

**Quarterly:**
- Audit frontmatter completeness
- Update MOC files
- Review semantic connection quality

---

_Smart Connections optimization powered by PRISM™ System_
