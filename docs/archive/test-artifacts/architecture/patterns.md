# Architecture Patterns - PRISM Standards

## Backend Patterns

### Repository Pattern
Use for all data access operations. Separates business logic from data access.

**Example**:
```typescript
// repositories/UserRepository.ts
export class UserRepository {
  async findById(id: string): Promise<User | null> {
    return prisma.user.findUnique({ where: { id } });
  }

  async create(data: CreateUserDto): Promise<User> {
    return prisma.user.create({ data });
  }
}
```

### Service Layer Pattern
Business logic lives in service classes. Controllers should be thin.

**Example**:
```typescript
// services/ProfileService.ts
export class ProfileService {
  constructor(private profileRepo: ProfileRepository) {}

  async updateProfile(userId: string, data: UpdateProfileDto) {
    // Business logic here
    return this.profileRepo.update(userId, data);
  }
}
```

### Controller Pattern
Controllers handle HTTP concerns only. Delegate to services.

**Example**:
```typescript
// controllers/ProfileController.ts
export class ProfileController {
  constructor(private profileService: ProfileService) {}

  async update(req: Request, res: Response) {
    const result = await this.profileService.updateProfile(
      req.user.id,
      req.body
    );
    return res.json(result);
  }
}
```

## Frontend Patterns

### Container/Presenter Pattern
Separate data-fetching containers from presentation components.

**Example**:
```typescript
// containers/ProfileContainer.tsx
export function ProfileContainer() {
  const { data, isLoading } = useProfile();
  return <ProfileView profile={data} loading={isLoading} />;
}

// components/ProfileView.tsx
export function ProfileView({ profile, loading }: Props) {
  // Pure presentation logic
}
```

### Custom Hooks Pattern
Extract reusable logic into custom hooks.

**Example**:
```typescript
// hooks/useProfile.ts
export function useProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  // Hook logic here
  return { profile, updateProfile };
}
```

## System Boundaries

### Frontend/Backend Separation
- Frontend communicates with backend ONLY via REST API
- No direct database access from frontend
- Backend validates ALL inputs, frontend validation is UX only

### Service Boundaries
- Profile Service should not directly access User Service data
- Use API contracts between services
- Maintain loose coupling via interfaces

### Database Access
- ONLY repositories access the database
- Services never import Prisma directly
- Use repository interfaces for testing

## Integration Patterns

### API Contract Pattern
Define explicit contracts for all API endpoints.

**Example**:
```typescript
// contracts/ProfileAPI.ts
export interface ProfileAPI {
  GET: {
    '/api/profiles/:id': {
      response: Profile;
      errors: { 404: 'Profile not found' };
    };
  };
  PUT: {
    '/api/profiles/:id': {
      body: UpdateProfileDto;
      response: Profile;
      errors: { 400: 'Validation error'; 403: 'Forbidden' };
    };
  };
}
```

### Error Handling Pattern
Consistent error handling across the application.

**Example**:
```typescript
// middleware/errorHandler.ts
export function errorHandler(err: Error, req: Request, res: Response) {
  if (err instanceof ValidationError) {
    return res.status(400).json({ error: err.message });
  }
  // Handle other error types
}
```

## Non-Functional Patterns

### Performance
- Implement caching at service boundaries
- Use pagination for list endpoints (max 100 items)
- Lazy load images and large data
- Database indexes on frequently queried fields

### Security
- All endpoints require authentication (except public endpoints)
- Validate all user inputs with Zod schemas
- Sanitize output to prevent XSS
- Rate limiting on write operations
- HTTPS only in production

### Testing
- Unit tests for services and utilities
- Integration tests for API endpoints
- E2E tests for critical user flows
- Minimum 80% code coverage

## Anti-Patterns to Avoid

❌ **God Objects**: Services that do everything
❌ **Tight Coupling**: Direct dependencies between unrelated modules
❌ **Anemic Domain Models**: Models with no behavior
❌ **Magic Numbers**: Use named constants
❌ **Callback Hell**: Use async/await
❌ **Premature Optimization**: Profile first, optimize later
