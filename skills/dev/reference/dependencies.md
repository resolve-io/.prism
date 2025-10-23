# Dev Dependencies Reference

The dev skill integrates with various PRISM artifacts.

## Dependencies Structure

```
.prism/
├── checklists/
│   ├── story-dod-checklist.md          # Story completion validation
│   └── strangler-migration-checklist.md # Migration safety checks
├── tasks/
│   ├── apply-qa-fixes.md               # QA feedback remediation
│   ├── create-next-story.md            # Story creation
│   ├── fetch-jira-issue.md             # Jira integration
│   └── strangler-pattern.md            # Legacy migration
├── workflows/
│   └── strangler-pattern-migration.yaml # Complete migration workflow
├── docs/
│   └── prism-kb.md                     # PRISM knowledge base
└── utils/
    └── jira-integration.md             # Jira utilities
```

## Dependency Details

### Checklists

#### story-dod-checklist.md
**Purpose**: Story Definition of Done validation
**Used by**: `*develop-story` completion step
**Content**:
- All acceptance criteria met
- Tests written and passing
- Code reviewed
- Documentation updated
- No regression failures

#### strangler-migration-checklist.md
**Purpose**: Migration safety validation
**Used by**: `*strangler` workflow
**Content**:
- Legacy behavior documented
- New implementation tested
- Parallel running verified
- Rollback plan ready
- Feature flags configured

### Tasks

#### apply-qa-fixes.md
**Purpose**: Apply fixes from QA review
**Used by**: `*review-qa` command
**Workflow**:
1. Read QA feedback from story
2. Prioritize issues
3. Implement fixes
4. Re-run tests
5. Update story QA Results section

#### create-next-story.md
**Purpose**: Create new story from requirements
**Used by**: Story planning workflow
**Workflow**:
1. Gather requirements
2. Define acceptance criteria
3. Break into tasks
4. Estimate with PSP/PROBE
5. Create story file

#### fetch-jira-issue.md
**Purpose**: Fetch Jira issue details
**Used by**: `*jira` command
**Workflow**:
1. Connect to Jira API
2. Fetch issue details
3. Parse and format
4. Display context
5. Cache for reuse

#### strangler-pattern.md
**Purpose**: Execute strangler pattern migration
**Used by**: `*strangler` command
**Workflow**:
1. Identify legacy boundaries
2. Create facade/adapter
3. Implement new service
4. Route traffic incrementally
5. Test both paths
6. Complete migration

### Workflows

#### strangler-pattern-migration.yaml
**Purpose**: Complete migration workflow definition
**Used by**: `*strangler` command
**Contains**:
- Phase definitions
- Migration steps
- Validation gates
- Rollback procedures
- Success criteria

### Docs

#### prism-kb.md
**Purpose**: PRISM methodology knowledge base
**Used by**: Development guidance
**Contains**:
- PRISM principles explained
- Implementation patterns
- Best practices
- Common pitfalls
- Code examples

### Utils

#### jira-integration.md
**Purpose**: Jira integration utilities
**Used by**: `*jira` command and workflows
**Contains**:
- API connection setup
- Authentication methods
- Issue parsing logic
- Field mapping
- Error handling

## Integration Points

### Story Files

Dev skill reads and updates story files (`.yaml`):

**Read:**
- Story description
- Acceptance criteria
- Tasks and subtasks
- Dev notes
- Testing requirements

**Update (authorized only):**
- Task checkboxes
- Dev Agent Record sections
- Debug Log
- Completion Notes
- File List
- Change Log
- Status (to 'Ready for Review')

### PSP Tracking

**Fields updated:**
- `psp.estimation.started` - Timestamp when work begins
- `psp.estimation.completed` - Timestamp when work ends
- `psp.estimation.actualHours` - Calculated duration
- `psp.estimation.accuracy` - Percentage vs estimate

### Jira Integration

**Automatic detection:**
- Issue keys in user messages (e.g., PLAT-123)
- Proactive offer to fetch context
- Integration with story workflows

**Fetched data:**
- Issue summary and description
- Status and assignee
- Comments and attachments
- Related issues
- Custom fields

## File Permissions

### Can Modify
- Story files: Dev Agent Record sections only
- Test files: Create and update
- Source code files: Create, update, delete (tracked in File List)
- Debug logs: Append entries

### Cannot Modify
- Story: description, acceptance criteria, requirements
- Architecture documents
- PRD documents
- Other agent sections (QA Results, Peer Review Results)
- Templates and checklists (unless creating new ones)

## Dependency Validation

Before starting work, dev skill validates:
- [ ] Story file exists and is readable
- [ ] Required tasks defined
- [ ] Checklists accessible
- [ ] Test framework available
- [ ] Jira credentials configured (if using Jira)

## Common Issues

**Missing Dependencies:**
- If task files missing, report to user
- If checklists missing, use inline validation
- If workflow files missing, use simplified process

**Configuration Issues:**
- Jira credentials not configured → continue without Jira
- Test framework not found → warn but continue
- Linter not configured → skip linting step

**Permission Issues:**
- Cannot write to story file → report error and halt
- Cannot read dependencies → report error and suggest fix
- Git permissions → warn but continue development
