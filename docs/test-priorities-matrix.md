<!-- Powered by PRISM™ System -->

# Test Priorities Matrix

Guide for prioritizing test scenarios based on risk, criticality, and business impact.

## Priority Levels

### P0 - Critical (Must Test)

**Criteria:**

- Revenue-impacting functionality
- Security-critical paths (authentication, authorization, tenant access)
- Data integrity operations (database transactions, multi-tenant isolation)
- API endpoints serving core business workflows
- Container-based service integrations
- Regulatory compliance requirements
- Previously broken functionality (regression prevention)

**Examples:**

- Authentication/authorization flows
- Tenant creation, migration, and deletion
- Core API endpoints (user management, workflow operations)
- Database connectivity and multi-tenant data isolation
- Service-to-service integrations
- Payment processing
- GDPR/privacy compliance

**Testing Requirements:**

- **Primary: E2E integration tests with real databases and containers**
- Complete user journey validation from API to database
- Both happy and unhappy paths in realistic environments
- Authentication integration with external identity providers
- Multi-tenant isolation and data integrity
- Container orchestration and service connectivity
- Edge cases and error scenarios in full system context
- Performance under load with real infrastructure

### P1 - High (Should Test)

**Criteria:**

- Core user journeys spanning multiple services
- Frequently used API endpoints and workflows
- Features with complex business logic requiring database interactions
- Integration points between services and external systems
- Features affecting user experience across the full stack

**Examples:**

- User registration and management workflows
- Workflow execution and management APIs
- Data import/export with validation across services
- Notification and messaging systems
- Dashboard and reporting endpoints
- Configuration management across environments

**Testing Requirements:**

- **Primary: E2E integration testing for complete feature flows**
- API-to-database validation for primary happy paths
- Key error scenarios with realistic failure conditions
- Service integration points and cross-cutting concerns
- Authentication/authorization in context of full workflows
- Critical edge cases in multi-service scenarios
- Basic performance validation under realistic load

### P2 - Medium (Nice to Test)

**Criteria:**

- Secondary features with limited cross-service impact
- Administrative functionality and configuration endpoints
- Reporting and analytics features
- Non-critical integration points
- UI polish and user experience enhancements

**Examples:**

- Admin configuration APIs and management interfaces
- Report generation and data visualization endpoints
- System health monitoring and diagnostic APIs
- Theme and customization features
- Analytics and usage tracking
- Documentation and help system integrations

**Testing Requirements:**

- **E2E testing for primary happy paths**
- API endpoint validation with container-based testing when feasible
- Basic error handling in realistic environments
- Integration testing for service dependencies
- Can defer complex edge cases to unit/manual testing
- Focus on functional completeness over comprehensive scenarios

### P3 - Low (Test if Time Permits)

**Criteria:**

- Rarely used features with minimal business impact
- Nice-to-have functionality without service dependencies
- Cosmetic issues and UI polish
- Non-critical optimizations and experimental features
- Legacy feature support with limited integration scope

**Examples:**

- Advanced user preferences and customization options
- Experimental or beta feature endpoints
- Debug utilities and developer tools
- Legacy API compatibility layers
- Performance optimization features
- Non-essential integrations and third-party connectors

**Testing Requirements:**

- **Manual testing primarily, with selective E2E validation**
- Smoke tests for basic functionality when infrastructure permits
- Unit tests for isolated logic where applicable
- Document known limitations and accepted risks
- Can rely on production monitoring and user feedback
- Focus resources on higher priority integration testing

## Risk-Based Priority Adjustments

### Increase Priority When:

- High user impact (affects >50% of users)
- High financial impact (>$10K potential loss)
- Security vulnerability potential (especially authentication/authorization)
- Compliance/legal requirements
- Customer-reported issues in production
- Complex implementation requiring database transactions (>500 LOC)
- **Multiple service dependencies and integration points**
- **API endpoints critical to user workflows**
- **Multi-tenant data isolation concerns**
- **Container orchestration and infrastructure dependencies**

### Decrease Priority When:

- Feature flag protected with controlled rollout
- Gradual rollout planned with monitoring checkpoints
- Strong monitoring and alerting in place
- Easy rollback capability without data loss
- Low usage metrics and minimal user impact
- Simple implementation without external dependencies
- **Well-isolated component with minimal service integration**
- **Clear service boundaries and minimal cross-cutting concerns**
- **Unit-testable logic without database or infrastructure dependencies**

## Test Coverage by Priority

| Priority | E2E Integration | Unit Coverage | Integration Coverage | Manual Testing     |
| -------- | --------------- | ------------- | -------------------- | ------------------ |
| P0       | >95%            | >70%          | >90%                 | All critical paths |
| P1       | >80%            | >60%          | >75%                 | Main happy paths   |
| P2       | >60%            | >40%          | >50%                 | Smoke tests        |
| P3       | Best effort     | Best effort   | Best effort          | Manual only        |

## Priority Assignment Rules

1. **Start with business impact** - What happens if this fails across the entire system?
2. **Consider integration complexity** - How many services and databases are involved?
3. **Evaluate authentication/authorization impact** - Does this affect security boundaries?
4. **Factor in detectability** - Would we know if it failed in production?
5. **Account for recoverability** - Can we fix it quickly without data corruption?
6. **Assess container and infrastructure dependencies** - How complex is the runtime environment?

## Priority Decision Tree

```
Is it revenue-critical OR affects authentication/tenant isolation?
├─ YES → P0
└─ NO → Does it require multi-service integration?
    ├─ YES → Does it affect core user workflow?
    │   ├─ YES → P0 (if high-risk) / P1 (if standard risk)
    │   └─ NO → Is it frequently used?
    │       ├─ YES → P1
    │       └─ NO → P2
    └─ NO → Is it an isolated API endpoint or service?
        ├─ YES → Is it customer-facing?
        │   ├─ YES → P2
        │   └─ NO → P3
        └─ NO → P3
```

## Test Execution Order

1. **Execute P0 E2E integration tests first** (fail fast on critical system issues)
   - Authentication and tenant isolation flows
   - Core API endpoints with database validation
   - Multi-service integration scenarios
2. **Execute P1 E2E integration tests second** (core user functionality)
   - Complete user workflow validation
   - Service-to-service communication verification
3. **Execute P2 integration tests if time permits** (secondary features)
   - Administrative endpoints and configuration APIs
4. **P3 tests only in full regression cycles** (manual validation preferred)
   - Focus on E2E validation over isolated unit testing
   - Prioritize container-based test environments over mocked dependencies

## Continuous Adjustment

Review and adjust priorities based on:

- **Production incident patterns** (especially multi-service failures)
- **Integration test failure patterns** and service dependency issues
- User feedback and complaints related to end-to-end workflows
- **API usage analytics and service performance metrics**
- **Authentication and tenant isolation security incidents**
- **Container infrastructure and deployment issues**
- Business priority changes affecting core user journeys
- Database performance and multi-tenant scaling concerns

## E2E Integration Testing Focus Areas

**Container-Based Test Infrastructure:**
- SQL Server TestContainers for realistic database testing
- Authentication service integration (Keycloak, external identity providers)
- Multi-tenant database isolation validation
- Service discovery and inter-service communication

**Critical Integration Scenarios:**
- Complete tenant lifecycle (create, migrate, delete) with database validation
- Authentication flows from API to database with real tokens
- Workflow execution spanning multiple services and data stores
- Error handling and rollback scenarios across service boundaries
- Performance testing under realistic load with container infrastructure

**Preferred Testing Stack:**
- ASP.NET Core TestHost with WebApplicationFactory
- Real database connections via TestContainers
- Full dependency injection container validation
- HTTP client testing with actual API surface
- Minimal mocking in favor of real service integration
