# PRISM Documentation Validation Report

**Generated**: 2026-04-05 21:12:27

---

## Executive Summary

- **Files Checked**: 251/276
- **Coverage**: 90.9%
- **Total Issues**: 233

### Issues by Severity

- **Critical**: 0
- **Warning**: 116
- **Info**: 117

### Issues by Category

- **Cross Reference**: 35
- **Progressive Disclosure**: 177
- **Claude Code Features**: 1
- **Terminology**: 20

---

## Cross Reference Issues

### Warning

**SB021**: `skills/file-first/reference/README.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/file-first/reference/TESTING.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/story-001-prism-system-validation.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/story-002-hierarchical-progressive-disclosure-validation.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

**SB021**: `skills/shared/reference/validation-report.md`
- **Issue**: Orphaned reference file (not reachable from SKILL.md)
- **Fix**: Add a link to this file from SKILL.md or another reachable file

### Info

**SB013**: `skills/agent-builder/reference/configuration-guide.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/configuration-guide.md → skills/agent-builder/reference/agent-examples.md → skills/agent-builder/reference/configuration-guide.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/agent-builder/reference/configuration-guide.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/configuration-guide.md → skills/agent-builder/reference/agent-examples.md → skills/agent-builder/reference/best-practices.md → skills/agent-builder/reference/configuration-guide.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/agent-builder/reference/agent-examples.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/agent-examples.md → skills/agent-builder/reference/best-practices.md → skills/agent-builder/reference/agent-examples.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/agent-builder/reference/configuration-guide.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/configuration-guide.md → skills/agent-builder/reference/agent-examples.md → skills/agent-builder/reference/best-practices.md → skills/agent-builder/reference/troubleshooting.md → skills/agent-builder/reference/configuration-guide.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/agent-builder/reference/best-practices.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/best-practices.md → skills/agent-builder/reference/troubleshooting.md → skills/agent-builder/reference/best-practices.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/agent-builder/reference/agent-examples.md`
- **Issue**: Circular reference detected: skills/agent-builder/reference/agent-examples.md → skills/agent-builder/reference/best-practices.md → skills/agent-builder/reference/troubleshooting.md → skills/agent-builder/reference/agent-examples.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/jira/SKILL.md`
- **Issue**: Circular reference detected: skills/jira/SKILL.md → skills/jira/reference/instructions.md → skills/jira/reference/README.md → skills/jira/reference/extraction-format.md → skills/jira/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/quick-reference.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/quick-reference.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/quick-reference.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/quick-reference.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/quick-reference.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/quick-reference.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/instructions.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/progressive-disclosure.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/progressive-disclosure.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/instructions.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/dynamic-manifests.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/dynamic-manifests.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/instructions.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/progressive-disclosure.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/progressive-disclosure.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/dynamic-manifests.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/dynamic-manifests.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/progressive-disclosure.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/progressive-disclosure.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/dynamic-manifests.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/dynamic-manifests.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/instructions.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

*... and 10 more Info issues*


## Progressive Disclosure Issues

### Warning

**PD002**: `agents/templates/sfr-qa-gate.md`:1
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `agents/templates/sfr-requirements-trace.md`:1
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `agents/templates/sfr-story-content.md`:1
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/draft_story.md`:3
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/implement_tasks.md`:3
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/review_previous_notes.md`:8
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/verify_green_state.md`:3
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/verify_plan.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `hooks/core-steps/write_failing_tests.md`:3
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/byos/SKILL.md`:10
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/document-project/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/initialize-architecture/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/nfr-assess/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/prism-done/SKILL.md`:10
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/risk-profile/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/sdlc-handoff/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/story-sizing/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/version-bump/SKILL.md`:14
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**SB016**: `skills/agent-builder/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/agent-builder/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

*... and 74 more Warning issues*

### Info

**PD005**: `CHANGELOG.md`
- **Issue**: Long document (1127 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `CLAUDE.md`
- **Issue**: Long document (642 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `README.md`
- **Issue**: Long document (274 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/architecture-compliance-checker.md`
- **Issue**: Long document (174 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/epic-analyzer.md`
- **Issue**: Long document (277 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/link-checker.md`
- **Issue**: Long document (200 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/lint-checker.md`
- **Issue**: Long document (171 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/qa-gate-manager.md`
- **Issue**: Long document (470 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/requirements-tracer.md`
- **Issue**: Long document (531 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/test-runner.md`
- **Issue**: Long document (218 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD003**: `commands/dev.md`
- **Issue**: Long document (221 lines) with shallow hierarchy (max depth: 2)
- **Fix**: Consider breaking into subsections or using deeper heading levels

**PD005**: `commands/dev.md`
- **Issue**: Long document (221 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD003**: `commands/qa.md`
- **Issue**: Long document (245 lines) with shallow hierarchy (max depth: 2)
- **Fix**: Consider breaking into subsections or using deeper heading levels

**PD005**: `commands/qa.md`
- **Issue**: Long document (245 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD003**: `commands/sm.md`
- **Issue**: Long document (317 lines) with shallow hierarchy (max depth: 2)
- **Fix**: Consider breaking into subsections or using deeper heading levels

**PD005**: `commands/sm.md`
- **Issue**: Long document (317 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `commands/support.md`
- **Issue**: Long document (153 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `hooks/README.md`
- **Issue**: Long document (232 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `scripts/README.md`
- **Issue**: Long document (430 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `utils/jira-integration.md`
- **Issue**: Long document (293 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

*... and 63 more Info issues*


## Claude Code Features Issues

### Info

**CC006**: `.claude/settings.json`
- **Issue**: No .claude/settings.json found
- **Fix**: Create settings.json to configure Claude Code behavior


## Terminology Issues

### Warning

**TC001**: `commands/po.md`:81
- **Issue**: Skill 'create-epic' referred to as 'task'
- **Fix**: Replace with '/create-epic' or 'create-epic skill'

**TC001**: `commands/po.md`:83
- **Issue**: Skill 'correct-course' referred to as 'task'
- **Fix**: Replace with '/correct-course' or 'correct-course skill'

**TC001**: `commands/qa.md`:90
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC001**: `commands/qa.md`:115
- **Issue**: Skill 'nfr-assess' referred to as 'task'
- **Fix**: Replace with '/nfr-assess' or 'nfr-assess skill'

**TC001**: `commands/qa.md`:116
- **Issue**: Skill 'nfr-assess' referred to as 'task'
- **Fix**: Replace with '/nfr-assess' or 'nfr-assess skill'

**TC001**: `commands/qa.md`:193
- **Issue**: Skill 'risk-profile' referred to as 'task'
- **Fix**: Replace with '/risk-profile' or 'risk-profile skill'

**TC001**: `commands/qa.md`:194
- **Issue**: Skill 'risk-profile' referred to as 'task'
- **Fix**: Replace with '/risk-profile' or 'risk-profile skill'

**TC001**: `commands/qa.md`:195
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC001**: `commands/sm.md`:102
- **Issue**: Skill 'create-epic' referred to as 'task'
- **Fix**: Replace with '/create-epic' or 'create-epic skill'

**TC001**: `commands/sm.md`:186
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC001**: `commands/sm.md`:286
- **Issue**: Skill 'correct-course' referred to as 'task'
- **Fix**: Replace with '/correct-course' or 'correct-course skill'

**TC001**: `commands/sm.md`:289
- **Issue**: Skill 'execute-checklist' referred to as 'task'
- **Fix**: Replace with '/execute-checklist' or 'execute-checklist skill'

**TC001**: `commands/support.md`:95
- **Issue**: Skill 'validate-issue' referred to as 'task'
- **Fix**: Replace with '/validate-issue' or 'validate-issue skill'

**TC001**: `commands/support.md`:99
- **Issue**: Skill 'investigate-root-cause' referred to as 'task'
- **Fix**: Replace with '/investigate-root-cause' or 'investigate-root-cause skill'

**TC001**: `commands/support.md`:103
- **Issue**: Skill 'create-failing-test' referred to as 'task'
- **Fix**: Replace with '/create-failing-test' or 'create-failing-test skill'

**TC001**: `utils/jira-integration.md`:270
- **Issue**: Skill 'validate-issue' referred to as 'task'
- **Fix**: Replace with '/validate-issue' or 'validate-issue skill'

**TC001**: `skills/shared/reference/best-practices.md`:481
- **Issue**: Skill 'risk-profile' referred to as 'task'
- **Fix**: Replace with '/risk-profile' or 'risk-profile skill'

### Info

**TC006**: `docs/reference/claude-code-features/tasks.md`:66
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:70
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:74
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'


