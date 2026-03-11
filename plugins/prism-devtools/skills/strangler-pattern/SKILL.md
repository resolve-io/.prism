---
name: strangler-pattern
version: 1.0.0
description: Use when implementing strangler pattern for legacy migrations. Safely migrates controllers with feature flag control.
disable-model-invocation: true
---

# Strangler Pattern

Safely migrate legacy controllers to actions.api with feature flag routing and zero downtime.

## Steps

1. Verify suitability: active endpoints with complex logic or rollback requirements only
2. Capture real behavior: test live endpoint, record responses and auth details
3. Create integration tests in actions.api suite (must fail first — TDD RED)
4. Implement Request/Handler/Service pattern until tests pass (TDD GREEN)
5. Add 4-line feature flag routing to express-web-api controller
6. Validate with [migration checklist](./reference/strangler-migration-checklist.md)

See [full guide](./instructions.md) and [migration YAML](./reference/strangler-pattern-migration.yaml).
