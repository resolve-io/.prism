<!-- Powered by PRISM™ System -->

# Test Levels Framework

Comprehensive guide for determining appropriate test levels with emphasis on E2E integration testing as the primary confidence driver.

## The Inverted Testing Pyramid

**Priority Order: E2E Integration → Integration → Unit**

Modern applications benefit from an inverted testing pyramid where E2E integration tests provide the highest confidence and form the foundation of your test suite.

## Test Level Decision Matrix

### E2E Integration Tests (Primary Focus)

**When to use:**

- Critical API endpoints and user workflows
- Full application feature validation
- Cross-component integration verification
- Database transactions and state management
- Authentication and authorization flows
- Service-to-service communication

**Characteristics:**

- High confidence in real-world scenarios
- Tests complete feature workflows end-to-end
- Uses containerized test environments for isolation
- Validates actual system behavior under realistic conditions
- Moderate execution time with proper test organization

**Implementation Patterns:**

```yaml
e2e_integration_test:
  pattern: 'WebApplicationFactory'
  components: ['API', 'Database', 'External Services']
  scenario: 'User registration with email verification'
  justification: 'Critical user onboarding flow requiring full validation'
  test_environment: 'Containerized database with test fixtures'
  isolation: 'Container per test class'
```

**Test Organization:**
- Use test fixtures for shared setup (database containers, test data)
- Implement test collections for grouping related scenarios
- Apply Arrange-Act-Assert pattern consistently
- Use strong assertion libraries (e.g., Shouldly, FluentAssertions)

### Integration Tests (Supporting Role)

**When to use:**

- Service layer interactions
- Repository pattern validation
- Middleware and interceptor behavior
- Complex business workflows spanning multiple components
- Third-party service integration contracts

**Characteristics:**

- Tests component boundaries and integration points
- May use in-memory databases or test containers
- Focuses on service interactions rather than full workflows
- Moderate setup complexity

**Example scenarios:**

```yaml
integration_test:
  components: ['UserService', 'EmailService', 'AuditRepository']
  scenario: 'User profile update with audit trail'
  justification: 'Critical service interaction requiring validation'
  test_environment: 'In-memory database with mocked email service'
```

### Unit Tests (Minimal Coverage)

**When to use:**

- Pure business logic and algorithms
- Input validation and data transformation
- Complex calculations or state machines
- Error handling in isolated components
- Utility functions and helpers

**Characteristics:**

- Fast execution (immediate feedback)
- No external dependencies
- Easy to debug and maintain
- Limited real-world confidence

**Example scenarios:**

```yaml
unit_test:
  component: 'ValidationBehavior'
  scenario: 'Request validation with multiple rules'
  justification: 'Complex validation logic with multiple branches'
  mock_requirements: 'All external dependencies mocked'
```

## Test Level Selection Rules

### Favor E2E Integration Tests When:

- Testing API endpoints and user-facing features
- Validating critical business workflows
- Testing persistence layer operations
- Verifying cross-component interactions
- Testing authentication and authorization
- Validating system behavior under realistic conditions

### Favor Integration Tests When:

- Testing service layer interactions
- Validating repository patterns
- Testing middleware/interceptors in isolation
- Verifying third-party service contracts

### Favor Unit Tests When:

- Testing pure business logic
- Validating algorithms and calculations
- Testing utility functions
- Verifying error handling in isolation

## Container-Based Test Isolation

### Test Environment Setup

**Database Isolation:**
- Use containerized databases (e.g., Testcontainers) for each test class
- Provide separate connection strings for different database schemas
- Implement database fixtures with proper lifecycle management
- Seed test data through dedicated test data classes

**Application Factory Pattern:**
- Implement WebApplicationFactory for API testing
- Configure test-specific environment settings
- Override services for testing (e.g., datetime providers, external services)
- Provide test-specific configuration and connection strings

**Example Implementation:**
```yaml
test_environment:
  database_fixture:
    container: 'MsSqlContainer'
    lifecycle: 'Per test class'
    connection_strings:
      - 'MasterDb'
      - 'TenantDb'
  
  application_factory:
    pattern: 'WebApplicationFactory<Program>'
    environment: 'Testing'
    service_overrides:
      - 'IDateTimeProvider → FrozenTimeProvider'
      - 'External APIs → Test stubs'
```

### Fixture-Based Test Organization

**Test Fixtures:**
- Database fixtures for container lifecycle management
- SMTP fixtures for email testing
- Authentication fixtures for token management
- Shared test data classes with consistent test scenarios

**Test Collections:**
- Group related tests using test collection attributes
- Share fixtures across test classes efficiently
- Implement IClassFixture for shared setup
- Use collection definitions for complex scenarios

**Example Structure:**
```yaml
test_organization:
  fixtures:
    - 'DatabaseFixture: Container lifecycle'
    - 'SmtpFixture: Email service setup'
    - 'TestDataFixture: Consistent test data'
  
  collections:
    - 'DefaultWebApplicationCollection'
    - 'AuthenticationCollection'
    - 'DatabaseOnlyCollection'
```

## Anti-patterns to Avoid

- Over-reliance on unit tests for system validation
- E2E testing for isolated business logic
- Shared state between test classes without proper isolation
- Manual database cleanup instead of containerization
- Testing framework behavior instead of application logic
- Duplicate coverage across levels without clear justification

## Test Quality Guidelines

**Arrange-Act-Assert Pattern:**
- Clear separation of test phases
- Meaningful variable names and setup
- Single responsibility per test method
- Descriptive test names indicating scenario and expected outcome

**Test Data Management:**
- Use builder patterns for complex test data creation
- Implement test data classes for consistency
- Avoid hard-coded values in favor of meaningful constants
- Ensure test data independence and isolation

**Assertion Best Practices:**
- Use fluent assertion libraries (Shouldly, FluentAssertions)
- Provide meaningful failure messages
- Test both positive and negative scenarios
- Verify complete object state, not just return values

## Test Naming Conventions

- E2E Integration: `{Feature}_{Scenario}_Should{ExpectedOutcome}`
- Integration: `{Service}_{Operation}_Should{ExpectedResult}`
- Unit: `{Method}_{Condition}_Should{ExpectedBehavior}`

**Examples:**
- `RegisterComponent_WithValidTenant_ShouldReturnToken`
- `UserService_CreateUserWithRole_ShouldPersistAndAudit`
- `ValidationBehavior_WithInvalidRequest_ShouldThrowException`

## Test ID Format

`{EPIC}.{STORY}-{LEVEL}-{SEQ}`

Examples:

- `1.3-E2E-001` (E2E Integration Test)
- `1.3-INT-002` (Integration Test)
- `1.3-UNIT-001` (Unit Test)
