---
name: nfr-assess
description: Use to assess non-functional requirements (security, performance, reliability, maintainability) through E2E integration testing patterns.
version: 1.0.0
---

Validates NFRs (security, performance, reliability, maintainability) via E2E integration testing and generates gate-ready outputs.

## Steps

1. Provide story ID (`{epic}.{story}`) and story path
2. Select NFRs to assess (default: security, performance, reliability, maintainability)
3. Check for thresholds in architecture docs and story AC
4. Run E2E integration assessment for each NFR
5. Generate gate YAML block for `nfr_validation`
6. Save markdown report to `qa.qaLocation/assessments/{story}-nfr-{date}.md`

See [instructions.md](./instructions.md) for assessment criteria and output formats.
