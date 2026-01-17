# File Write Chunking Rules

**ALL file write operations MUST follow chunking guidelines to prevent terminal crashes.**

## The Problem

Writing large files in single operations causes:
- **Terminal crashes** due to memory pressure
- **Communication timeouts** breaking client-server connection
- **Process hangs** making the terminal unresponsive

## The Rules

### Rule 1: ALWAYS Chunk Large Writes to ≤30 Lines
**NEVER write more than 30 lines in a single operation.**

```python
# ✅ CORRECT: Chunk into multiple writes
Write(path, first_30_lines, mode="rewrite")
Write(path, next_30_lines, mode="append")
Write(path, next_30_lines, mode="append")
# Continue with ≤30 line chunks

# ❌ WRONG: Single massive write
Write(path, 477_lines_of_content)  # This WILL crash the terminal
```

### Rule 2: Use Append Mode for Subsequent Chunks
**First chunk uses `mode="rewrite"`, all others use `mode="append"`.**

```python
# First chunk - rewrite to create/overwrite file
Write(file_path, lines_1_to_30, mode="rewrite")

# Subsequent chunks - append to existing file
Write(file_path, lines_31_to_60, mode="append")
Write(file_path, lines_61_to_90, mode="append")
```

### Rule 3: Plan Before Writing
**Before any file write, count the lines and plan chunks.**

```python
# Count lines in content
line_count = len(content.split('\n'))

# If > 30 lines, must chunk
if line_count > 30:
    # Split into chunks of 30 lines
    # Write first chunk with mode="rewrite"
    # Write remaining chunks with mode="append"
```

## Performance Limits

- **Configured limit**: `fileWriteLineLimit: 50` lines
- **Recommended maximum**: 30 lines per operation
- **Hard maximum**: Never exceed 50 lines

## Warning Signs

Desktop Commander will warn you:
> "💡 Performance tip: For optimal speed, consider chunking files into ≤30 line pieces"

**If you see this warning, you've already violated the rules. Don't ignore it.**

## Examples of Violations

These operations **caused terminal crashes**:
- 477 lines (Testing Strategy) ❌
- 282 lines (Implementation Guide) ❌
- 223 lines (Test Scripts) ❌
- 156 lines (Migration Tests) ❌

All of these should have been chunked to ≤30 lines each.

## When to Chunk

**ALWAYS chunk when:**
- Writing documentation files
- Writing code files with >30 lines
- Appending large blocks to existing files
- Creating any file that will exceed 30 lines

**NO EXCEPTIONS.**
