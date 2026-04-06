---
name: strangler-pattern
version: 1.0.0
description: Safely migrate legacy controllers using strangler pattern with feature flags
---

# Strangler Pattern

Safely migrate legacy controllers to actions.api with feature flag routing and zero downtime.

## Steps

1. Verify suitability: active endpoints with complex logic or rollback requirements only
2. Capture real behavior: test live endpoint, record responses and auth details
3. Create integration tests in actions.api suite (must fail first — TDD RED)
4. Implement Request/Handler/Service pattern until tests pass (TDD GREEN)
5. Add 4-line feature flag routing to express-web-api controller
6. Validate with [migration checklist](./reference/strangler-migration-checklist.md) — see also [full guide](./reference/instructions.md) and [migration YAML](./reference/strangler-pattern-migration.yaml)
