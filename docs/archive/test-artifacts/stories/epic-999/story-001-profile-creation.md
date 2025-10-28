# Story: Profile Creation and Editing

## Status: Draft

## Story
As a registered user
I want to create and edit my personal profile with basic information and an avatar
So that I can personalize my account and share information with other users

## Acceptance Criteria
- [ ] User can create a new profile with name, email, and bio (max 500 chars)
- [ ] User can upload a profile picture (JPG, PNG, max 5MB)
- [ ] User can edit existing profile information
- [ ] System validates all input fields before saving
- [ ] Profile picture is automatically resized to 400x400px
- [ ] User sees confirmation message after successful save
- [ ] Validation errors are displayed clearly next to relevant fields
- [ ] Changes are persisted to database immediately
- [ ] Concurrent updates are handled with optimistic locking

## Tasks

### Backend Tasks
- [ ] Create ProfileRepository with CRUD methods following Repository Pattern
- [ ] Implement ProfileService with create/update business logic
- [ ] Create ProfileController with thin HTTP handling layer
- [ ] Add Zod validation schemas for profile data (name, email, bio)
- [ ] Implement image upload endpoint with file type validation
- [ ] Add image processing service (resize to 400x400px using Sharp library)
- [ ] Integrate AWS S3 storage for profile images
- [ ] Add optimistic locking to handle concurrent updates
- [ ] Implement rate limiting (max 10 updates per hour per user)
- [ ] Write unit tests for ProfileService business logic
- [ ] Write integration tests for API endpoints

### Frontend Tasks
- [ ] Create ProfileForm component using React Hook Form + Zod
- [ ] Implement ImageUpload component with preview functionality
- [ ] Add ProfileContainer for data fetching using custom hook
- [ ] Create useProfile custom hook for profile operations
- [ ] Implement form validation with inline error display
- [ ] Add loading states and success/error notifications
- [ ] Ensure mobile-responsive design using Tailwind CSS
- [ ] Write React Testing Library tests for components
- [ ] Add Playwright E2E test for complete profile creation flow

### Database Tasks
- [ ] Create profiles table with columns: id, user_id, name, email, bio, avatar_url, version, created_at, updated_at
- [ ] Add indexes on user_id and email fields
- [ ] Create Prisma schema for Profile model
- [ ] Run migration to create table

## Architecture Alignment

### Technology Stack
- **Backend**: Node.js 18+ with Express 4.x and TypeScript 5.x
- **Database**: PostgreSQL 14+ with Prisma 5.x ORM
- **Frontend**: React 18+ with TypeScript, React Hook Form, Zod validation
- **UI**: Tailwind CSS and Radix UI components
- **Storage**: AWS S3 for image storage
- **Validation**: Zod schemas (backend and frontend)
- **Testing**: Jest, Supertest (backend), React Testing Library, Playwright (frontend)

### Architecture Patterns Applied
- **Repository Pattern**: ProfileRepository handles all database access
- **Service Layer Pattern**: ProfileService contains business logic
- **Controller Pattern**: ProfileController handles HTTP concerns only
- **Container/Presenter Pattern**: ProfileContainer (data) + ProfileView (presentation)
- **Custom Hooks Pattern**: useProfile hook for reusable logic
- **API Contract Pattern**: Explicit REST API contracts defined

### System Boundaries
- Frontend communicates with backend via REST API only
- Backend validates all inputs; frontend validation is UX enhancement
- Only ProfileRepository accesses database directly
- ProfileService uses repository interface for loose coupling

## Dev Notes

### Epic Context
This story implements the first core feature from EPIC-999 (User Profile Management System). It focuses on basic profile creation and editing capabilities, which serves as the foundation for subsequent stories covering privacy settings, activity history, and profile viewing.

### Technical Decisions
1. **Image Processing**: Use Sharp library for server-side image resizing to ensure consistent dimensions and quality
2. **Optimistic Locking**: Use version field in database to detect concurrent updates and return 409 Conflict
3. **Storage**: AWS S3 with presigned URLs for secure image access, CDN integration for performance
4. **Validation**: Zod schemas shared between frontend and backend for consistency
5. **Rate Limiting**: Implement at middleware level using Redis-backed sliding window

### Security Considerations
- Validate file type by magic bytes, not just extension
- Sanitize bio field to prevent XSS attacks
- Require authentication for all profile endpoints
- Use signed URLs for S3 uploads with 1-hour expiration
- Implement CSRF protection on form submission

### Performance Considerations
- Image upload should complete in < 3 seconds for 5MB file (per epic NFR)
- Profile load time target: < 500ms (per epic NFR)
- Use lazy loading for profile images
- Cache profile data in Redis with 5-minute TTL
- Add database index on user_id for fast lookups

### Error Handling
- Return 400 Bad Request for validation errors with detailed field-level messages
- Return 409 Conflict for concurrent update conflicts
- Return 413 Payload Too Large for files > 5MB
- Return 415 Unsupported Media Type for invalid file types
- Return 429 Too Many Requests when rate limit exceeded

## Testing

### Unit Tests
- ProfileService.createProfile() with valid data
- ProfileService.updateProfile() with partial updates
- ProfileService.updateProfile() with concurrent version conflict
- Image validation logic (file type, size, dimensions)
- Zod schema validation for all profile fields

### Integration Tests
- POST /api/profiles - create new profile
- PUT /api/profiles/:id - update existing profile
- POST /api/profiles/:id/avatar - upload profile picture
- GET /api/profiles/:id - retrieve profile data
- Test authentication requirement on all endpoints
- Test rate limiting behavior

### E2E Tests
- Complete user journey: login -> create profile -> upload avatar -> edit bio -> save
- Validation error display for invalid inputs
- Concurrent edit scenario with two browser tabs
- Image upload with preview and successful save
- Mobile responsiveness of profile form

## Size Estimate
**2 days** (16 hours)
- Backend: 8 hours (repository, service, controller, image processing, tests)
- Frontend: 6 hours (form, image upload, validation, tests)
- Database: 1 hour (schema, migration)
- E2E Testing: 1 hour

## Dependencies
- User authentication system must be in place (JWT tokens)
- AWS S3 bucket configured with appropriate IAM permissions
- Redis instance available for rate limiting and caching
- Image processing library (Sharp) installed
- Prisma migrations configured

## Risks
1. **Image Upload Performance**: Large files may exceed 3-second target
   - Mitigation: Client-side compression before upload, optimize S3 configuration
2. **Concurrent Updates**: Version conflicts may confuse users
   - Mitigation: Clear error message with option to reload and retry
3. **Storage Costs**: S3 costs may grow with many users
   - Mitigation: Implement image cleanup for deleted profiles, use S3 lifecycle policies

## Dev Agent Record
### Completion Notes
[Dev fills this]

### File List
[Dev fills this]

### Change Log
[Dev fills this]

## QA Results
[QA fills this]
