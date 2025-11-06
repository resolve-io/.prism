# Context Memory API Reference

Pure API documentation for `storage_obsidian.py` functions.

## Import

```python
from skills.context_memory.utils.storage_obsidian import (
    store_file_analysis,
    store_pattern,
    store_decision,
    recall_query,
    recall_file,
    get_memory_stats
)
```

---

## store_file_analysis()

Store analysis of a source file.

**Signature:**
```python
def store_file_analysis(
    file_path: str,
    summary: str,
    purpose: str = None,
    complexity: str = 'moderate',
    key_functions: List[str] = None,
    dependencies: List[str] = None,
    notes: str = None
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | Yes | Relative path from project root |
| `summary` | str | Yes | Brief file description |
| `purpose` | str | No | Detailed explanation |
| `complexity` | str | No | `simple`, `moderate`, or `complex` |
| `key_functions` | List[str] | No | Important function names |
| `dependencies` | List[str] | No | External libraries used |
| `notes` | str | No | Additional context |

**Returns:** `str` - Path to created markdown file

**Example:**
```python
path = store_file_analysis(
    file_path='src/auth/jwt.ts',
    summary='JWT token validation and refresh',
    purpose='Handles authentication token lifecycle',
    complexity='moderate',
    key_functions=['validateToken', 'refreshToken'],
    dependencies=['jsonwebtoken', 'crypto']
)
```

**Output Location:** `{vault}/PRISM-Memory/Files/{file_path}.md`

---

## store_pattern()

Store reusable code pattern.

**Signature:**
```python
def store_pattern(
    name: str,
    description: str,
    category: str = 'general',
    example_path: str = None,
    code_example: str = None,
    when_to_use: str = None
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | Yes | Pattern name |
| `description` | str | Yes | What pattern does |
| `category` | str | No | Pattern type (e.g., `architecture`, `testing`) |
| `example_path` | str | No | File where pattern is used |
| `code_example` | str | No | Code snippet |
| `when_to_use` | str | No | Usage guidance |

**Returns:** `str` - Path to created markdown file

**Example:**
```python
path = store_pattern(
    name='Repository Pattern',
    description='Encapsulates data access in repository classes',
    category='architecture',
    example_path='src/repos/user-repository.ts'
)
```

**Output Location:** `{vault}/PRISM-Memory/Patterns/{category}/{name-slugified}.md`

---

## store_decision()

Record architectural decision.

**Signature:**
```python
def store_decision(
    title: str,
    decision: str,
    context: str,
    alternatives: str = None,
    consequences: str = None
) -> str
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | str | Yes | Decision title |
| `decision` | str | Yes | What was decided |
| `context` | str | Yes | Why it matters |
| `alternatives` | str | No | Options considered |
| `consequences` | str | No | Impact/tradeoffs |

**Returns:** `str` - Path to created markdown file

**Example:**
```python
path = store_decision(
    title='Use JWT for Authentication',
    decision='Implement stateless JWT tokens',
    context='Need horizontal scaling',
    alternatives='Considered Redis sessions',
    consequences='Tokens cannot be revoked until expiry'
)
```

**Output Location:** `{vault}/PRISM-Memory/Decisions/{YYYYMMDD}-{title-slugified}.md`

---

## recall_query()

Search all stored context.

**Signature:**
```python
def recall_query(
    query: str,
    limit: int = 10,
    types: List[str] = None
) -> List[Dict]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | str | Yes | Search terms |
| `limit` | int | No | Max results (default: 10) |
| `types` | List[str] | No | Filter by type: `['file', 'pattern', 'decision']` |

**Returns:** `List[Dict]` - Matching notes

**Result Structure:**
```python
[
    {
        'type': 'file',  # file|pattern|decision
        'path': 'src/auth/jwt.ts',
        'title': 'JWT Handler',
        'summary': 'JWT token validation...',
        'content': '...',  # Full markdown
        'file_path': 'docs/memory/.../jwt.md'
    }
]
```

**Example:**
```python
results = recall_query('authentication JWT', limit=5)
for r in results:
    print(f"{r['type']}: {r['path']}")
```

---

## recall_file()

Get analysis for specific file.

**Signature:**
```python
def recall_file(file_path: str) -> Optional[Dict]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | Yes | Relative path from project root |

**Returns:** `Optional[Dict]` - File analysis or `None`

**Result Structure:**
```python
{
    'path': 'src/auth/jwt.ts',
    'summary': '...',
    'purpose': '...',
    'complexity': 'moderate',
    'key_functions': [...],
    'dependencies': [...],
    'last_analyzed': '2025-01-05'
}
```

**Example:**
```python
analysis = recall_file('src/auth/jwt.ts')
if analysis:
    print(f"Complexity: {analysis['complexity']}")
```

---

## get_memory_stats()

Get vault statistics.

**Signature:**
```python
def get_memory_stats() -> Dict
```

**Parameters:** None

**Returns:** `Dict` - Statistics

**Result Structure:**
```python
{
    'files_analyzed': 42,
    'patterns_stored': 15,
    'decisions_recorded': 8,
    'total_notes': 65,
    'vault_path': '/path/to/vault'
}
```

**Example:**
```python
stats = get_memory_stats()
print(f"Total notes: {stats['total_notes']}")
```

---

## Configuration

Vault location configured via:

1. Environment variable: `PRISM_OBSIDIAN_VAULT`
2. core-config.yaml: `memory.vault`
3. Default: `../docs/memory`

**Path Resolution:**
- Relative paths: resolved from `.prism/` folder
- Absolute paths: used as-is

**Example:**
```bash
# Relative (from .prism/)
PRISM_OBSIDIAN_VAULT=../docs/memory
# → C:\Dev\docs\memory

# Absolute
PRISM_OBSIDIAN_VAULT=C:\vault
# → C:\vault
```

---

## Markdown Format

All notes use YAML frontmatter:

```markdown
---
type: file_analysis
path: src/auth/jwt.ts
analyzed_at: 2025-01-05
complexity: moderate
tags:
  - authentication
---

# File Name

Content...
```

---

## Error Handling

Functions return `None` or raise exceptions:

```python
try:
    result = recall_file('missing.ts')
    if result is None:
        print("Not found")
except Exception as e:
    print(f"Error: {e}")
```

---

**Version:** 1.7.0
