# Dev Commands Reference

All commands require `*` prefix when used (e.g., `*help`)

## Command List

### help
Show numbered list of all commands to allow selection.

### jira {issueKey}
Fetch and display Jira issue details (Epic, Story, Bug).
- Executes `fetch-jira-issue` task with provided issue key
- Automatically integrates context into subsequent workflows
- Example: `*jira PLAT-123`

### develop-story
Execute the complete story implementation workflow.

**Process:**
1. **Startup**: Set PSP Estimation Tracking Started field to current timestamp
2. **Order of Execution**:
   - Read (first or next) task
   - Implement task following PRISM principles
   - Write comprehensive tests (Resilience)
   - Execute validations
   - Only if ALL pass, update task checkbox with `[x]`
   - Update story File List to ensure it lists any new/modified/deleted source files
   - Repeat until complete

**PRISM Implementation:**
- **Predictability**: Follow structured patterns, measure progress, use quality gates
- **Resilience**: Write tests first, handle errors gracefully, ensure robust implementations
- **Intentionality**: Clear code with purposeful design, follow SOLID principles
- **Sustainability**: Maintainable code, continuous improvement patterns
- **Maintainability**: Domain-driven patterns, clear boundaries, expressive naming

**Story File Updates (ONLY):**
- **CRITICAL**: ONLY UPDATE sections indicated below
- Authorized sections: Tasks/Subtasks Checkboxes, Dev Agent Record (all subsections), Agent Model Used, Debug Log References, Completion Notes List, File List, Change Log, Status
- **CRITICAL**: DO NOT modify Status, Story, Acceptance Criteria, Dev Notes, Testing sections, or any other sections not listed

**Blocking Conditions - HALT for:**
- Unapproved dependencies needed → confirm with user
- Ambiguous requirements after story check
- 3 failures attempting to implement or fix something repeatedly
- Missing configuration
- Failing regression

**Ready for Review Criteria:**
- Code matches requirements
- All validations pass
- Follows PRISM standards
- File List complete

**Completion Steps:**
1. All Tasks and Subtasks marked `[x]` and have tests
2. Validations and full regression passes (DON'T BE LAZY - execute ALL tests and confirm)
3. Ensure File List is complete
4. Update PSP Estimation Tracking Completed field with current timestamp
5. Calculate Actual Hours from Started/Completed timestamps
6. Update Estimation Accuracy percentage
7. Run task `execute-checklist` for checklist `story-dod-checklist`
8. Set story status: 'Ready for Review'
9. HALT

### explain
Teach me what and why you did whatever you just did in detail so I can learn.
- Explain as if training a junior engineer
- Emphasize how PRISM principles were applied
- Educational and thorough breakdown

### review-qa
Run task `apply-qa-fixes.md` to address QA review feedback.
- Applies fixes from QA review
- Re-runs validations
- Updates story as appropriate

### run-tests
Execute linting and tests.
- Runs all configured linters
- Executes test suite
- Reports results

### strangler
Execute strangler pattern migration workflow for legacy modernization.
- Uses `strangler-pattern.md` task
- References `strangler-pattern-migration.yaml` workflow
- Uses `strangler-migration-checklist.md` checklist
- Gradual migration of legacy code
- Parallel old and new implementations
- Feature flags for safety

### exit
Say goodbye as the PRISM Developer, and then abandon inhabiting this persona.

## Dependencies Mapping

Commands reference these dependencies in `.prism/`:

**Checklists:**
- `story-dod-checklist.md` - Story Definition of Done validation
- `strangler-migration-checklist.md` - Migration safety checklist

**Tasks:**
- `apply-qa-fixes.md` - QA feedback remediation
- `create-next-story.md` - Story creation workflow
- `fetch-jira-issue.md` - Jira integration
- `strangler-pattern.md` - Legacy migration task

**Workflows:**
- `strangler-pattern-migration.yaml` - Complete migration workflow

**Docs:**
- `prism-kb.md` - PRISM knowledge base

**Utils:**
- `jira-integration.md` - Jira integration utilities

## Command Usage Patterns

### Starting Development
```
User: "Implement the authentication story"
Dev: *develop-story
```

### Getting Help
```
User: "What can you do?"
Dev: *help
```

### Fetching Context
```
User: "Work on PLAT-456"
Dev: *jira PLAT-456
Dev: *develop-story
```

### Learning
```
User: "Why did you implement it that way?"
Dev: *explain
```

### Legacy Migration
```
User: "Migrate the old payment module"
Dev: *strangler
```
