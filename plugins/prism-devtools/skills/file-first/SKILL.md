---
name: file-first
description: Read source files directly with Glob/Grep/Read. No RAG, no vector databases, no pre-loaded summaries.
version: 1.1.1
---

# file-first

Read source files directly. No RAG, no vector databases, no pre-loaded summaries.

## Steps

1. Detect project type: run `scripts/analyze_codebase.py` to identify structure
2. Locate relevant files with Glob/Grep
3. Read actual source files (not summaries)
4. Cite file:line when referencing code
5. Iterate: search again if needed

[Full instructions](./instructions.md)
