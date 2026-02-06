# File-First Quick Reference

Setup guide and common usage examples.

## Setup

No setup required. The file-first approach uses Claude Code's built-in tools:

- **Read** - Read file contents directly
- **Glob** - Find files by pattern
- **Grep** - Search file contents

## Usage Examples

### 1. Analyze Unknown Codebase

```bash
# Run analyzer to detect project type
python analyze_codebase.py /path/to/repo

# Output shows:
# - Project type (dotnet_backend, typescript_fullstack, etc.)
# - Key files to read first
# - Suggested read order
```

### 2. Load Context for Story

```markdown
## Context Loading Checklist

1. [ ] Read story file
2. [ ] Read related epic (from story's epic_reference)
3. [ ] Read devLoadAlwaysFiles from core-config.yaml
4. [ ] Read files in story's File List
5. [ ] Search for relevant code with Grep/Glob
```

### 3. Validate File-First Compliance

```bash
# Check if recent agent session followed principles
python validate_file_first.py --session-log /path/to/log
```

## Quick Decisions

| Scenario | Action |
|----------|--------|
| Need info about codebase | Run `analyze_codebase.py` |
| Starting new story | Read story file + devLoadAlwaysFiles |
| Unknown file location | Use Glob with broad pattern |
| Unknown content location | Use Grep with keyword |
| Need architecture context | Read `docs/architecture/*.md` |
| Multiple repos | Run analyzer on each separately |

## File Read Priority

Always read in this order:

1. **Story file** - Single source of truth for current work
2. **Epic file** - Parent context and requirements
3. **Architecture docs** - Patterns and standards
4. **Source code** - Actual implementation files
5. **Tests** - Existing test patterns

## Common Patterns

### Find Entry Point

```bash
# .NET
Glob: "**/Program.cs"

# TypeScript/Node
Glob: "**/index.ts" or "**/main.ts"

# Python
Glob: "**/main.py" or "**/__main__.py"
```

### Find Configuration

```bash
# .NET
Glob: "**/appsettings*.json"

# Node
Glob: "**/package.json"

# Python
Glob: "**/pyproject.toml" or "**/setup.py"
```

### Find Tests

```bash
# .NET
Glob: "**/*Tests.cs" or "**/*Test.cs"

# TypeScript
Glob: "**/*.test.ts" or "**/*.spec.ts"

# Python
Glob: "**/test_*.py" or "**/*_test.py"
```

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Wrong | Correct Approach |
|--------------|----------------|------------------|
| Pre-building indexes | Stale context, overhead | Read directly |
| Relying on summaries | Information loss | Read full files |
| Assuming file exists | Hallucination risk | Check with Glob first |
| Guessing file contents | Incorrect context | Always read |
| Using cached context | May be outdated | Re-read each session |

## Related Skills

- **jira** - Fetch ticket context to combine with file-first codebase analysis
- **document-project** - Create documentation from file-first analysis
