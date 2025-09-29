<!-- Powered by PRISM™ System -->

# Technical Preferences and Testing Patterns

## Testing Framework Preferences

### Primary Testing Approach: E2E Integration Testing
- **Preferred Strategy**: End-to-End integration testing over isolated unit testing
- **Rationale**: E2E integration tests provide higher confidence by testing real application behavior with actual dependencies
- **Test Framework**: xUnit (preferred) with support for NUnit and MSTest as alternatives

### Integration Testing Stack
- **Test Framework**: xUnit with collection-based test grouping
- **API Testing**: WebApplicationFactory pattern for ASP.NET Core applications
- **Assertion Library**: Shouldly (preferred) with FluentAssertions as alternative
- **Container Orchestration**: Testcontainers for database and service isolation
- **Mocking**: NSubstitute (minimal use, prefer real implementations where possible)
- **JSON Serialization**: System.Text.Json with Newtonsoft.Json fallback support

### Test Organization Patterns
- **Fixture-based Architecture**: Use IClassFixture and ICollectionFixture for shared test resources
- **Collection Grouping**: Group related tests using [CollectionDefinition] attributes
- **Test Data Management**: Centralized test data classes with seeding capabilities
- **Database Testing**: Testcontainers with dedicated connection strings for master/tenant scenarios

### Authentication Testing
- **Bearer Token Patterns**: JWT token-based authentication with real token generation
- **Test Authentication**: Use actual authentication flows rather than mocked auth
- **Authorization Headers**: Standard Bearer token implementation in test clients

### Database Testing Approach
- **Container Isolation**: Each test collection uses isolated database containers
- **Connection Management**: Separate connection strings for different database schemas (master/tenant)
- **Data Seeding**: Automated test data seeding through database fixtures
- **State Management**: Database transactions or container reset for test isolation

### API Testing Standards
- **HttpClient Factory**: WebApplicationFactory for creating test clients
- **Request/Response Testing**: Full HTTP request/response cycle testing
- **Content Serialization**: JSON content with proper content-type headers
- **Status Code Validation**: Explicit HTTP status code assertions
- **Error Response Testing**: Structured error response validation

### Unit Testing (When Necessary)
- **Limited Scope**: Use unit tests only for complex business logic or algorithms
- **Mocking Framework**: NSubstitute for dependency mocking
- **Test Structure**: Arrange-Act-Assert pattern with clear test organization
- **Validation Testing**: Behavior testing for validation rules and edge cases

### Test Environment Configuration
- **Environment Variables**: Test-specific configuration override capability
- **Service Override**: ConfigureTestServices for dependency replacement
- **Logging Integration**: xUnit test output integration for debugging
- **Async Lifecycle**: IAsyncLifetime for proper async setup/teardown

### Dependencies and Libraries
```xml
<!-- Integration Testing -->
<PackageReference Include="xunit" />
<PackageReference Include="Microsoft.AspNetCore.Mvc.Testing" />
<PackageReference Include="Shouldly" />
<PackageReference Include="Testcontainers" />
<PackageReference Include="Testcontainers.MsSql" />
<PackageReference Include="System.Text.Json" />

<!-- Unit Testing (minimal) -->
<PackageReference Include="NSubstitute" />
<PackageReference Include="MockQueryable.NSubstitute" />
```

### Testing Philosophy
1. **Integration First**: Prefer integration tests that exercise real application paths
2. **Container Isolation**: Use containers to provide consistent, isolated test environments  
3. **Real Dependencies**: Test against actual databases, APIs, and services when possible
4. **Fixture Reuse**: Share expensive setup through fixtures while maintaining test isolation
5. **Clear Organization**: Use collections and fixtures to group related tests logically
6. **Comprehensive Coverage**: Focus on testing complete user scenarios rather than code coverage metrics
