# Story: Privacy Settings and Enforcement

## Status: Draft

## Story
As a registered user
I want to control who can view my profile with privacy settings
So that I can protect my personal information and manage my visibility

## Acceptance Criteria
- [ ] User can set privacy level: Public, Friends Only, or Private
- [ ] Public profiles are visible to all authenticated users
- [ ] Friends Only profiles are visible only to user's friends
- [ ] Private profiles are visible only to the profile owner
- [ ] Privacy settings are enforced at the API level
- [ ] Unauthorized profile access returns 403 Forbidden
- [ ] Privacy settings can be changed at any time
- [ ] Default privacy level is "Friends Only" for new profiles
- [ ] User sees clear explanation of each privacy level
- [ ] Privacy violations are logged for security auditing

## Tasks

### Backend Tasks
- [ ] Add privacy_level column to profiles table (ENUM: PUBLIC, FRIENDS_ONLY, PRIVATE)
- [ ] Create PrivacyService with enforcement logic
- [ ] Implement privacy enforcement middleware for profile routes
- [ ] Add GET /api/profiles/:id/privacy endpoint
- [ ] Add PUT /api/profiles/:id/privacy endpoint
- [ ] Implement canViewProfile(viewerId, profileId) method
- [ ] Update GET /api/profiles/:id to enforce privacy rules
- [ ] Add privacy audit logging for unauthorized access attempts
- [ ] Set default privacy level to FRIENDS_ONLY in profile creation
- [ ] Write unit tests for privacy enforcement logic
- [ ] Write integration tests for all privacy scenarios

### Frontend Tasks
- [ ] Create PrivacySettings component with radio buttons
- [ ] Add privacy level descriptions for each option
- [ ] Implement privacy settings toggle on profile edit page
- [ ] Show privacy indicator on profile view (lock icon)
- [ ] Display appropriate message when profile not accessible
- [ ] Add confirmation modal when changing to Private
- [ ] Ensure mobile-responsive design
- [ ] Write component tests for PrivacySettings
- [ ] Add E2E test for privacy enforcement

### Database Tasks
- [ ] Add privacy_level column (VARCHAR or ENUM)
- [ ] Create index on privacy_level for query optimization
- [ ] Add CHECK constraint for valid privacy values
- [ ] Create Prisma enum for PrivacyLevel
- [ ] Run migration to add privacy_level column
- [ ] Backfill existing profiles with default FRIENDS_ONLY

### Security Tasks
- [ ] Create privacy_audit_logs table
- [ ] Log all unauthorized access attempts
- [ ] Implement rate limiting on privacy checks
- [ ] Add monitoring alerts for suspicious patterns
- [ ] Write security tests for bypass attempts

## Architecture Alignment

### Technology Stack
- **Backend**: Node.js with Express and TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Frontend**: React with TypeScript
- **Security**: Winston logger for audit trails
- **Testing**: Jest, Supertest (backend), React Testing Library, Playwright (frontend)

### Architecture Patterns Applied
- **Strategy Pattern**: Different privacy strategies (Public, FriendsOnly, Private)
- **Middleware Pattern**: Privacy enforcement middleware for routes
- **Repository Pattern**: PrivacyRepository for privacy-related queries
- **Service Layer Pattern**: PrivacyService encapsulates privacy logic
- **Audit Pattern**: Log all privacy-related events

### System Boundaries
- PrivacyService is the single source of truth for privacy rules
- All profile access routes must pass through privacy middleware
- Privacy enforcement happens at API layer, not database layer
- Frontend displays privacy UI but does not enforce (defense in depth)
- Audit logs stored separately from application data

## Dev Notes

### Epic Context
This story implements privacy controls from EPIC-999 (User Profile Management System). Privacy is a critical security feature that enables users to control their data visibility and supports future social features.

### Technical Decisions
1. **Privacy Levels**: Three levels sufficient for MVP (Public, Friends Only, Private)
2. **Default Level**: Friends Only balances privacy and discoverability
3. **Enforcement Layer**: Middleware enforces at API level for consistency
4. **Audit Logging**: Winston logger with separate audit log file
5. **Friends Support**: Friends Only level prepared for future friends system
6. **Database Design**: ENUM type for type safety and query optimization

### Security Considerations
- Privacy enforcement MUST happen at API level (never trust frontend)
- Log all unauthorized access attempts for security monitoring
- Rate limit privacy checks to prevent enumeration attacks
- Use database-level CHECK constraints to prevent invalid states
- Privacy changes trigger email notification to user
- Implement comprehensive tests to prevent privacy bypass bugs
- Consider GDPR implications of audit logs

### Performance Considerations
- Index privacy_level column for fast filtering
- Cache privacy settings in Redis (5-minute TTL)
- Optimize canViewProfile() for high-frequency calls
- Batch privacy checks for list queries
- Pre-compute privacy eligibility where possible
- Monitor query performance on privacy_level index

### Error Handling
- Return 403 Forbidden (not 404) for inaccessible profiles
- Return 400 Bad Request for invalid privacy level values
- Return 401 Unauthorized if user not authenticated
- Log all 403 responses to audit log
- Provide user-friendly error messages on frontend
- Rate limit excessive 403 attempts

## Testing

### Unit Tests
- PrivacyService.canViewProfile() for all privacy combinations
- Public profile accessible by anyone
- Friends Only profile accessible by friends
- Private profile accessible only by owner
- Privacy level validation (reject invalid values)
- Default privacy level set correctly on creation

### Integration Tests
- GET /api/profiles/:id with PUBLIC privacy (success)
- GET /api/profiles/:id with FRIENDS_ONLY privacy (friend access)
- GET /api/profiles/:id with FRIENDS_ONLY privacy (non-friend denied)
- GET /api/profiles/:id with PRIVATE privacy (owner access)
- GET /api/profiles/:id with PRIVATE privacy (other user denied)
- PUT /api/profiles/:id/privacy - change privacy level
- Verify 403 responses logged to audit log

### E2E Tests
- User sets profile to Public, another user views successfully
- User sets profile to Private, another user sees "not accessible" message
- User changes privacy from Public to Private
- User changes privacy from Private to Public
- Owner can always view own profile regardless of privacy
- Unauthorized user receives clear error message

### Security Tests
- Attempt to bypass privacy with direct API calls
- Attempt to enumerate profiles by trying many IDs
- Verify no information leakage in 403 responses
- Test rate limiting on privacy checks
- Verify audit logs capture all violations
- Test GDPR compliance for audit data retention

## Size Estimate
**2 days** (16 hours)
- Backend: 8 hours (privacy service, middleware, audit logging, tests)
- Frontend: 4 hours (privacy settings UI, error handling, tests)
- Database: 2 hours (schema changes, migration, backfill)
- Security: 2 hours (audit logging, monitoring, security tests)

## Dependencies
- Profile CRUD API must exist (Story-001)
- User authentication system (JWT tokens)
- Redis for caching privacy settings
- Winston logger configured
- Friends system interface defined (for Friends Only level)
- PostgreSQL database with Prisma

## Risks
1. **Privacy Bypass Bugs**: Critical security risk if enforcement fails
   - Mitigation: Comprehensive test suite, security audit, code review
2. **Friends System Dependency**: Friends Only level depends on future feature
   - Mitigation: Stub friends check to always return false until implemented
3. **Performance Impact**: Privacy checks on every request may slow API
   - Mitigation: Caching, indexing, optimize middleware
4. **Audit Log Growth**: Logs may grow large with many users
   - Mitigation: Log rotation, archival strategy, retention policies

## Dev Notes - Privacy Implementation

### Privacy Enforcement Middleware
```typescript
// Pseudocode for privacy enforcement
async function enforceProfilePrivacy(req, res, next) {
  const viewerId = req.user.id;
  const profileId = req.params.id;
  const canView = await privacyService.canViewProfile(viewerId, profileId);

  if (!canView) {
    await auditLogger.logUnauthorizedAccess(viewerId, profileId);
    return res.status(403).json({ error: 'Profile not accessible' });
  }

  next();
}
```

### Privacy Decision Logic
```typescript
// Pseudocode for privacy decision
async function canViewProfile(viewerId: string, profileId: string): Promise<boolean> {
  if (viewerId === profileId) return true; // Owner always can view

  const profile = await profileRepository.findById(profileId);

  switch (profile.privacyLevel) {
    case PrivacyLevel.PUBLIC:
      return true;

    case PrivacyLevel.FRIENDS_ONLY:
      return await friendsService.areFriends(viewerId, profileId);

    case PrivacyLevel.PRIVATE:
      return false;

    default:
      return false;
  }
}
```

## Dev Agent Record
### Completion Notes
[Dev fills this]

### File List
[Dev fills this]

### Change Log
[Dev fills this]

## QA Results
[QA fills this]
