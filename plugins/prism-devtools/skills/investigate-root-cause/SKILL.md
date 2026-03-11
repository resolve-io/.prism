---
name: investigate-root-cause
description: Systematically investigate bugs to find root cause via code analysis, git history, and error tracing.
version: 1.0.1
disable-model-invocation: true
---

# investigate-root-cause

Deep investigation to find the root cause of a validated customer issue using code analysis and debugging.

## Steps

1. Review validation evidence (errors, screenshots, console logs)
2. Search codebase for error signatures using Grep/search tools
3. Analyze code flow from user action through call chain to failure
4. Check recent git history for changes to affected files
5. Identify root cause with file/line location and impact assessment
6. Document findings: root cause report + recommended fix approach

[Full instructions](./instructions.md)