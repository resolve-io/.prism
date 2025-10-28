# Story: Avatar Upload and Image Management

## Status: Draft

## Story
As a registered user
I want to upload and manage my profile avatar with automatic optimization
So that I can personalize my profile with a professional-looking image

## Acceptance Criteria
- [ ] User can upload images up to 5MB in size
- [ ] System accepts only image file types (JPG, PNG, GIF, WEBP)
- [ ] Uploaded files are automatically scanned for malware
- [ ] Images are automatically compressed and optimized
- [ ] Images are served via CDN for fast loading
- [ ] System generates multiple thumbnail sizes (100x100, 300x300)
- [ ] Upload completes in less than 3 seconds for 5MB file
- [ ] User sees preview before confirming upload
- [ ] Clear error messages for invalid file types or sizes
- [ ] Old avatar is replaced when new one uploaded

## Tasks

### Backend Tasks
- [ ] Set up AWS S3 bucket with proper IAM permissions
- [ ] Implement POST /api/profiles/:id/avatar endpoint
- [ ] Add file type validation using magic bytes detection
- [ ] Add file size validation (max 5MB)
- [ ] Integrate virus scanning service (ClamAV or cloud service)
- [ ] Implement image compression using Sharp library
- [ ] Generate thumbnails: 100x100px, 300x300px, 600x600px
- [ ] Configure CloudFront CDN for image serving
- [ ] Update profile record with avatar URLs (original, thumbnails)
- [ ] Implement avatar deletion endpoint (DELETE /api/profiles/:id/avatar)
- [ ] Add cleanup job to delete old avatars when replaced
- [ ] Write unit tests for image processing pipeline
- [ ] Write integration tests for upload endpoint

### Frontend Tasks
- [ ] Create AvatarUpload component with drag-and-drop support
- [ ] Implement image preview before upload
- [ ] Add client-side file type and size validation
- [ ] Show upload progress bar during upload
- [ ] Display current avatar with "change" button
- [ ] Add image cropping tool for better framing
- [ ] Implement loading states during processing
- [ ] Show success/error notifications
- [ ] Ensure mobile-responsive design
- [ ] Write component tests for AvatarUpload
- [ ] Add E2E test for complete upload flow

### Infrastructure Tasks
- [ ] Provision S3 bucket with versioning enabled
- [ ] Configure S3 lifecycle policies for cleanup
- [ ] Set up CloudFront distribution
- [ ] Configure virus scanning service
- [ ] Set up monitoring for upload failures
- [ ] Configure alerts for high failure rates

## Architecture Alignment

### Technology Stack
- **Storage**: AWS S3 with versioning and lifecycle policies
- **CDN**: AWS CloudFront for global image delivery
- **Image Processing**: Sharp library for compression and thumbnails
- **Security**: ClamAV or AWS GuardDuty for virus scanning
- **Backend**: Node.js with Express and TypeScript
- **Frontend**: React with TypeScript, react-dropzone
- **Testing**: Jest, Supertest (backend), React Testing Library, Playwright (frontend)

### Architecture Patterns Applied
- **Service Layer Pattern**: ImageService handles all image processing logic
- **Strategy Pattern**: Different thumbnail generation strategies
- **Repository Pattern**: ImageRepository manages S3 interactions
- **Adapter Pattern**: StorageAdapter abstracts S3 implementation
- **Pipeline Pattern**: Upload -> Validate -> Scan -> Process -> Store

### System Boundaries
- ImageService coordinates the entire upload pipeline
- StorageAdapter is the only component accessing S3 directly
- Virus scanning service called via API (external boundary)
- CDN serves images (read-only boundary)
- Profile service updated with avatar URLs after successful upload

## Dev Notes

### Epic Context
This story implements the avatar upload feature from EPIC-999 (User Profile Management System). It provides the image infrastructure needed for personalized profiles and must handle security concerns around file uploads carefully.

### Technical Decisions
1. **Virus Scanning**: Use ClamAV daemon for real-time scanning before storage
2. **Image Processing**: Sharp library chosen for speed and quality
3. **Storage Strategy**: Store original + 3 sizes (100px, 300px, 600px thumbnails)
4. **CDN Integration**: CloudFront with 24-hour cache TTL for images
5. **File Validation**: Magic bytes detection prevents extension spoofing
6. **Upload Method**: Direct upload to API, then async processing to avoid timeout

### Security Considerations
- Validate file type by magic bytes, not extension alone
- Scan all uploads with virus scanning service
- Use signed S3 URLs with 1-hour expiration for uploads
- Sanitize filenames to prevent path traversal
- Implement rate limiting (max 5 uploads per hour per user)
- Store images in user-specific S3 prefixes
- Enable S3 bucket encryption at rest
- Disable S3 public access; serve only via CDN

### Performance Considerations
- Target: < 3 seconds for 5MB upload (per epic NFR)
- Async image processing to avoid blocking response
- Progressive image loading on frontend
- Lazy loading for thumbnail generation
- CDN caching reduces origin load
- Optimize Sharp settings for speed vs. quality
- Add CloudWatch metrics for upload performance

### Error Handling
- Return 400 Bad Request for invalid file type/size
- Return 413 Payload Too Large for files > 5MB
- Return 415 Unsupported Media Type for non-images
- Return 429 Too Many Requests when rate limit exceeded
- Return 500 Internal Server Error if virus scanning fails
- Return 503 Service Unavailable if S3 is down
- Graceful degradation if thumbnail generation fails

## Testing

### Unit Tests
- ImageService.validateFileType() with various file types
- ImageService.compressImage() verifies compression works
- ImageService.generateThumbnails() creates correct sizes
- File size validation with boundary values (4.9MB, 5MB, 5.1MB)
- Magic bytes detection for common image formats

### Integration Tests
- POST /api/profiles/:id/avatar - successful upload flow
- POST /api/profiles/:id/avatar - reject oversized file
- POST /api/profiles/:id/avatar - reject non-image file
- POST /api/profiles/:id/avatar - reject file with virus signature
- DELETE /api/profiles/:id/avatar - remove avatar
- Verify S3 upload with mocked S3 client
- Verify thumbnail URLs returned in response

### E2E Tests
- Complete upload flow: select file -> preview -> upload -> confirm
- Upload large file and verify 3-second performance
- Attempt invalid file type and see error message
- Upload image, then replace with new image
- Mobile upload flow with touch interactions
- Drag-and-drop upload on desktop

## Size Estimate
**3 days** (24 hours)
- Backend: 10 hours (validation, scanning, processing, storage, tests)
- Frontend: 6 hours (upload component, preview, progress, tests)
- Infrastructure: 4 hours (S3, CloudFront, ClamAV setup)
- Integration: 2 hours (end-to-end testing and debugging)
- Documentation: 2 hours (API docs, deployment guide)

## Dependencies
- AWS account with S3 and CloudFront access
- Virus scanning service configured (ClamAV or AWS GuardDuty)
- Sharp library and dependencies installed
- Profile CRUD API must exist (Story-001)
- Redis for rate limiting
- User authentication system (JWT tokens)

## Risks
1. **Virus Scanning Performance**: Scanning may slow upload significantly
   - Mitigation: Async scanning with immediate upload confirmation
2. **Storage Costs**: S3 costs grow with user base
   - Mitigation: S3 lifecycle policies, delete old avatars, optimize compression
3. **CDN Cache Invalidation**: Users may see old avatar after update
   - Mitigation: Use cache-busting query parameters on avatar URLs
4. **Large File Uploads**: May exceed 3-second target
   - Mitigation: Client-side compression before upload, optimize network path

## Dev Agent Record
### Completion Notes
[Dev fills this]

### File List
[Dev fills this]

### Change Log
[Dev fills this]

## QA Results
[QA fills this]
