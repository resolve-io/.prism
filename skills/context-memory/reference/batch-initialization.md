# Batch Initialization Guide

Complete guide for initializing context memory for existing codebases.

## Overview

The batch initialization script analyzes your entire existing codebase and populates the memory database with context about all files, functions, and patterns.

**When to use:**
- Starting PRISM on an existing project
- After database rebuild
- When adding a new large module
- Refreshing context after major refactor

## Quick Start

```bash
# 1. Dry run to see what would be analyzed
python skills/context-memory/utils/batch_init.py --dry-run

# 2. Run full analysis
python skills/context-memory/utils/batch_init.py

# 3. Verify results
python -c "from memory_ops import get_memory_stats; import json; print(json.dumps(get_memory_stats(), indent=2))"
```

## Command Options

```bash
python skills/context-memory/utils/batch_init.py [OPTIONS]

Options:
  --root DIR              Root directory to analyze (default: git root)
  --pattern GLOB          Glob pattern for files (e.g., "src/**/*.ts")
  --dry-run               Show what would be analyzed without analyzing
  --max-files N           Maximum number of files to analyze
  --include-existing      Reanalyze files already in database
  --analyze-patterns      Analyze and store project patterns
```

## Usage Examples

### Example 1: Analyze Entire Codebase

```bash
python skills/context-memory/utils/batch_init.py
```

**Output:**
```
🔍 Scanning codebase: C:\Dev\myproject
📊 Found 127 code files
⏱️  Estimated time: 8m

🚀 Starting analysis...
============================================================

[1/127] (0.8%) src/index.ts
🔍 Analyzing src/index.ts...
✅ Stored analysis for src/index.ts
   Summary: Main application entry point that initializes Express server...

[2/127] (1.6%) src/app.ts
🔍 Analyzing src/app.ts...
✅ Stored analysis for src/app.ts
   Summary: Express application configuration with middleware setup...

...

============================================================
✅ Analysis complete!

📊 Results:
   Total files: 127
   Analyzed: 125
   Skipped: 2
   Errors: 0
   Duration: 487.3s
   Avg time per file: 3.90s

📦 Database statistics:
   files: 125
   functions: 543
   patterns: 0
   decisions: 0
   database_size_mb: 2.34
```

### Example 2: Analyze Specific Directory

```bash
python skills/context-memory/utils/batch_init.py --pattern "src/auth/**/*.ts"
```

Analyzes only files in `src/auth/` directory.

### Example 3: Test Run First

```bash
# Analyze just 10 files to test
python skills/context-memory/utils/batch_init.py --max-files 10
```

Good for:
- Testing setup before full run
- Verifying API key works
- Checking analysis quality

### Example 4: Dry Run

```bash
python skills/context-memory/utils/batch_init.py --dry-run
```

**Output:**
```
🔍 Scanning codebase: C:\Dev\myproject
📊 Found 127 code files
⏱️  Estimated time: 8m

🔍 Files to analyze (dry run):
  1. src/index.ts (1234 bytes)
  2. src/app.ts (2345 bytes)
  3. src/auth/jwt.ts (3456 bytes)
  ... and 124 more files
```

Shows what would be analyzed without actually doing it.

### Example 5: Refresh After Refactor

```bash
# Reanalyze files already in database
python skills/context-memory/utils/batch_init.py --include-existing
```

Use when:
- Major refactoring changed many files
- Want to update all summaries
- Previous analysis was incomplete

### Example 6: Analyze Project Patterns

```bash
python skills/context-memory/utils/batch_init.py --analyze-patterns
```

Analyzes codebase structure and identifies common patterns:
- Directory structure conventions
- Naming patterns
- Common libraries/frameworks
- Import patterns

## What Gets Analyzed

### Files Included

**Languages:**
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Ruby (`.rb`)
- Go (`.go`)
- Rust (`.rs`)
- Java (`.java`)
- C# (`.cs`)
- C/C++ (`.c`, `.cpp`, `.h`, `.hpp`)
- PHP (`.php`)
- Swift (`.swift`)
- Kotlin (`.kt`)
- Scala (`.scala`)
- Clojure (`.clj`)
- Elixir (`.ex`, `.exs`)

### Directories Skipped

Automatically skips:
- `node_modules/`
- `.git/`
- `dist/`, `build/`, `out/`
- `__pycache__/`, `.pytest_cache/`
- `vendor/`, `target/`
- `.venv/`, `venv/`, `env/`
- `tmp/`, `temp/`, `logs/`
- `.idea/`, `.vscode/`
- `coverage/`

### Files Skipped

- Lock files (`package-lock.json`, `yarn.lock`, etc.)
- Very large files (>500KB)
- Binary files
- Generated files

## For Each File Analyzed

Claude generates:
1. **Summary** - One sentence description
2. **Purpose** - Main responsibility
3. **Complexity** - Simple/Moderate/Complex
4. **Key Functions** - Important functions/methods
5. **Dependencies** - Imported modules/files

Stored in database with:
- File path
- Language
- Line count
- Last analyzed timestamp

## Performance

### Time Estimates

Based on ~4 seconds per file (Claude API):

| Files | Estimated Time |
|-------|---------------|
| 10 | 40 seconds |
| 50 | 3 minutes |
| 100 | 7 minutes |
| 200 | 13 minutes |
| 500 | 33 minutes |
| 1000 | 67 minutes |
| 2000 | 2.2 hours |

**Factors affecting speed:**
- Claude API response time (2-6s per file)
- Network latency
- File complexity
- Your API rate limits

### Optimization Tips

1. **Use `--pattern` for focus:**
   ```bash
   # Just analyze src directory
   --pattern "src/**/*.ts"
   ```

2. **Test with `--max-files` first:**
   ```bash
   --max-files 10  # Quick test
   ```

3. **Run during off-hours:**
   - Overnight for large codebases
   - During lunch for medium projects

4. **Use `--dry-run` to estimate:**
   ```bash
   --dry-run  # Shows count and estimate
   ```

5. **Already-analyzed files skipped:**
   - Re-runs are fast (skips existing)
   - Only analyzes new/changed files

## Interrupting and Resuming

### Interrupt Safely

Press `Ctrl+C` to interrupt:
```
[45/127] (35.4%) src/services/payment.ts
🔍 Analyzing src/services/payment.ts...

^C
⚠️  Interrupted by user
```

Progress is saved - already analyzed files remain in database.

### Resume Analysis

Simply re-run the same command:
```bash
python skills/context-memory/utils/batch_init.py
```

Already-analyzed files are automatically skipped.

## Monitoring Progress

### Real-time Output

```
[45/127] (35.4%) src/services/payment.ts
🔍 Analyzing src/services/payment.ts...
✅ Stored analysis for src/services/payment.ts
   Summary: Payment processing service handling Stripe integration...
```

Shows:
- Current file number and total
- Percentage complete
- File being analyzed
- Generated summary

### Check Stats During Run

Open another terminal:
```bash
python -c "from memory_ops import get_memory_stats; print(get_memory_stats())"
```

## After Initialization

### Verify Results

```bash
# Database statistics
python -c "from memory_ops import get_memory_stats; import json; print(json.dumps(get_memory_stats(), indent=2))"

# Test a query
python -c "from memory_ops import recall_query; results = recall_query('authentication'); print(f'Found {len(results)} results')"

# Check specific file
python -c "from memory_ops import recall_file; data = recall_file('src/auth/jwt.ts'); print(data['summary'] if data else 'Not found')"
```

### Next Steps

1. **Enable automatic capture** (if not already):
   - Add hooks to `.claude/hooks.json`
   - See `docs/context-memory-setup.md`

2. **Start querying:**
   ```
   /memory "What patterns do we use for database access?"
   /memory "Show me authentication implementations"
   /memory "Find error handling approaches"
   ```

3. **Manual capture of patterns:**
   ```python
   from memory_ops import remember_pattern, remember_decision

   remember_pattern(
       "Repository Pattern",
       "All database access through repository classes",
       "src/repos/user-repo.ts"
   )
   ```

4. **Use in development:**
   - PRISM skills automatically query memory
   - Context used for better suggestions
   - Patterns enforced in code review

## Troubleshooting

### Rate Limit Errors

```
⚠️  Error analyzing file: rate_limit_error
```

**Solution:**
1. Wait 5-10 minutes
2. Re-run same command
3. Already-analyzed files will be skipped
4. Continue where left off

**Prevention:**
- Use `--max-files` for smaller batches
- Spread large analyses over time
- Upgrade API tier if needed

### Database Lock

```
❌ Database error: database is locked
```

**Solution:**
1. Close SQLite browser if open
2. Close other terminal sessions
3. Check for other processes using database
4. Retry analysis

### Memory Errors

```
⚠️  Memory error analyzing large-file.ts
```

**Solution:**
- Files >500KB automatically skipped
- Claude API limits content size
- Large files can be summarized manually

### API Connection Failed

```
❌ Error analyzing file: Connection timeout
```

**Solution:**
1. Check internet connection
2. Verify API key: `python skills/context-memory/utils/claude_api.py`
3. Check Anthropic status page
4. Retry failed files

### No Files Found

```
📊 Found 0 code files
❌ No code files found to analyze
```

**Solution:**
1. Check you're in correct directory
2. Use `--root` to specify directory
3. Verify files have recognized extensions
4. Check if files in skipped directories

## Advanced Usage

### Custom File Patterns

```bash
# Only TypeScript files in src
--pattern "src/**/*.ts"

# Multiple patterns (run separately)
--pattern "src/**/*.ts"
--pattern "lib/**/*.js"

# Specific subdirectory
--pattern "src/auth/**/*"
```

### Parallel Runs

For very large codebases, run parallel analyses:

```bash
# Terminal 1: Analyze src
python skills/context-memory/utils/batch_init.py --pattern "src/**/*.ts"

# Terminal 2: Analyze lib
python skills/context-memory/utils/batch_init.py --pattern "lib/**/*.ts"
```

**Note:** Ensure database can handle concurrent writes (SQLite has limits).

### Scheduled Re-analysis

Set up cron job for periodic re-analysis:

```bash
# Crontab entry: Daily at 2 AM
0 2 * * * cd /path/to/project && python skills/context-memory/utils/batch_init.py --include-existing >> /var/log/prism-memory.log 2>&1
```

Keeps context fresh as codebase evolves.

## Best Practices

1. **Start with dry run:**
   ```bash
   --dry-run
   ```
   Review before committing to full analysis.

2. **Test with small batch:**
   ```bash
   --max-files 10
   ```
   Verify setup before full run.

3. **Focus on important code:**
   ```bash
   --pattern "src/**/*.ts"
   ```
   Skip tests, configs initially.

4. **Run overnight for large codebases:**
   - 500+ files can take an hour
   - Schedule during off-hours

5. **Re-analyze periodically:**
   - After major refactors
   - Quarterly for active projects
   - Use `--include-existing`

6. **Monitor database size:**
   ```bash
   ls -lh .prism-memory.db
   ```
   Typical: 1-5MB per 100 files

7. **Backup before rebuilds:**
   ```bash
   cp .prism-memory.db .prism-memory.db.backup
   ```

## Integration with Workflows

### Pre-Development

Initialize memory before starting PRISM-driven development:

```bash
# 1. Initialize database
python skills/context-memory/utils/init_db.py

# 2. Batch analyze codebase
python skills/context-memory/utils/batch_init.py

# 3. Enable hooks
# Edit .claude/hooks.json

# 4. Start development
/dev "implement new feature"
# Now has full codebase context
```

### Post-Refactor

Refresh context after major changes:

```bash
python skills/context-memory/utils/batch_init.py --include-existing --pattern "src/refactored-module/**/*.ts"
```

### New Team Member Onboarding

Build context for learning:

```bash
# Analyze codebase
python skills/context-memory/utils/batch_init.py

# Query to learn
/memory "What are the main components?"
/memory "How does authentication work?"
/memory "What patterns do we follow?"
```

---

**Ready to initialize your project memory!**

Start with: `python skills/context-memory/utils/batch_init.py --dry-run`
