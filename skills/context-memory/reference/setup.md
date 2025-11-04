# PRISM Context Memory - Setup Guide

Complete setup guide for the PRISM Context Memory system.

## Overview

The Context Memory system provides Claude-native long-term memory for PRISM, storing and recalling:

- Code summaries and architecture
- Development patterns and conventions
- Architectural decisions (ADR)
- Agent learnings and interactions
- Git history context

**Key Features:**
- No embeddings or external AI systems
- Uses only Claude API for analysis
- SQLite database (single file)
- Automatic capture via hooks
- Full-text search with FTS5
- Privacy-first (all data local)

## Prerequisites

- Python 3.8+
- Claude API key
- Git (for commit context)
- SQLite 3 (usually pre-installed)

## Installation

### 1. Install Python Dependencies

```bash
# From PRISM root directory
pip install anthropic

# Or install all dependencies
pip install -r skills/context-memory/requirements.txt
```

### 2. Configure API Key

Create or edit `.env` file in PRISM root:

```bash
# Copy example
cp .env.example .env

# Edit .env and add:
ANTHROPIC_API_KEY=your-claude-api-key-here
```

Get your API key from: https://console.anthropic.com/settings/keys

### 3. Initialize Database

```bash
python skills/context-memory/utils/init_db.py
```

This will:
- Create `.prism-memory.db` in project root
- Add database to `.gitignore`
- Initialize schema with FTS5 indexes
- Display database statistics

**Expected output:**
```
🧠 PRISM Context Memory System
   Version: 1.0.0
   Database: C:\Dev\.prism\.prism-memory.db

📦 Creating database: C:\Dev\.prism\.prism-memory.db
✅ Database schema created successfully
✅ Created 18 tables

📊 Database Statistics:
   files: 0 records
   functions: 0 records
   patterns: 0 records
   decisions: 0 records
   interactions: 0 records
   git_context: 0 records
   loaded_docs: 0 records
   context_chains: 0 records
   user_preferences: 1 records

✅ Added .prism-memory.db to .gitignore

🎉 Memory system initialized!
   Database: C:\Dev\.prism\.prism-memory.db
   Size: 102400 bytes
```

### 4. Test Claude API Connection

```bash
python skills/context-memory/utils/claude_api.py
```

**Expected output:**
```
🧠 Testing Claude API connection...
✅ Claude API connection successful
```

If this fails, check your `ANTHROPIC_API_KEY` in `.env`.

### 5. Enable Automatic Capture (Optional but Recommended)

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

**Note:** If you already have hooks configured, merge these into your existing configuration.

### 6. Verify Installation

```bash
# Check database exists
ls -lh .prism-memory.db

# Check API connection
python skills/context-memory/utils/claude_api.py

# Check database integrity
python skills/context-memory/utils/init_db.py --verify
```

## Configuration

### Environment Variables

All configuration via `.env` file:

```bash
# Required
ANTHROPIC_API_KEY=your-key-here

# Optional (defaults shown)
PRISM_MEMORY_DB=.prism-memory.db
PRISM_MEMORY_AUTO_CAPTURE=true
PRISM_MEMORY_RETENTION_DAYS=365
```

### Core Config

Settings in `core-config.yaml`:

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
    - decisions
```

## Usage

### Manual Context Capture

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
    'Authentication redesign'
)
```

### Query Context

```python
from memory_ops import recall_query, recall_file, recall_decisions

# Natural language search
results = recall_query('authentication')
for r in results:
    print(f"{r['type']}: {r.get('path') or r.get('name')}")

# Specific file
file_data = recall_file('src/auth/jwt.ts')
print(f"Summary: {file_data['summary']}")

# Recent decisions
decisions = recall_decisions(days=30)
for d in decisions:
    print(f"{d['title']}: {d['reasoning']}")
```

### Via Slash Command

```
/memory
> What do we know about authentication?

> Store this as a pattern: All errors use Result<T, E> type

> Show me recent architectural decisions
```

## Docker Setup (Optional)

For containerized development:

### 1. Build Container

```bash
docker-compose build prism-memory
```

### 2. Run Interactive Shell

```bash
docker-compose run --rm prism-memory bash
```

### 3. Initialize Database in Container

```bash
docker-compose run --rm prism-memory python skills/context-memory/utils/init_db.py
```

### 4. View Database in Browser (Debug)

```bash
docker-compose --profile debug up sqlite-web
```

Open http://localhost:8080 to browse database.

## Verification Checklist

After setup, verify:

- [ ] `.prism-memory.db` exists in project root
- [ ] `.prism-memory.db` is in `.gitignore`
- [ ] `ANTHROPIC_API_KEY` set in `.env`
- [ ] Claude API test passes
- [ ] Database integrity check passes
- [ ] Can run `remember_file()` successfully
- [ ] Can run `recall_query()` successfully
- [ ] Hooks configured (optional but recommended)

## Troubleshooting

### Database Not Found

**Error:**
```
❌ Database not found: .prism-memory.db
   Run: python skills/context-memory/utils/init_db.py
```

**Solution:**
```bash
python skills/context-memory/utils/init_db.py
```

### API Key Missing

**Error:**
```
❌ ANTHROPIC_API_KEY not found in environment
   Please add to .env file:
   ANTHROPIC_API_KEY=your-key-here
```

**Solution:**
1. Create/edit `.env` file
2. Add `ANTHROPIC_API_KEY=your-key-here`
3. Get key from https://console.anthropic.com/settings/keys

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'anthropic'
```

**Solution:**
```bash
pip install anthropic
# or
pip install -r skills/context-memory/requirements.txt
```

### Database Corruption

**Error:**
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
```bash
# Backup old database
cp .prism-memory.db .prism-memory.db.backup

# Rebuild
python skills/context-memory/utils/init_db.py --rebuild
```

### Hooks Not Triggering

**Symptoms:**
- Files not being analyzed automatically
- Commits not being captured

**Check:**
1. `.claude/hooks.json` exists and is valid JSON
2. Hooks enabled in Claude Code settings
3. `PRISM_MEMORY_AUTO_CAPTURE=true` in `.env`
4. Check `.prism-memory-log.txt` for errors

### Slow Analysis

**Symptoms:**
- File analysis takes >10 seconds
- API timeouts

**Solutions:**
1. Check internet connection
2. Verify API key is valid
3. Check Anthropic status page
4. Reduce file size (only first 10K chars analyzed)

## Maintenance

### View Statistics

```bash
python -c "from memory_ops import get_memory_stats; import json; print(json.dumps(get_memory_stats(), indent=2))"
```

### Backup Database

```bash
# Simple copy
cp .prism-memory.db .prism-memory.db.backup

# Export to JSON
python -c "from memory_ops import export_memory; export_memory('backup.json')"
```

### Clear Old Data

```python
from memory_ops import clear_old_data

# Clear data older than 365 days
clear_old_data(days=365)
```

### Rebuild Database

```bash
# Backup first!
cp .prism-memory.db .prism-memory.db.backup

# Rebuild
python skills/context-memory/utils/init_db.py --rebuild
```

## Integration with PRISM Workflows

Context Memory integrates automatically with PRISM skills:

### Dev Workflow

```
/dev "implement user authentication"

# Claude automatically:
1. Recalls similar implementations
2. Queries patterns (e.g., "authentication pattern")
3. Implements using discovered patterns
4. Stores new patterns on completion
```

### Architect Workflow

```
/architect "design payment processing"

# Claude automatically:
1. Recalls previous decisions
2. Queries patterns for payment systems
3. Designs considering existing architecture
4. Stores new decisions
```

### QA Workflow

```
/qa "review authentication tests"

# Claude automatically:
1. Recalls test patterns
2. Checks similar test implementations
3. Validates against stored patterns
```

## Best Practices

1. **Let hooks capture automatically** - Most context stored without manual effort

2. **Query before implementing** - Check for existing patterns/solutions

3. **Store decisions explicitly** - Use `remember_decision()` for important choices

4. **Review stats periodically** - Run `get_memory_stats()` weekly

5. **Backup before rebuilds** - Always backup database before `--rebuild`

6. **Keep retention balanced** - Default 365 days works for most projects

7. **Use descriptive titles** - Makes searching easier later

## Security

**API Key Protection:**
- Store in `.env` (gitignored)
- Never commit to version control
- Rotate periodically

**Data Privacy:**
- All data stays local
- No external services (except Claude API)
- Database not synced to version control

**Access Control:**
- Database file has standard user permissions
- No network access required (except Claude API)

## Support

**Documentation:**
- `skills/context-memory/SKILL.md` - Quick reference
- `skills/context-memory/README.md` - Overview
- `skills/context-memory/reference/commands.md` - Command reference
- `skills/context-memory/reference/schema.md` - Database schema

**Help:**
1. Check this guide's troubleshooting section
2. Review `.prism-memory-log.txt` for errors
3. Run verification commands
4. Check PRISM issues on GitHub

---

**Ready to use Context Memory!**

Start querying: `/memory "What patterns do we use?"`
