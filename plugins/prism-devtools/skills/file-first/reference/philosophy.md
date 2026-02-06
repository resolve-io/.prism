# File-First Philosophy

Why direct file access beats RAG for AI-assisted development.

## The RAG Problem

Traditional RAG (Retrieval-Augmented Generation) approaches seem logical but introduce hidden complexity:

### 1. Vector Embedding Issues

```
Source Code → Chunking → Embedding → Vector DB → Similarity Search → Context
     ^           ^          ^           ^              ^
     |           |          |           |              |
   Original   Arbitrary   Lossy     Infrastructure   Black box
   content    boundaries  transform  complexity      retrieval
```

**Problems:**
- Chunking is arbitrary - where do you split code?
- Embeddings are lossy - semantic meaning != string matching
- Vector similarity doesn't understand code structure
- Debugging retrieval failures is nearly impossible

### 2. File-First Solution

```
Source Code → Direct Read → Context
     ^            ^
     |            |
   Original   Deterministic
   content    access
```

**Benefits:**
- No intermediate representations
- Debuggable - you know exactly what the AI sees
- Fresh - always reading current file state
- Structured - respect file boundaries

## Key Insights from "File-First AI Agent"

The article validates several observations:

### "Tuning retrieval is endless"

RAG systems require constant tuning:
- Chunk size optimization
- Overlap configuration
- Embedding model selection
- Similarity thresholds
- Re-ranking strategies

File-first eliminates all of this - just read the file.

### "Chunking is an art, not science"

No principled way to chunk source code:
- Function boundaries? What about helpers?
- Class boundaries? What about partial classes?
- Import statements? Always needed but low "similarity"

File-first preserves natural boundaries - the file itself.

### "Similarity search is a black box"

When RAG returns wrong context:
- Which embedding caused the issue?
- Was the query embedded correctly?
- Is the chunk even in the index?

File-first failures are obvious - file not found, wrong path, etc.

## When RAG Might Help

File-first isn't always sufficient:

| Scenario | RAG Might Help | File-First Alternative |
|----------|----------------|------------------------|
| Millions of files | Possibly | Hierarchical Glob patterns |
| Full-text search | Possibly | Grep with good patterns |
| Semantic search | Yes | Explicit file mapping in config |
| Historical analysis | Yes | Git log + targeted reads |

## PRISM's File-First Implementation

PRISM already embodies file-first principles:

### 1. devLoadAlwaysFiles

```yaml
devLoadAlwaysFiles:
  - docs/architecture/coding-standards.md
  - docs/architecture/tech-stack.md
  - docs/architecture/source-tree.md
```

Explicit file selection, not similarity search.

### 2. Story Files as Context

Stories accumulate context:
- Requirements from epic
- Architecture decisions
- Implementation notes
- Test strategies

Passed between agents as files, not embeddings.

### 3. Direct Architecture Reading

```
SM Agent reads docs/architecture/tech-stack.md
     ↓
Creates story with tech context
     ↓
DEV Agent reads story + same architecture files
     ↓
Implements with consistent understanding
```

No RAG pipeline, no retrieval failures.

## Cost Analysis

### RAG Costs

- **Infrastructure**: Vector DB hosting, embedding API calls
- **Latency**: Embedding generation, similarity search
- **Maintenance**: Index updates, chunk re-processing
- **Debugging**: Time spent on retrieval failures

### File-First Costs

- **Tokens**: Pay for context on each query
- **Selection**: Human/agent must choose files wisely

Trade-off: Higher per-query token cost vs. lower overall complexity.

## Practical Guidelines

### Do

- Read files directly with Read tool
- Use Glob for file discovery
- Use Grep for content search
- Let story files carry context between agents
- Re-read files each session (freshness over caching)

### Don't

- Pre-index codebases before starting work
- Build vector databases for small/medium projects
- Cache file contents between sessions
- Assume previous context is still valid
- Use embeddings for code understanding

## Conclusion

File-first works because:

1. **Simplicity** - No infrastructure, no tuning
2. **Transparency** - Know exactly what the AI sees
3. **Freshness** - Always current file state
4. **Structure** - Natural file boundaries preserved
5. **Debugging** - Obvious failure modes

For most development tasks, direct file access is sufficient and far simpler than RAG. Use the file-first approach as the default, adding retrieval complexity only when demonstrated necessary.
