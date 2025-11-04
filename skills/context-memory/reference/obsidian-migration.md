# Obsidian Migration Design

## Overview

Migrate PRISM Context Memory from SQLite to Obsidian markdown notes for human-readable, linkable knowledge management.

## Vault Structure

```
<OBSIDIAN_VAULT>/
├── PRISM-Memory/                    # Root folder for PRISM context
│   ├── Files/                       # File analyses
│   │   ├── src/
│   │   │   ├── auth/
│   │   │   │   └── jwt.ts.md
│   │   │   └── database/
│   │   │       └── connection.py.md
│   │   └── tests/
│   ├── Patterns/                    # Reusable patterns
│   │   ├── Architecture/
│   │   │   ├── Repository Pattern.md
│   │   │   └── Service Layer.md
│   │   ├── Testing/
│   │   │   └── Integration Test Setup.md
│   │   └── Security/
│   │       └── JWT Authentication.md
│   ├── Decisions/                   # Architectural decisions
│   │   ├── 2025-01-15 Use JWT for Auth.md
│   │   ├── 2025-02-03 PostgreSQL vs MongoDB.md
│   │   └── 2025-03-10 Microservices Architecture.md
│   ├── Commits/                     # Git commit context
│   │   ├── 2025-01/
│   │   │   ├── abc1234-add-authentication.md
│   │   │   └── def5678-refactor-database.md
│   │   └── 2025-02/
│   ├── Interactions/                # Agent learnings
│   │   ├── 2025-01-15-auth-implementation.md
│   │   └── 2025-02-20-testing-strategy.md
│   ├── Preferences/                 # User preferences
│   │   └── coding-style.md
│   └── Index/                       # Meta notes
│       ├── README.md                # Vault overview
│       ├── File Index.md            # MOC for files
│       ├── Pattern Index.md         # MOC for patterns
│       └── Decision Log.md          # Chronological decisions
```

## Markdown Format

### File Analysis Note

**Path:** `PRISM-Memory/Files/<relative-path>.md`

```markdown
---
type: file-analysis
file_path: src/auth/jwt.ts
language: typescript
complexity: moderate
lines_of_code: 150
analyzed_at: 2025-01-15T10:30:00Z
last_modified: 2025-01-15T10:00:00Z
dependencies:
  - jsonwebtoken
  - bcrypt
  - express
tags:
  - authentication
  - security
  - backend
---

# src/auth/jwt.ts

## Summary
JWT token generation and validation service for user authentication.

## Purpose
Provides secure token-based authentication with configurable expiration and refresh token support.

## Key Functions

### `generateToken(userId: string): Promise<string>`
- **Purpose:** Creates JWT access token for authenticated user
- **Complexity:** Simple
- **Signature:** `async function generateToken(userId: string): Promise<string>`

### `verifyToken(token: string): Promise<JWTPayload>`
- **Purpose:** Validates JWT token and extracts payload
- **Complexity:** Simple
- **Signature:** `async function verifyToken(token: string): Promise<JWTPayload>`

### `refreshToken(refreshToken: string): Promise<TokenPair>`
- **Purpose:** Generates new access token from valid refresh token
- **Complexity:** Moderate
- **Signature:** `async function refreshToken(refreshToken: string): Promise<TokenPair>`

## Related Notes

- [[Patterns/Security/JWT Authentication]]
- [[Decisions/2025-01-15 Use JWT for Auth]]
- [[Files/src/auth/middleware.ts]]

## Dependencies

```typescript
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import { Request, Response } from 'express';
```
```

### Pattern Note

**Path:** `PRISM-Memory/Patterns/<category>/<name>.md`

```markdown
---
type: pattern
category: architecture
created_at: 2025-01-15T10:30:00Z
updated_at: 2025-01-20T14:00:00Z
usage_count: 5
tags:
  - architecture
  - data-access
  - separation-of-concerns
---

# Repository Pattern

## Description
Encapsulates data access logic in repository classes, providing a clean separation between business logic and data persistence.

## When to Use
- When you need to abstract database operations
- When supporting multiple data sources
- When testing requires mocking data access

## Example Implementation
[[Files/src/repositories/user-repository.ts]]

## Structure

```typescript
interface IUserRepository {
  findById(id: string): Promise<User | null>;
  findByEmail(email: string): Promise<User | null>;
  save(user: User): Promise<User>;
  delete(id: string): Promise<void>;
}

class UserRepository implements IUserRepository {
  // Implementation details...
}
```

## Benefits
- **Testability:** Easy to mock for unit tests
- **Maintainability:** Changes to data layer isolated
- **Flexibility:** Can swap data sources without changing business logic

## Trade-offs
- Additional abstraction layer
- More files to maintain
- Can be over-engineering for simple CRUD

## Related Patterns
- [[Patterns/Architecture/Service Layer]]
- [[Patterns/Testing/Repository Mocking]]

## Used In
- [[Files/src/repositories/user-repository.ts]]
- [[Files/src/repositories/post-repository.ts]]
- [[Files/src/repositories/comment-repository.ts]]

## Related Decisions
- [[Decisions/2025-01-10 Adopt Repository Pattern]]
```

### Decision Note

**Path:** `PRISM-Memory/Decisions/<date> <title>.md`

```markdown
---
type: decision
decision_date: 2025-01-15
status: accepted
impact: high
tags:
  - authentication
  - security
  - architecture
---

# Use JWT for Authentication

## Decision
Implement JWT (JSON Web Tokens) for stateless authentication instead of session-based authentication.

## Context
Building a REST API that needs to scale horizontally. Current session-based auth requires sticky sessions or shared session storage.

## Reasoning
1. **Stateless:** No server-side session storage needed
2. **Scalability:** Works seamlessly with load balancers
3. **Mobile-friendly:** Easy to implement in mobile apps
4. **Standard:** Well-established protocol with good library support

## Alternatives Considered

### Session-Based Authentication
**Pros:** Simpler to revoke, smaller payload
**Cons:** Requires shared storage (Redis), sticky sessions, or session replication
**Why Rejected:** Adds infrastructure complexity for horizontal scaling

### OAuth 2.0 + OpenID Connect
**Pros:** Industry standard, rich feature set
**Cons:** Overkill for internal API, complex setup
**Why Rejected:** Too complex for our current needs

## Implementation
- Access tokens: 15-minute expiration
- Refresh tokens: 7-day expiration
- RS256 signing algorithm
- Token rotation on refresh

## Consequences

### Positive
- Horizontal scaling without session management
- Better mobile app integration
- Reduced server-side state

### Negative
- Cannot revoke tokens before expiration (mitigated with short expiration)
- Larger payload than session ID
- Need refresh token mechanism

## Related Notes
- [[Files/src/auth/jwt.ts]]
- [[Patterns/Security/JWT Authentication]]
- [[Decisions/2025-01-20 Add Token Blacklist]]

## Validation
- ✅ Load testing shows linear scalability
- ✅ Mobile team reports smooth integration
- ⚠️ Need to add token blacklist for logout
```

### Commit Note

**Path:** `PRISM-Memory/Commits/<year-month>/<hash>-<slug>.md`

```markdown
---
type: git-commit
commit_hash: abc1234def5678
author: John Doe
date: 2025-01-15T10:30:00Z
branch: feature/authentication
files_changed: 5
insertions: 234
deletions: 45
tags:
  - authentication
  - feature
---

# Add JWT authentication system

## Commit
`abc1234def5678`

## Message
```
Add JWT authentication system

Implements stateless authentication using JWT tokens with refresh token support.

- Add JWT service with token generation and validation
- Implement auth middleware for protected routes
- Add refresh token endpoint
- Configure token expiration policies

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Files Changed
- `src/auth/jwt.ts` (new)
- `src/auth/middleware.ts` (new)
- `src/routes/auth.ts` (modified)
- `package.json` (modified)
- `README.md` (modified)

## Context
Implementation of [[Decisions/2025-01-15 Use JWT for Auth]].

## Key Changes

### New Features
- JWT token generation with configurable expiration
- Token validation middleware
- Refresh token mechanism

### Technical Details
- Using `jsonwebtoken` library
- RS256 signing algorithm
- 15-minute access tokens
- 7-day refresh tokens

## Related Notes
- [[Files/src/auth/jwt.ts]]
- [[Patterns/Security/JWT Authentication]]
- [[Decisions/2025-01-15 Use JWT for Auth]]

## Testing
- Unit tests for token generation
- Integration tests for auth flow
- Middleware tests for protected routes
```

### Interaction Note

**Path:** `PRISM-Memory/Interactions/<date>-<topic>.md`

```markdown
---
type: interaction
date: 2025-01-15T10:30:00Z
outcome: success
duration_minutes: 45
tags:
  - authentication
  - implementation
---

# Authentication Implementation Session

## Request
"Implement JWT authentication for the API"

## Approach
1. Analyzed existing auth code
2. Reviewed similar patterns in codebase
3. Implemented JWT service following repository pattern
4. Added comprehensive tests
5. Updated documentation

## Key Learnings
- Project uses repository pattern consistently
- Tests follow Given-When-Then structure
- Security features require security review tag

## Challenges Encountered
- Initial confusion about token expiration config
- Needed to add refresh token mechanism
- Required environment variable documentation

## Patterns Applied
- [[Patterns/Architecture/Repository Pattern]]
- [[Patterns/Security/JWT Authentication]]

## Files Created/Modified
- [[Files/src/auth/jwt.ts]]
- [[Files/src/auth/middleware.ts]]

## Follow-up Items
- [ ] Add token blacklist for logout
- [ ] Implement rate limiting on auth endpoints
- [ ] Add monitoring for failed auth attempts

## Related
- [[Decisions/2025-01-15 Use JWT for Auth]]
- [[Commits/2025-01/abc1234-add-authentication]]
```

### Preferences Note

**Path:** `PRISM-Memory/Preferences/coding-style.md`

```markdown
---
type: user-preferences
category: coding-style
updated_at: 2025-01-15T10:30:00Z
---

# Coding Style Preferences

## General
- **Language:** TypeScript preferred for new code
- **Formatting:** Prettier with 2-space indentation
- **Linting:** ESLint with strict rules enabled

## Naming Conventions
- **Files:** kebab-case (e.g., `user-repository.ts`)
- **Classes:** PascalCase (e.g., `UserRepository`)
- **Functions:** camelCase (e.g., `findUserById`)
- **Constants:** UPPER_SNAKE_CASE (e.g., `MAX_RETRIES`)

## Architecture
- Prefer repository pattern for data access
- Service layer for business logic
- Middleware for cross-cutting concerns
- Avoid god objects/classes

## Testing
- Given-When-Then structure
- Mock external dependencies
- Aim for 80%+ coverage
- Integration tests for critical paths

## Documentation
- JSDoc for public APIs
- README for each module
- Architecture Decision Records for major choices

## Learned Preferences
- Prefers explicit over implicit
- Values testability
- Likes comprehensive error messages
- Wants inline documentation
```

## Query Strategy

Since we're moving away from SQL, we need alternative query methods:

### 1. File System Search
```python
import os
from pathlib import Path
import frontmatter

def find_files_by_tag(vault_path: Path, tag: str) -> list[Path]:
    """Find all notes with specific tag"""
    results = []
    for md_file in vault_path.rglob("*.md"):
        post = frontmatter.load(md_file)
        if tag in post.get('tags', []):
            results.append(md_file)
    return results

def find_files_by_type(vault_path: Path, note_type: str) -> list[Path]:
    """Find all notes of specific type"""
    results = []
    for md_file in vault_path.rglob("*.md"):
        post = frontmatter.load(md_file)
        if post.get('type') == note_type:
            results.append(md_file)
    return results
```

### 2. Full-Text Search
```python
import re

def search_content(vault_path: Path, query: str) -> list[dict]:
    """Search note content"""
    results = []
    for md_file in vault_path.rglob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if re.search(query, content, re.IGNORECASE):
                post = frontmatter.loads(content)
                results.append({
                    'path': md_file,
                    'title': md_file.stem,
                    'metadata': post.metadata,
                    'content': post.content
                })
    return results
```

### 3. Link Graph Traversal
```python
def find_linked_notes(vault_path: Path, note_path: Path) -> list[Path]:
    """Find all notes linked from given note"""
    with open(note_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find [[wikilinks]]
    links = re.findall(r'\[\[(.*?)\]\]', content)

    result = []
    for link in links:
        # Convert wikilink to file path
        link_path = vault_path / f"{link}.md"
        if link_path.exists():
            result.append(link_path)

    return result
```

### 4. Obsidian Dataview Integration
If using Obsidian's Dataview plugin, can create dynamic queries:

```markdown
# File Index (MOC)

## Recent Analyses
```dataview
TABLE file_path, language, complexity, analyzed_at
FROM "PRISM-Memory/Files"
WHERE type = "file-analysis"
SORT analyzed_at DESC
LIMIT 20
```

## By Language
### TypeScript
```dataview
LIST
FROM "PRISM-Memory/Files"
WHERE language = "typescript"
```

### Python
```dataview
LIST
FROM "PRISM-Memory/Files"
WHERE language = "python"
```
```

## Obsidian Links

Use wikilinks to create knowledge graph:

```markdown
## Related Notes
- [[Patterns/Security/JWT Authentication]]
- [[Decisions/2025-01-15 Use JWT for Auth]]
- [[Files/src/auth/middleware.ts]]

## See Also
- [[Patterns/Architecture/Service Layer]] - Related pattern
- [[Decisions/2025-01-20 Add Token Blacklist]] - Follow-up decision
```

## Configuration

Update `.env`:
```bash
# Obsidian vault path (absolute or relative to .prism folder)
PRISM_OBSIDIAN_VAULT=/path/to/your/obsidian/vault

# Or use default at project root (same level as .prism)
PRISM_OBSIDIAN_VAULT=../docs/memory

# Optional: customize folder structure
PRISM_MEMORY_FILES_FOLDER=PRISM-Memory/Files
PRISM_MEMORY_PATTERNS_FOLDER=PRISM-Memory/Patterns
PRISM_MEMORY_DECISIONS_FOLDER=PRISM-Memory/Decisions
PRISM_MEMORY_COMMITS_FOLDER=PRISM-Memory/Commits
```

## Migration Strategy

### Phase 1: Export Existing Data
```python
# Read from SQLite, write to markdown
python skills/context-memory/utils/export_to_obsidian.py
```

### Phase 2: Update Storage Layer
- Replace `storage.py` SQLite operations with file operations
- Maintain same API interface for backward compatibility

### Phase 3: Update Hooks
- Modify hooks to write markdown instead of database entries

### Phase 4: Deprecate SQLite
- Keep database for backup/reference
- All new operations use Obsidian

## Benefits

1. **Human-Readable:** Browse and edit in Obsidian
2. **Linkable:** Create knowledge graph with wikilinks
3. **Searchable:** Use Obsidian's powerful search
4. **Sync-able:** Use Obsidian Sync or Git
5. **Visual:** Use graph view to explore connections
6. **Extensible:** Use Obsidian plugins (Dataview, Templater, etc.)
7. **Version Control:** Markdown files work great with Git
8. **No Database:** Simpler architecture, no SQLite dependency

## Trade-offs

1. **Performance:** File system slower than indexed database
2. **Queries:** More complex without SQL
3. **Transactions:** No atomic operations
4. **Concurrency:** Need file locking for writes
5. **Size:** Many small files vs single database

## Future Enhancements

1. **Obsidian URI Support:** Deep link to notes from CLI
2. **Template Integration:** Use Templater for consistent formatting
3. **Daily Notes:** Integrate with Obsidian daily notes
4. **Graph Analysis:** Export graph data for visualization
5. **MCP Integration:** Use Obsidian MCP server for direct access
