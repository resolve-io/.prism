---
name: apply-qa-fixes
description: Apply code/test fixes from QA gate results: prioritized plan from gate YAML and assessments.
version: 1.0.0
---

Implement fixes based on QA results (gate and assessments) for a story; apply code/test changes systematically.

1. Load QA gate YAML and assessment markdowns for the story
2. Build prioritized fix plan (high severity first, then NFRs, then coverage gaps)
3. Apply code fixes and add missing tests
4. Run `deno lint` and `deno test -A` until clean
5. Update allowed story sections (Dev Agent Record, File List, Change Log)
6. Set status to "Ready for Review" or "Ready for Done"

→ Full instructions: [instructions.md](./instructions.md)
