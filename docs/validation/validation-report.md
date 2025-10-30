# PRISM Documentation Validation Report

**Generated**: 2025-10-29 12:03:11

---

## Executive Summary

- **Files Checked**: 135/149
- **Coverage**: 90.6%
- **Total Issues**: 395

### Issues by Severity

- **Critical**: 262
- **Warning**: 16
- **Info**: 117

### Issues by Category

- **Cross Reference**: 268
- **Progressive Disclosure**: 125
- **Claude Code Features**: 2

---

## Cross Reference Issues

### Critical

**CR001**: `README.md`:116
- **Issue**: Broken link: 'docs/sub-agent-user-guide.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `checklists/documentation-quality-checklist.md`:68
- **Issue**: Broken link: 'path' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `checklists/documentation-quality-checklist.md`:69
- **Issue**: Broken link: 'path' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:11
- **Issue**: Broken link: './sub-agent-user-guide.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:18
- **Issue**: Broken link: './sub-agent-quick-reference.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:24
- **Issue**: Broken link: './sub-agent-implementation-playbook.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:125
- **Issue**: Broken link: './sub-agent-user-guide.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:144
- **Issue**: Broken link: './sub-agent-user-guide.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:145
- **Issue**: Broken link: './sub-agent-quick-reference.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:146
- **Issue**: Broken link: './sub-agent-user-guide.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:147
- **Issue**: Broken link: './sub-agent-quick-reference.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:148
- **Issue**: Broken link: './sub-agent-implementation-playbook.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `docs/index.md`:154
- **Issue**: Broken link: './archive/' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `workflows/README.md`:371
- **Issue**: Broken link: 'workflow-name.yaml' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:67
- **Issue**: Broken link: './reference/review-workflow.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:80
- **Issue**: Broken link: './reference/architecture-review.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:93
- **Issue**: Broken link: './reference/duplication-detection.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:142
- **Issue**: Broken link: './reference/file-permissions.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:174
- **Issue**: Broken link: './reference/review-workflow.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/peer/SKILL.md`:175
- **Issue**: Broken link: './reference/architecture-review.md' does not exist
- **Fix**: Verify the target file exists or update the link path

*... and 242 more Critical issues*

### Warning

**SB021**: `skills/agent-builder/reference/prism-agent-strategy.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/best-practices.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/commands.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/dependencies.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/examples.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/sm/reference/commands.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file


## Progressive Disclosure Issues

### Warning

**PD001**: `tasks/investigate-root-cause.md`:172
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/skill-builder/reference/skill-creation-process.md`:435
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/skill-builder/reference/skill-creation-process.md`:549
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/skill-builder/reference/skill-creation-process.md`:643
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/qa/reference/test-framework.md`:300
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/qa/reference/test-framework.md`:343
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/qa/reference/test-framework.md`:378
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/dev/reference/development-workflow.md`:159
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

**PD001**: `skills/dev/reference/development-workflow.md`:202
- **Issue**: Heading hierarchy skip: jumped from H1 to H4
- **Fix**: Use H2 instead, or restructure document hierarchy

### Info

**PD005**: `CHANGELOG.md`
- **Issue**: Long document (200 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `README.md`
- **Issue**: Long document (278 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/architect-checklist.md`
- **Issue**: Long document (440 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/change-checklist.md`
- **Issue**: Long document (219 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/code-quality-checklist.md`
- **Issue**: Long document (169 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/po-master-checklist.md`
- **Issue**: Long document (434 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `commands/dev.md`
- **Issue**: Long document (190 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD003**: `commands/qa.md`
- **Issue**: Long document (232 lines) with shallow hierarchy (max depth: 2)
- **Fix**: Consider breaking into subsections or using deeper heading levels

**PD005**: `commands/qa.md`
- **Issue**: Long document (232 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD003**: `commands/sm.md`
- **Issue**: Long document (304 lines) with shallow hierarchy (max depth: 2)
- **Fix**: Consider breaking into subsections or using deeper heading levels

**PD005**: `commands/sm.md`
- **Issue**: Long document (304 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `docs/index.md`
- **Issue**: Long document (165 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `hooks/README.md`
- **Issue**: Long document (200 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `scripts/README.md`
- **Issue**: Long document (430 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/calibrate-sizing.md`
- **Issue**: Long document (336 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/correct-course.md`
- **Issue**: Long document (192 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/create-dev-task.md`
- **Issue**: Long document (214 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/create-failing-test.md`
- **Issue**: Long document (212 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/create-qa-task.md`
- **Issue**: Long document (175 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `tasks/create-story-tasks.md`
- **Issue**: Long document (289 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

*... and 96 more Info issues*


## Claude Code Features Issues

### Warning

**CC005**: `skills\shared`
- **Issue**: Skill directory missing SKILL.md file
- **Fix**: Create SKILL.md to document skill usage and structure

### Info

**CC007**: `.claude/settings.json`
- **Issue**: No plugins or MCP servers configured in settings
- **Fix**: Consider adding plugins/MCP servers to extend capabilities


