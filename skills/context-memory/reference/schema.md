# Context Memory Database Schema

Complete reference for the SQLite database schema.

## Overview

The context memory database uses SQLite with FTS5 (Full-Text Search) extensions for fast text search. The schema is designed to store:

- Code summaries and analysis
- Architectural decisions
- Development patterns
- Agent learnings
- Git history context
- Progressive disclosure state

## Core Tables

### files

Stores file summaries and metadata.

```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    language TEXT,
    summary TEXT NOT NULL,
    purpose TEXT,
    complexity TEXT CHECK(complexity IN ('simple', 'moderate', 'complex')),
    last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lines_of_code INTEGER,
    dependencies TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Columns:**
- `path`: Unique file path (primary key for lookups)
- `language`: Programming language (python, typescript, etc.)
- `summary`: Claude-generated one-sentence summary
- `purpose`: Main responsibility of this file
- `complexity`: simple/moderate/complex
- `dependencies`: JSON array of imported modules/files
- `last_analyzed`: When Claude last analyzed this file

**Indexes:**
- `path` (unique)
- `language`

**FTS5:** `files_fts` on `path`, `summary`, `purpose`

### functions

Key functions/methods within files.

```sql
CREATE TABLE functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    signature TEXT,
    purpose TEXT NOT NULL,
    complexity TEXT CHECK(complexity IN ('simple', 'moderate', 'complex')),
    line_start INTEGER,
    line_end INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);
```

**Relationships:**
- Belongs to `files` via `file_id`
- CASCADE delete when file deleted

**Indexes:**
- `file_id`
- `name`

### patterns

Reusable code patterns and conventions.

```sql
CREATE TABLE patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category TEXT,
    examples TEXT,  -- JSON array of file paths
    usage_count INTEGER DEFAULT 0,
    effectiveness TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Categories:**
- `architecture`
- `testing`
- `error-handling`
- `api`
- `data`

**Effectiveness:**
- `effective` - Works well
- `needs-review` - Revisit this pattern
- `deprecated` - Don't use anymore

**Indexes:**
- `name` (unique)
- `category`

**FTS5:** `patterns_fts` on `name`, `description`

### decisions

Architectural decisions and reasoning (ADR-like).

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    context TEXT,
    alternatives_considered TEXT,
    impact TEXT,
    files_affected TEXT,  -- JSON array
    decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    superseded_by INTEGER,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'superseded', 'reconsidered')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (superseded_by) REFERENCES decisions(id)
);
```

**Status:**
- `active` - Current decision in effect
- `superseded` - Replaced by newer decision
- `reconsidered` - Under review

**Relationships:**
- Self-referential: `superseded_by` points to newer decision

**Indexes:**
- `status`
- `decision_date`

**FTS5:** `decisions_fts` on `title`, `reasoning`, `context`

### interactions

Agent memory and learnings from interactions.

```sql
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_used TEXT,
    context TEXT NOT NULL,
    action_taken TEXT,
    outcome TEXT,
    learned TEXT,
    effectiveness TEXT CHECK(effectiveness IN ('successful', 'partial', 'unsuccessful')),
    user_feedback TEXT,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Skills:**
- `dev`, `architect`, `qa`, `sm`, `peer`, `support`

**Effectiveness:**
- `successful` - Goal achieved
- `partial` - Some success
- `unsuccessful` - Failed

**Indexes:**
- `skill_used`
- `session_id`

### git_context

Git commit history and refactoring context.

```sql
CREATE TABLE git_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT,
    commit_message TEXT NOT NULL,
    files_changed TEXT,  -- JSON array
    summary TEXT NOT NULL,
    refactoring BOOLEAN DEFAULT 0,
    bug_fix BOOLEAN DEFAULT 0,
    feature BOOLEAN DEFAULT 0,
    author TEXT,
    commit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Classification:**
- `refactoring` - Code restructure
- `bug_fix` - Bug fix
- `feature` - New functionality

**Indexes:**
- `commit_hash`
- `commit_date`

## Supporting Tables

### loaded_docs

Tracks which docs have been loaded (progressive disclosure).

```sql
CREATE TABLE loaded_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT NOT NULL,
    document_path TEXT NOT NULL,
    loaded_for_context TEXT,
    relevance_score INTEGER,  -- 1-10
    session_id TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `skill`
- `session_id`

### context_chains

Document sequences that work well together.

```sql
CREATE TABLE context_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    documents_used TEXT NOT NULL,  -- JSON array
    task_description TEXT,
    effectiveness TEXT CHECK(effectiveness IN ('highly-effective', 'effective', 'ineffective')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `session_id`

### user_preferences

Learned user preferences over time.

```sql
CREATE TABLE user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_key TEXT NOT NULL UNIQUE,
    preference_value TEXT NOT NULL,
    context TEXT,
    confidence INTEGER DEFAULT 5,  -- 1-10
    last_confirmed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `preference_key` (unique)

### queries_log

Query analytics for optimization.

```sql
CREATE TABLE queries_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_type TEXT,
    results_count INTEGER,
    response_time_ms INTEGER,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- `query_type`
- `session_id`

## Full-Text Search (FTS5)

### files_fts

```sql
CREATE VIRTUAL TABLE files_fts USING fts5(
    path,
    summary,
    purpose,
    content='files',
    content_rowid='id'
);
```

**Triggers:** Auto-sync on INSERT/UPDATE/DELETE

### patterns_fts

```sql
CREATE VIRTUAL TABLE patterns_fts USING fts5(
    name,
    description,
    content='patterns',
    content_rowid='id'
);
```

### decisions_fts

```sql
CREATE VIRTUAL TABLE decisions_fts USING fts5(
    title,
    reasoning,
    context,
    content='decisions',
    content_rowid='id'
);
```

## Automatic Updates

### Timestamp Triggers

```sql
CREATE TRIGGER update_files_timestamp
AFTER UPDATE ON files
BEGIN
    UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

Similar triggers for:
- `patterns`
- `user_preferences`

### FTS Sync Triggers

Auto-sync FTS tables when data changes:

```sql
CREATE TRIGGER files_ai AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, path, summary, purpose)
    VALUES (new.id, new.path, new.summary, new.purpose);
END;
```

## Relationships

```
files (1) ──> (N) functions
    └─> path referenced in patterns.examples (JSON)
    └─> path referenced in git_context.files_changed (JSON)

decisions (1) ──> (1) decisions (superseded_by)
    └─> files_affected (JSON)

interactions
    └─> session_id groups related interactions

loaded_docs ──> context_chains (via session_id)
```

## JSON Fields

Several fields store JSON arrays:

**files.dependencies:**
```json
["jsonwebtoken", "bcrypt", "./utils/crypto"]
```

**patterns.examples:**
```json
["src/repos/user-repo.ts", "src/repos/post-repo.ts"]
```

**decisions.files_affected:**
```json
["src/auth/jwt.ts", "src/middleware/auth.ts"]
```

**git_context.files_changed:**
```json
["src/models/user.ts", "src/repos/user-repo.ts"]
```

**context_chains.documents_used:**
```json
["skills/dev/SKILL.md", "skills/dev/reference/workflow.md"]
```

## Query Patterns

### Find files by language

```sql
SELECT path, summary FROM files
WHERE language = 'typescript'
ORDER BY last_analyzed DESC;
```

### Find patterns by category

```sql
SELECT name, description, usage_count FROM patterns
WHERE category = 'architecture'
ORDER BY usage_count DESC;
```

### Find active decisions

```sql
SELECT title, reasoning, decision_date FROM decisions
WHERE status = 'active'
ORDER BY decision_date DESC;
```

### Full-text search across all

```sql
-- Files
SELECT f.* FROM files_fts JOIN files f ON files_fts.rowid = f.id
WHERE files_fts MATCH 'authentication'
ORDER BY rank;

-- Patterns
SELECT p.* FROM patterns_fts JOIN patterns p ON patterns_fts.rowid = p.id
WHERE patterns_fts MATCH 'authentication'
ORDER BY rank;

-- Decisions
SELECT d.* FROM decisions_fts JOIN decisions d ON decisions_fts.rowid = d.id
WHERE decisions_fts MATCH 'authentication'
ORDER BY rank;
```

### Find related context

```sql
-- Files that import a module
SELECT path, summary FROM files
WHERE json_extract(dependencies, '$') LIKE '%express%';

-- Patterns with examples
SELECT name, description FROM patterns
WHERE json_array_length(examples) > 0;

-- Recent commits by author
SELECT commit_message, commit_date FROM git_context
WHERE author = 'John Doe'
ORDER BY commit_date DESC
LIMIT 10;
```

## Maintenance

### Vacuum database

```sql
VACUUM;
```

### Rebuild FTS indexes

```sql
INSERT INTO files_fts(files_fts) VALUES('rebuild');
INSERT INTO patterns_fts(patterns_fts) VALUES('rebuild');
INSERT INTO decisions_fts(decisions_fts) VALUES('rebuild');
```

### Check integrity

```sql
PRAGMA integrity_check;
```

### Database statistics

```sql
SELECT
    name,
    (SELECT COUNT(*) FROM sqlite_master WHERE type='table') as table_count,
    page_size * page_count / 1024.0 / 1024.0 as size_mb
FROM pragma_page_count(), pragma_page_size();
```
