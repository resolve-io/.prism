---
name: qa-gate
description: Create/update QA gate YAML for a story: PASS/CONCERNS/FAIL/WAIVED decision with actionable issues.
version: 1.0.0
---

Create or update a quality gate decision file for a story based on review findings.

1. Review story findings (manual or via review-story)
2. Determine gate decision (PASS, CONCERNS, FAIL, or WAIVED)
3. Create YAML file at `qa.qaLocation/gates/{epic}.{story}-*.yml`
4. Include status_reason and any top_issues
5. Set reviewer and timestamp

→ Full instructions: [instructions.md](./instructions.md)
