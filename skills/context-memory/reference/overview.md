# PRISM Context Memory System

Claude-native long-term memory for storing and recalling codebase context.

## Quick Start

### 1. Install Dependencies

```bash
pip install anthropic
```

### 2. Configure API Key

Add to `.env` in project root:

```bash
ANTHROPIC_API_KEY=your-claude-api-key-here
```

### 3. Initialize Database

```bash
python skills/context-memory/utils/init_db.py
```

This creates `.prism-memory.db` and adds it to `.gitignore`.

### 4. Test Connection

```bash
python skills/context-memory/utils/claude_api.py
```

Should output: `✅ Claude API connection successful`

### 5. Batch Initialize (For Existing Projects)

If you have an existing codebase, analyze it all at once:

```bash
# See what would be analyzed
python skills/context-memory/utils/batch_init.py --dry-run

# Analyze entire codebase (can take minutes to hours)
python skills/context-memory/utils/batch_init.py

# Or test with just 10 files first
python skills/context-memory/utils/batch_init.py --max-files 10
```

For new projects, skip this step - hooks will capture context as you code.

See `QUICKSTART.md` and `reference/batch-initialization.md` for details.

### 6. Enable Automatic Capture

Add hooks to `.claude/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-file-context.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/capture-commit-context.py"
          }
        ]
      }
    ]
  }
}
```

## Usage

Context memory works **automatically through existing PRISM skills**. You don't need new commands.

### Transparent Integration

```bash
# Use existing skills normally
/dev "implement user authentication"
# Dev skill automatically queries memory for similar implementations

/architect "design payment processing"
# Architect skill automatically recalls previous decisions

/qa "review authentication tests"
# QA skill automatically checks against test patterns
```

### Manual Context Operations (For Skill Integration)

```python
from memory_ops import remember_file, remember_pattern, remember_decision

# Analyze a file
remember_file('src/auth/jwt.ts', 'Core JWT implementation')

# Store a pattern
remember_pattern(
    'Repository Pattern',
    'All database access through repository classes',
    'src/repos/user-repo.ts',
    'architecture'
)

# Record a decision
remember_decision(
    'Using JWT for auth',
    'Stateless authentication scales better',
    'Authentication redesign',
    'Considered sessions but needed stateless approach'
)
```

### View Statistics

```python
from memory_ops import get_memory_stats

stats = get_memory_stats()
print(f"Files analyzed: {stats['files']}")
print(f"Patterns stored: {stats['patterns']}")
print(f"Database size: {stats['database_size_mb']:.2f} MB")
```

## How It Works

1. **Automatic Capture** (via hooks)
   - On file save → Analyze with Claude → Store summary
   - On git commit → Summarize changes → Store context

2. **Smart Retrieval** (via queries)
   - Full-text search across files, patterns, decisions
   - Claude reasons over retrieved summaries
   - No embeddings needed

3. **Progressive Disclosure**
   - Tracks which docs are loaded
   - Learns effective document chains
   - Optimizes future context loading

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your-key-here

# Optional
PRISM_MEMORY_DB=.prism-memory.db
PRISM_MEMORY_AUTO_CAPTURE=true
PRISM_MEMORY_RETENTION_DAYS=365
```

### Core Config

Add to `core-config.yaml`:

```yaml
memory:
  enabled: true
  database: .prism-memory.db
  auto_capture: true
  retention_days: 365
  capture_on:
    - file_changes
    - commits
    - story_completion
```

## File Structure

```
skills/context-memory/
├── SKILL.md                 # Main skill documentation
├── README.md                # This file
├── db/
│   └── schema.sql           # Database schema
├── utils/
│   ├── init_db.py           # Database initialization
│   ├── claude_api.py        # Claude API integration
│   └── memory_ops.py        # Core operations
└── reference/
    ├── commands.md          # Command reference
    ├── schema.md            # Schema documentation
    └── examples.md          # Usage examples
```

## Integration with PRISM Skills

Context memory enhances existing skills transparently:

**dev skill:**
- Queries memory for similar implementations before coding
- Uses stored patterns during implementation
- Records new patterns after successful completion

**architect skill:**
- Recalls previous architectural decisions during design
- Checks established patterns for consistency
- Stores new decisions with reasoning

**qa skill:**
- Recalls test patterns during review
- Checks against quality standards
- Validates consistency with conventions

**peer skill:**
- Recalls review patterns for consistency
- Applies learned preferences
- Stores review insights

**sm skill:**
- Recalls similar stories for better estimates
- Tracks estimation accuracy over time
- Improves sizing with historical data

See `reference/integration.md` for implementation details.

## Troubleshooting

### Database not found

```bash
❌ Database not found: .prism-memory.db
   Run: python skills/context-memory/utils/init_db.py
```

### API key missing

```bash
❌ ANTHROPIC_API_KEY not found in environment
   Add to .env file: ANTHROPIC_API_KEY=your-key-here
```

### Hooks not triggering

1. Check `.claude/hooks.json` exists and is valid JSON
2. Verify hooks enabled in Claude Code settings
3. Check `.prism-memory-log.txt` for errors

### Database corruption

```bash
# Verify integrity
python skills/context-memory/utils/init_db.py --verify

# Rebuild if needed
python skills/context-memory/utils/init_db.py --rebuild
```

## Architecture

**No Embeddings Required:**
- Claude reasons over text summaries
- Simpler than vector databases
- Fully Claude-native

**File-Based:**
- SQLite database = single file
- Easy backup and sync
- No server required

**Privacy First:**
- All data stays local
- Claude API only for analysis
- No external services

## Performance

**Typical Metrics:**
- Database size: 1-5 MB for 100+ files
- Query time: <100ms for most searches
- Analysis time: 2-5s per file (Claude API)

**Optimization:**
- FTS5 indexes for fast search
- Cached analysis (reanalyze only on changes)
- Async capture (doesn't block workflow)

## Best Practices

1. **Let hooks capture automatically** - Most context stored without manual effort

2. **Query before implementing** - Check for existing patterns/solutions

3. **Store decisions explicitly** - Make architectural choices searchable

4. **Review stats periodically** - Understand what's being captured

5. **Export before major changes** - Backup your context

## Documentation

- `SKILL.md` - Quick reference (<2k tokens)
- `reference/commands.md` - Complete command reference
- `reference/schema.md` - Database schema details
- `reference/examples.md` - Usage examples

## Support

Issues? Questions?

1. Check troubleshooting section above
2. Review `.prism-memory-log.txt` for errors
3. Verify setup with test commands
4. Open issue in PRISM repository
