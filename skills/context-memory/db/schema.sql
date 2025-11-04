-- PRISM Context Memory Database Schema
-- Claude-native long-term memory for codebase context
-- Version 1.0.0

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Files table: Stores file summaries and metadata
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    language TEXT,
    summary TEXT NOT NULL,
    purpose TEXT,
    complexity TEXT CHECK(complexity IN ('simple', 'moderate', 'complex')),
    last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lines_of_code INTEGER,
    dependencies TEXT, -- JSON array of file dependencies
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Functions table: Key functions/methods within files
CREATE TABLE IF NOT EXISTS functions (
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

-- Patterns table: Reusable code patterns and conventions
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    category TEXT, -- e.g., 'architecture', 'testing', 'error-handling'
    examples TEXT, -- JSON array of file paths where pattern is used
    usage_count INTEGER DEFAULT 0,
    effectiveness TEXT, -- 'effective', 'needs-review', 'deprecated'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decisions table: Architectural decisions and reasoning
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    context TEXT, -- What problem were we solving?
    alternatives_considered TEXT, -- What else did we think about?
    impact TEXT, -- What changed as a result?
    files_affected TEXT, -- JSON array of affected file paths
    decision_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    superseded_by INTEGER, -- Reference to newer decision if this is outdated
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'superseded', 'reconsidered')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (superseded_by) REFERENCES decisions(id)
);

-- Interactions table: Agent memory and learnings
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_used TEXT, -- 'dev', 'architect', 'qa', etc.
    context TEXT NOT NULL, -- What was the user asking for?
    action_taken TEXT, -- What did the agent do?
    outcome TEXT, -- How did it work out?
    learned TEXT, -- What did we learn?
    effectiveness TEXT CHECK(effectiveness IN ('successful', 'partial', 'unsuccessful')),
    user_feedback TEXT, -- Optional user feedback
    session_id TEXT, -- Group related interactions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Git context table: Commit history and refactorings
CREATE TABLE IF NOT EXISTS git_context (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT,
    commit_message TEXT NOT NULL,
    files_changed TEXT, -- JSON array of file paths
    summary TEXT NOT NULL, -- Claude's summary of what changed and why
    refactoring BOOLEAN DEFAULT 0,
    bug_fix BOOLEAN DEFAULT 0,
    feature BOOLEAN DEFAULT 0,
    author TEXT,
    commit_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Progressive disclosure state: Which docs have been loaded
CREATE TABLE IF NOT EXISTS loaded_docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill TEXT NOT NULL,
    document_path TEXT NOT NULL,
    loaded_for_context TEXT, -- What was the query/task?
    relevance_score INTEGER, -- 1-10, how useful was it?
    session_id TEXT,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Context chains: Document sequences that worked well together
CREATE TABLE IF NOT EXISTS context_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    documents_used TEXT NOT NULL, -- JSON array of document paths in order
    task_description TEXT,
    effectiveness TEXT CHECK(effectiveness IN ('highly-effective', 'effective', 'ineffective')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences: Learned preferences over time
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    preference_key TEXT NOT NULL UNIQUE,
    preference_value TEXT NOT NULL,
    context TEXT, -- When/why does this preference apply?
    confidence INTEGER DEFAULT 5, -- 1-10, how sure are we?
    last_confirmed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Queries log: Track what queries are common for optimization
CREATE TABLE IF NOT EXISTS queries_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    query_type TEXT, -- 'recall', 'recall-pattern', 'recall-file', etc.
    results_count INTEGER,
    response_time_ms INTEGER,
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_language ON files(language);
CREATE INDEX IF NOT EXISTS idx_functions_file_id ON functions(file_id);
CREATE INDEX IF NOT EXISTS idx_functions_name ON functions(name);
CREATE INDEX IF NOT EXISTS idx_patterns_name ON patterns(name);
CREATE INDEX IF NOT EXISTS idx_patterns_category ON patterns(category);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_date ON decisions(decision_date);
CREATE INDEX IF NOT EXISTS idx_interactions_skill ON interactions(skill_used);
CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_git_commit_hash ON git_context(commit_hash);
CREATE INDEX IF NOT EXISTS idx_git_commit_date ON git_context(commit_date);
CREATE INDEX IF NOT EXISTS idx_loaded_docs_skill ON loaded_docs(skill);
CREATE INDEX IF NOT EXISTS idx_loaded_docs_session ON loaded_docs(session_id);
CREATE INDEX IF NOT EXISTS idx_context_chains_session ON context_chains(session_id);
CREATE INDEX IF NOT EXISTS idx_user_prefs_key ON user_preferences(preference_key);
CREATE INDEX IF NOT EXISTS idx_queries_type ON queries_log(query_type);
CREATE INDEX IF NOT EXISTS idx_queries_session ON queries_log(session_id);

-- Full-text search support for natural language queries
-- SQLite FTS5 for fast text search
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    path,
    summary,
    purpose,
    content='files',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS patterns_fts USING fts5(
    name,
    description,
    content='patterns',
    content_rowid='id'
);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    title,
    reasoning,
    context,
    content='decisions',
    content_rowid='id'
);

-- Triggers to keep FTS tables in sync
CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, path, summary, purpose)
    VALUES (new.id, new.path, new.summary, new.purpose);
END;

CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
    DELETE FROM files_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
    UPDATE files_fts SET
        path = new.path,
        summary = new.summary,
        purpose = new.purpose
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS patterns_ai AFTER INSERT ON patterns BEGIN
    INSERT INTO patterns_fts(rowid, name, description)
    VALUES (new.id, new.name, new.description);
END;

CREATE TRIGGER IF NOT EXISTS patterns_ad AFTER DELETE ON patterns BEGIN
    DELETE FROM patterns_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS patterns_au AFTER UPDATE ON patterns BEGIN
    UPDATE patterns_fts SET
        name = new.name,
        description = new.description
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO decisions_fts(rowid, title, reasoning, context)
    VALUES (new.id, new.title, new.reasoning, new.context);
END;

CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    DELETE FROM decisions_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    UPDATE decisions_fts SET
        title = new.title,
        reasoning = new.reasoning,
        context = new.context
    WHERE rowid = new.id;
END;

-- Update timestamps automatically
CREATE TRIGGER IF NOT EXISTS update_files_timestamp
AFTER UPDATE ON files
BEGIN
    UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_patterns_timestamp
AFTER UPDATE ON patterns
BEGIN
    UPDATE patterns SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_user_preferences_timestamp
AFTER UPDATE ON user_preferences
BEGIN
    UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
