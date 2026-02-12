# Example Project Skills

Three real-world examples showing project skills with PRISM agent assignment.

## 1. Team Code Standards (Dev Agent, Green Phase)

A skill that enforces project-specific coding patterns during implementation.

**`.claude/skills/team-code-standards/SKILL.md`**:

```markdown
---
name: team-code-standards
description: Enforce team coding standards and patterns during implementation. Covers naming conventions, error handling patterns, and module structure.
version: 1.0.0
prism:
  agent: dev
  phase: green
  priority: 10
---

# Team Code Standards

## When to Use

- Implementing new features or fixing bugs
- Writing new modules, classes, or functions
- Refactoring existing code

## Standards

### Naming Conventions
- Services: `{Domain}Service` (e.g., `UserService`, `OrderService`)
- Repositories: `{Entity}Repository`
- DTOs: `{Entity}{Action}Dto` (e.g., `UserCreateDto`)

### Error Handling
- Always use `Result<T>` pattern instead of throwing exceptions
- Map external errors to domain-specific error types
- Log errors at the boundary, not in domain logic

### Module Structure
- One public class per file
- Group by feature, not by type
- See [detailed standards](./reference/full-standards.md) for complete rules

## Guardrails

- Do NOT skip error handling for "simple" cases
- Do NOT use generic exception types (`Exception`, `Error`)
- Do NOT create utility classes - use extension methods or domain services
```

**Why it works**: The Dev agent sees this during `green` phase (implementation), ensuring code follows team patterns as it's written.

## 2. Team Test Patterns (QA Agent, Red Phase)

A skill that enforces project-specific test conventions during test creation.

**`.claude/skills/team-test-patterns/SKILL.md`**:

```markdown
---
name: team-test-patterns
description: Enforce team test conventions when writing tests. Covers test naming, fixture patterns, assertion styles, and test data management.
version: 1.0.0
prism:
  agent: qa
  phase: red
  priority: 10
---

# Team Test Patterns

## When to Use

- Writing new tests (unit, integration, e2e)
- Creating test fixtures or factories
- Setting up test data

## Test Naming Convention

```
{MethodUnderTest}_{Scenario}_{ExpectedBehavior}
```

Examples:
- `CreateUser_WithValidEmail_ReturnsSuccess`
- `GetOrder_WhenNotFound_ThrowsNotFoundException`

## Test Structure

Use Arrange-Act-Assert with clear section comments:

```csharp
[Fact]
public void CreateUser_WithValidEmail_ReturnsSuccess()
{
    // Arrange
    var dto = UserFactory.CreateValid();

    // Act
    var result = _sut.CreateUser(dto);

    // Assert
    result.Should().BeSuccess();
}
```

## Test Data

- Use factory classes (`UserFactory`, `OrderFactory`) not raw constructors
- See [factory patterns](./reference/factory-patterns.md) for team conventions

## Guardrails

- NEVER use `Thread.Sleep` in tests - use async waits
- NEVER share mutable state between tests
- ALWAYS use factories for test data - no inline object creation
```

**Why it works**: The QA agent sees this during `red` phase (writing failing tests), ensuring tests follow team conventions from the start.

## 3. Team Architecture Guard (Architect Agent, Planning Phase)

A skill that ensures architecture decisions are followed during story planning.

**`.claude/skills/team-arch-guard/SKILL.md`**:

```markdown
---
name: team-arch-guard
description: Validate stories against architecture decisions and boundaries during planning. Ensures new work respects established patterns and service boundaries.
version: 1.0.0
prism:
  agent: architect
  phase: planning
  priority: 5
---

# Architecture Guard

## When to Use

- Planning new features or stories
- Reviewing proposed changes that cross service boundaries
- Any work touching the domain model or API contracts

## Architecture Decisions

### Service Boundaries
- **User Service**: Authentication, authorization, user profiles
- **Order Service**: Order lifecycle, payments, fulfillment
- **Notification Service**: Email, SMS, push notifications

Cross-service communication MUST use events, not direct calls.

### Technology Constraints
- New APIs: REST with OpenAPI spec (no GraphQL without ADR)
- New storage: PostgreSQL (no new database engines without ADR)
- New messaging: RabbitMQ via MassTransit

### Required Checks
Before approving a story plan:
1. Does it respect service boundaries?
2. Does it use approved technology choices?
3. Does it have an ADR if introducing new patterns?
4. See [ADR index](./reference/adr-index.md) for existing decisions

## Guardrails

- BLOCK plans that violate service boundaries
- BLOCK plans that introduce unapproved technology
- REQUIRE ADR reference for any new architectural pattern
```

**Why it works**: The Architect agent sees this during `planning` phase, catching boundary violations before any code is written.
