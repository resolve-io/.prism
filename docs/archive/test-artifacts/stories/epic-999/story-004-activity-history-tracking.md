# Story: Activity History Tracking and Display

## Status: Draft

## Story
As a registered user
I want to view my recent profile-related activities
So that I can track changes and actions on my account

## Acceptance Criteria
- [ ] System automatically tracks all profile-related actions
- [ ] User can view their last 30 days of activity history
- [ ] Activity list is paginated (20 items per page)
- [ ] Each activity shows: action type, timestamp, details
- [ ] Activities older than 30 days are automatically archived
- [ ] Activity display performs well with large datasets
- [ ] User can filter activities by action type
- [ ] Activities include: profile created, profile updated, avatar changed, privacy changed
- [ ] Activity history loads in less than 500ms
- [ ] Mobile-responsive activity timeline

## Tasks

### Backend Tasks
- [ ] Create activity_logs table schema
- [ ] Design ActivityLog entity with Prisma
- [ ] Implement ActivityService with tracking methods
- [ ] Add activity tracking hooks to profile operations
- [ ] Create GET /api/profiles/:id/activities endpoint
- [ ] Implement 30-day filtering logic
- [ ] Add pagination support (limit, offset)
- [ ] Implement activity type filtering
- [ ] Create scheduled job to archive old activities
- [ ] Optimize database queries with indexes
- [ ] Write unit tests for ActivityService
- [ ] Write integration tests for activities endpoint

### Frontend Tasks
- [ ] Create ActivityTimeline component
- [ ] Create ActivityItem component for each entry
- [ ] Implement pagination controls
- [ ] Add activity type filter dropdown
- [ ] Design activity icons for each action type
- [ ] Format timestamps in user-friendly format (e.g., "2 hours ago")
- [ ] Add loading skeleton for activity list
- [ ] Handle empty state (no activities)
- [ ] Ensure mobile-responsive design
- [ ] Write component tests for ActivityTimeline
- [ ] Add E2E test for viewing activity history

### Database Tasks
- [ ] Create activity_logs table with proper indexes
- [ ] Add columns: id, user_id, action_type, details, created_at
- [ ] Create index on (user_id, created_at DESC)
- [ ] Create index on action_type for filtering
- [ ] Add foreign key constraint to profiles table
- [ ] Create Prisma schema for ActivityLog model
- [ ] Run migration to create activity_logs table

### Background Jobs
- [ ] Create archival job to move old activities
- [ ] Schedule job to run daily at 2 AM
- [ ] Create archived_activity_logs table
- [ ] Implement archival logic (move activities > 30 days)
- [ ] Add monitoring for archival job success/failure

## Architecture Alignment

### Technology Stack
- **Backend**: Node.js with Express and TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Frontend**: React with TypeScript
- **Background Jobs**: Node-cron or Bull queue
- **Date Handling**: date-fns library
- **Testing**: Jest, Supertest (backend), React Testing Library, Playwright (frontend)

### Architecture Patterns Applied
- **Observer Pattern**: Activity tracking hooks observe profile changes
- **Repository Pattern**: ActivityRepository handles database access
- **Service Layer Pattern**: ActivityService encapsulates business logic
- **Pagination Pattern**: Cursor-based pagination for scalability
- **Archive Pattern**: Move old data to separate table
- **Event Sourcing (Light)**: Activities provide audit trail

### System Boundaries
- ActivityService is the single source for activity tracking
- All profile operations emit activity events
- Activity hooks do not block main operations (async)
- Archived activities read-only via separate API
- Background jobs isolated from application code

## Dev Notes

### Epic Context
This story implements activity history tracking from EPIC-999 (User Profile Management System). Activity history provides users with transparency into their account actions and serves as an audit trail for security.

### Technical Decisions
1. **Data Retention**: 30 days in primary table, older data archived
2. **Pagination**: Cursor-based for better performance at scale
3. **Tracking Method**: Event hooks triggered after successful operations
4. **Archival Strategy**: Separate table keeps primary queries fast
5. **Activity Types**: Enum of predefined action types for consistency
6. **Performance**: Indexed queries and pagination for large datasets

### Security Considerations
- Users can only view their own activity history
- Activity logs are immutable (insert-only, no updates/deletes)
- Include IP address and user agent for security auditing
- Rate limit activity queries to prevent abuse
- Sensitive data (e.g., passwords) never logged
- GDPR compliance: allow users to export/delete activities

### Performance Considerations
- Target: < 500ms for activity history load (per epic NFR)
- Index on (user_id, created_at DESC) for fast queries
- Pagination prevents loading too much data at once
- Archival keeps primary table size manageable
- Use SELECT only needed columns, not SELECT *
- Consider read replica for activity queries
- Cache recent activities in Redis (5-minute TTL)

### Error Handling
- Return 404 Not Found if profile doesn't exist
- Return 403 Forbidden if accessing other user's activities
- Return 400 Bad Request for invalid pagination parameters
- Return 500 Internal Server Error if archival job fails
- Graceful degradation if activity tracking fails (don't block main operation)

## Testing

### Unit Tests
- ActivityService.trackActivity() creates activity log
- ActivityService.getActivities() returns paginated results
- ActivityService.getActivities() filters by action type
- ActivityService.archiveOldActivities() moves old records
- Date filtering logic (last 30 days)
- Pagination logic (offset, limit)

### Integration Tests
- GET /api/profiles/:id/activities - retrieve activities
- GET /api/profiles/:id/activities?page=2 - pagination
- GET /api/profiles/:id/activities?type=AVATAR_CHANGED - filtering
- Verify activities created after profile operations
- Test access control (user can't view others' activities)
- Test archival job moves old activities correctly

### E2E Tests
- User creates profile, views activity showing "Profile created"
- User updates profile, sees "Profile updated" activity
- User changes avatar, sees "Avatar changed" activity
- User navigates through paginated activity list
- User filters activities by type
- Mobile view of activity timeline

### Performance Tests
- Load test with 1000 activities for single user
- Verify < 500ms response time
- Verify pagination performance doesn't degrade
- Test archival job with large dataset
- Verify index usage with EXPLAIN query plans

## Size Estimate
**2.5 days** (20 hours)
- Backend: 8 hours (activity service, tracking hooks, archival job, tests)
- Frontend: 6 hours (timeline component, pagination, filtering, tests)
- Database: 3 hours (schema, indexes, migration, archival table)
- Background Jobs: 2 hours (archival job, scheduling, monitoring)
- Testing: 1 hour (E2E and performance tests)

## Dependencies
- Profile CRUD API must exist (Story-001)
- User authentication system (JWT tokens)
- PostgreSQL database with Prisma
- Background job scheduler (node-cron or Bull)
- Redis for caching (optional but recommended)
- date-fns library for date formatting

## Risks
1. **Activity Log Growth**: Database may grow large with many users
   - Mitigation: Archival strategy, retention policies, monitoring
2. **Performance Degradation**: Large activity tables slow queries
   - Mitigation: Proper indexing, pagination, archival, caching
3. **Tracking Failure**: Failed activity tracking may go unnoticed
   - Mitigation: Monitoring, alerts, non-blocking implementation
4. **Archival Job Failure**: Job may fail silently
   - Mitigation: Job monitoring, failure alerts, retry logic

## Dev Notes - Activity Tracking

### Activity Types Enum
```typescript
enum ActivityType {
  PROFILE_CREATED = 'PROFILE_CREATED',
  PROFILE_UPDATED = 'PROFILE_UPDATED',
  AVATAR_CHANGED = 'AVATAR_CHANGED',
  AVATAR_REMOVED = 'AVATAR_REMOVED',
  PRIVACY_CHANGED = 'PRIVACY_CHANGED',
}
```

### Activity Tracking Hook
```typescript
// Pseudocode for activity tracking
async function trackActivity(userId: string, actionType: ActivityType, details?: object) {
  try {
    await activityRepository.create({
      userId,
      actionType,
      details: JSON.stringify(details),
      ipAddress: req.ip,
      userAgent: req.headers['user-agent'],
      createdAt: new Date(),
    });
  } catch (error) {
    // Log error but don't block main operation
    logger.error('Failed to track activity', { error, userId, actionType });
  }
}
```

### Archival Job
```typescript
// Pseudocode for archival
async function archiveOldActivities() {
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const oldActivities = await activityRepository.findOlderThan(thirtyDaysAgo);

  await archivedActivityRepository.bulkInsert(oldActivities);
  await activityRepository.deleteOlderThan(thirtyDaysAgo);

  logger.info(`Archived ${oldActivities.length} activities`);
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
