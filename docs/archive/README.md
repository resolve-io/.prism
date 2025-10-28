# Archive Documentation

This directory contains historical documentation from the sub-agent implementation project.

## Implementation History

Located in `implementation-history/`

These files document the step-by-step implementation of the sub-agent system (October 2025):

### Strategy Documents
- **sm-first-sub-agent-strategy.md** (34K) - Rationale for SM-first implementation approach
- **command-to-agent-strategy.md** (29K) - Original architectural vision for two-layer agent system

### Progress Reports
- **sub-agent-implementation-status.md** (18K) - Intermediate status report after Phase 1-2
- **phase-1-4-implementation-summary.md** (15K) - Summary of Phases 1-4 (SM + Dev agents)
- **phase-3-completion-report.md** (23K) - Detailed Phase 3 completion (SM command integration)
- **phase-4-completion-report.md** (21K) - Detailed Phase 4 completion (Dev sub-agents)
- **phase-5-completion-report.md** (31K) - Detailed Phase 5 completion (QA sub-agents)
- **phase-6-completion-report.md** (17K) - Detailed Phase 6 completion (Documentation & polish)

**Total**: 8 files, ~188K

**Current Documentation**: See `../sub-agent-implementation-playbook.md` for the complete, up-to-date implementation guide (65K, version 1.5.0).

## Test Artifacts

Located in `test-artifacts/`

These files were created during development to test sub-agent validators (October 2025):

### Test Epic
- **prd/epic-999-test-feature.md** - User Profile Management System (test epic)

### Test Stories
- **stories/epic-999/story-001-profile-creation.md**
- **stories/epic-999/story-002-avatar-upload-management.md**
- **stories/epic-999/story-003-privacy-settings-enforcement.md**
- **stories/epic-999/story-004-activity-history-tracking.md**
- **stories/test/story-001-test.md** (old test story)

**Total**: 6 files, ~15K

**Note**: These are not production artifacts. They were used solely for testing validators during implementation.

## Why Archive?

These files are archived (not deleted) because:

1. **Content is superseded** - The playbook contains all current implementation details
2. **Historical value** - Valuable for understanding decisions and rationale
3. **Reduce clutter** - Keep main docs directory focused on current documentation
4. **Rarely needed** - Only consulted when researching implementation history

## When to Consult Archive

Consult these files if you need to:

- **Understand WHY** certain architectural decisions were made
- **See detailed phase-by-phase** implementation history
- **Review original** architecture vision before it evolved
- **Understand test methodology** used during validator development
- **Research past issues** and how they were resolved

## Current Documentation Structure

For current documentation, always refer to the main `docs/` directory:

```
docs/
├── sub-agent-implementation-playbook.md    (Master implementation guide)
├── sub-agent-user-guide.md                 (How to use sub-agents)
├── sub-agent-quick-reference.md            (Cheat sheet)
├── prism-kb.md                             (Knowledge base)
├── prism-workflow.md                       (Workflow guide)
└── ... (other current docs)
```

## Maintenance

**These files are frozen** - they represent a historical snapshot and should not be modified.

If you need to reference this history:
- Link to files in this archive
- Do not duplicate content back to main docs
- The playbook is the single source of truth

---

**Archived**: 2025-10-27
**Archive Version**: 1.0.0
**Playbook Version at Archive**: 1.5.0 (100% complete)
