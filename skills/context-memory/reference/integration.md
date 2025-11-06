# Integration Code Examples

Pure code examples for using context-memory API in skills.

## Basic Import

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

## Store Operations

### Store File Analysis

```python
store_file_analysis(
    file_path='src/auth/jwt-handler.ts',
    summary='JWT token validation and refresh logic',
    purpose='Handles authentication token lifecycle',
    complexity='moderate',
    key_functions=['validateToken', 'refreshToken', 'revokeToken'],
    dependencies=['jsonwebtoken', 'crypto'],
    notes='Uses RSA256 signing with 15-minute expiry'
)
```

### Store Pattern

```python
store_pattern(
    name='Repository Pattern',
    description='Encapsulates data access logic in repository classes',
    category='architecture',
    example_path='src/repos/user-repository.ts',
    when_to_use='When abstracting database operations'
)
```

### Store Decision

```python
store_decision(
    title='Use JWT for Authentication',
    decision='Implement stateless JWT tokens instead of server sessions',
    context='Need to scale API horizontally across multiple servers',
    alternatives='Considered Redis sessions but adds infrastructure dependency',
    consequences='Tokens cannot be revoked until expiry'
)
```

## Retrieval Operations

### Query All Context

```python
results = recall_query('authentication JWT', limit=10)
for result in results:
    print(f"Type: {result['type']}")
    print(f"Path: {result.get('path', result.get('name'))}")
    print(f"Summary: {result.get('summary', result.get('description'))}")
    print("---")
```

### Get Specific File

```python
analysis = recall_file('src/auth/jwt-handler.ts')
if analysis:
    print(f"Summary: {analysis['summary']}")
    print(f"Complexity: {analysis['complexity']}")
    print(f"Functions: {', '.join(analysis.get('key_functions', []))}")
    print(f"Dependencies: {', '.join(analysis.get('dependencies', []))}")
```

### Get Stats

```python
stats = get_memory_stats()
print(f"Files analyzed: {stats['files_analyzed']}")
print(f"Patterns stored: {stats['patterns_stored']}")
print(f"Decisions recorded: {stats['decisions_recorded']}")
print(f"Total notes: {stats['total_notes']}")
```

## Conditional Usage (Optional Dependency)

```python
try:
    from skills.context_memory.utils.storage_obsidian import recall_query, store_pattern
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

def get_context(query_text):
    if not MEMORY_AVAILABLE:
        return None
    try:
        return recall_query(query_text)
    except:
        return None

# Use conditionally
context = get_context('authentication')
if context:
    # Use context
    pass
```

## Batch Operations

### Store Multiple Files

```python
files = [
    {
        'file_path': 'src/auth/jwt.ts',
        'summary': 'JWT token utilities',
        'complexity': 'moderate'
    },
    {
        'file_path': 'src/auth/middleware.ts',
        'summary': 'Authentication middleware',
        'complexity': 'simple'
    }
]

for file_data in files:
    store_file_analysis(**file_data)
```

### Store Multiple Patterns

```python
patterns = [
    {
        'name': 'Repository Pattern',
        'description': 'Data access abstraction',
        'category': 'architecture'
    },
    {
        'name': 'Factory Pattern',
        'description': 'Object creation abstraction',
        'category': 'design'
    }
]

for pattern_data in patterns:
    store_pattern(**pattern_data)
```

### Query Multiple Topics

```python
topics = ['authentication', 'database', 'error handling']

all_results = {}
for topic in topics:
    all_results[topic] = recall_query(topic, limit=5)

# Process results
for topic, results in all_results.items():
    print(f"\n{topic}:")
    for r in results:
        print(f"  - {r['path']}")
```

## Error Handling

```python
try:
    result = store_file_analysis(
        file_path='src/example.ts',
        summary='Example file'
    )
    print(f"Stored: {result}")
except Exception as e:
    print(f"Error storing: {e}")

try:
    analysis = recall_file('src/nonexistent.ts')
    if analysis is None:
        print("File not found in memory")
except Exception as e:
    print(f"Error recalling: {e}")
```

## Type Hints

```python
from typing import List, Dict, Optional

def analyze_and_store(file_path: str, content: str) -> Optional[str]:
    """
    Analyze file and store in memory.

    Returns:
        Path to created note or None on error
    """
    try:
        return store_file_analysis(
            file_path=file_path,
            summary=f"Analysis of {file_path}",
            complexity='moderate'
        )
    except Exception:
        return None

def search_context(query: str) -> List[Dict]:
    """
    Search memory for context.

    Returns:
        List of matching notes
    """
    try:
        return recall_query(query, limit=10)
    except Exception:
        return []
```

## Path Handling

```python
from pathlib import Path

# Normalize paths
project_root = Path.cwd()
file_path = Path('src/auth/jwt.ts')
relative_path = file_path.relative_to(project_root)

# Store with relative path
store_file_analysis(
    file_path=str(relative_path),
    summary='JWT utilities'
)

# Recall with relative path
analysis = recall_file(str(relative_path))
```

---

**Version:** 1.7.0
