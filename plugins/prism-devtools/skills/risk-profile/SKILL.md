---
name: risk-profile
description: Use to assess and document risk factors for stories or features. Creates risk profiles with mitigation strategies.
version: 1.0.0
---

Generates probability × impact risk matrix for a story with E2E-focused mitigation strategies and gate-ready outputs.

## Steps

1. Provide story ID and path
2. Identify risks across TECH, SEC, PERF, DATA, BUS, OPS categories
3. Rate each risk: probability × impact (score 1–9)
4. Build risk matrix and E2E mitigation strategies
5. Output gate YAML `risk_summary` block
6. Save markdown report to `qa.qaLocation/assessments/{story}-risk-{date}.md`

See [instructions.md](./instructions.md) for risk categories, scoring, and output formats.
