# Strangler Pattern — Full Reference

Implement the strangler pattern to safely migrate controllers from express-web-api to actions.api with feature flag control.

## When to Use Strangler Pattern

Use strangler pattern for:
- **Active endpoints** with existing frontend usage
- **Complex business logic** that needs gradual migration
- **High-risk migrations** requiring rollback capability
- **Live systems** where downtime isn't acceptable

Skip strangler pattern for:
- Simple CRUD operations that can be rewritten quickly
- Unused or deprecated endpoints
- New features without legacy constraints

## Architecture Overview

### Express-Web-API (Legacy)
- .NET Framework Web API controllers
- Command/Manager/Service factory patterns
- JWT authentication with custom attributes
- ServiceResponse<T> wrapper pattern

### Actions.API (Target)
- .NET 6+ Minimal API endpoints
- MediatR Command/Request → Handler pattern
- Multiple authentication schemes
- Direct return types with ApiError exceptions

## Implementation Pattern

### Generic Controller Strangling (4 Lines)

```csharp
public async Task<HttpResponseMessage> YourControllerMethod([FromBody] YourRequestModel requestModel)
{
    var tenant = Features.ResolveTenant(Request.Headers);
    if (await FeatureResolverSingleton.GetIsFeatureEnabledAsync(Features.YourFeatureFlag, tenant))
        return CreateResponseMessage(await strangledService.Value.YourMethod(requestModel));

    return CreateResponseMessage(legacyService.Value.YourMethod(requestModel, EyeShareToken));
}
```

**Real example (WorkflowController):**
```csharp
public async Task<HttpResponseMessage> StartWorkflowExecution([FromBody] EyeShareWorkflowDesignerModel workflowDesigner)
{
    var tenant = Features.ResolveTenant(Request.Headers);
    if (await FeatureResolverSingleton.GetIsFeatureEnabledAsync(Features.WorkflowStrangle, tenant))
        return CreateResponseMessage(await strangledService.Value.StartWorkflowExecution(workflowDesigner));

    return CreateResponseMessage(legacyService.Value.StartWorkflowExecution(workflowDesigner, EyeShareToken));
}
```

### Controller Setup Pattern

```csharp
public class YourController : ApiBaseController
{
    private Lazy<YourLegacyService> legacyService;
    private Lazy<YourStrangledService> strangledService;

    public YourController()
    {
        legacyService = new Lazy<YourLegacyService>(() => {
            var token = TokenManager.GetTokenInfo();
            return new YourLegacyService(token, new DalService(token));
        });
        strangledService = new Lazy<YourStrangledService>(() => new YourStrangledService(ControllerContext));
    }
}
```

## Actions.API Implementation

### Clean Endpoint Pattern
```csharp
app.MapPost("/api/YourController/yourMethod",
    async (YourRequest request, IMediator mediator) =>
    {
        var result = await mediator.Send(request);
        return Results.Ok(result);
    }).RequireAuthorization();
```

### Request/Handler/Service Pattern
```csharp
public record YourRequest : IRequest<YourResponse>
{
    public YourDataModel Data { get; init; }
}

public class YourRequestHandler : IRequestHandler<YourRequest, YourResponse>
{
    public async Task<YourResponse> Handle(YourRequest request, CancellationToken cancellationToken)
    {
        return await _service.YourMethodAsync(request.Data);
    }
}
```

## TDD Implementation Process

### Phase 1: Capture Real Behavior
1. Test live endpoint with authentication
2. Capture JSON responses for all scenarios
3. Document authentication method (password grant, client credentials)
4. Record performance baseline

### Express-Web-API Authentication

```powershell
$authResponse = Invoke-RestMethod -Uri "http://localhost:52928/api/Auth/token" -Method Post -Body @{
    grant_type = "password"
    client_id = "RDTest"
    username = "SuperAdmin"
    password = "R3solv3!"
} -ContentType "application/x-www-form-urlencoded"

$token = $authResponse.token  # Note: 'token' field, not 'access_token'
$headers = @{
    'Authorization' = "Bearer $token"
    'Content-Type' = 'application/json'
}
```

Key details: endpoint `http://localhost:52928/api/Auth/token`, token field is `token` (not `access_token`).

### Phase 2: Create Tests (RED)
1. Create integration tests in actions.api test suite
2. Use captured responses as expected results
3. Ensure tests fail before implementation
4. Follow existing test patterns (ActionsApiFactory, DatabaseFixture)

### Phase 3: Implement (GREEN)
1. Build minimal implementation to pass tests
2. Preserve exact behavior from captured responses
3. Follow actions.api patterns (Request/Handler/Service)
4. Integrate with existing auth/db

### Phase 4: Strangler Integration
1. Modify express-web-api controller with feature flag
2. Set up lazy-loaded services
3. Enable gradual traffic switching
4. Test dual-path validation

## Key Integration Points

### Authentication
- **Express-web-api:** JWT via custom attributes
- **Actions.api:** Multiple schemes (JWT/MasterToken/TenantToken)
- **Bridge:** Service layer handles auth forwarding

### Database Context
- **Express-web-api:** Custom DbContext patterns
- **Actions.api:** TenantDbContext with IDbContextResolver
- **Migration:** Update entity mappings and queries

### Response Formats
- **Express-web-api:** ServiceResponse<T> wrapper
- **Actions.api:** Direct Results pattern
- **Bridge:** CreateResponseMessage() unifies response format

### Feature Flags
- **Location:** Express-web-api controllers only
- **Pattern:** FeatureResolverSingleton.GetIsFeatureEnabledAsync
- **Scope:** Per-tenant or per-user switching

## Success Criteria

- Feature flag routing works between legacy and new systems
- Response behavior identical to captured baseline
- All tests pass in actions.api integration suite
- No regressions in existing functionality
- Performance maintains or exceeds baseline
- Rollback capability tested and verified

## Reference Documents

- [Validation Checklist](./strangler-migration-checklist.md)
- [Migration Orchestration YAML](./strangler-pattern-migration.yaml)
