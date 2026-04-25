# PRISM Documentation Validation Report

**Generated**: 2026-04-24 23:29:36

---

## Executive Summary

- **Files Checked**: 196/219
- **Coverage**: 89.5%
- **Total Issues**: 171

### Issues by Severity

- **Critical**: 0
- **Warning**: 71
- **Info**: 100

### Issues by Category

- **Cross Reference**: 35
- **Progressive Disclosure**: 130
- **Claude Code Features**: 1
- **Terminology**: 5

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

**PD002**: `skills/document-project/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/initialize-architecture/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/nfr-assess/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/risk-profile/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/sdlc-handoff/SKILL.md`:9
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**PD002**: `skills/version-bump/SKILL.md`:13
- **Issue**: Document starts with H2 instead of H1
- **Fix**: Start document with a single H1 heading

**SB016**: `skills/agent-builder/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/agent-builder/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/apply-qa-fixes/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/apply-qa-fixes/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/brain/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/brain/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/conductor/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/conductor/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/correct-course/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/create-dev-task/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

**SB016**: `skills/create-dev-task/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

**SB016**: `skills/create-failing-test/SKILL.md`
- **Issue**: Missing recommended section: 'when to use' (whenToUse or trigger conditions)
- **Fix**: Add a section about whenToUse or trigger conditions

*... and 44 more Warning issues*

### Info

**PD005**: `CHANGELOG.md`
- **Issue**: Long document (1127 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `CLAUDE.md`
- **Issue**: Long document (479 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `README.md`
- **Issue**: Long document (263 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/architecture-compliance-checker.md`
- **Issue**: Long document (174 lines) missing disclosure techniques
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

**PD005**: `hooks/README.md`
- **Issue**: Long document (232 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `scripts/README.md`
- **Issue**: Long document (430 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `utils/jira-integration.md`
- **Issue**: Long document (293 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `utils/prism-doc-template.md`
- **Issue**: Long document (327 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/agent-examples.md`
- **Issue**: Long document (628 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/best-practices.md`
- **Issue**: Long document (617 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/configuration-guide.md`
- **Issue**: Long document (371 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/instructions.md`
- **Issue**: Long document (199 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/prism-agent-strategy.md`
- **Issue**: Long document (711 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/agent-builder/reference/troubleshooting.md`
- **Issue**: Long document (789 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `skills/apply-qa-fixes/reference/instructions.md`
- **Issue**: Long document (172 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

*... and 46 more Info issues*


## Claude Code Features Issues

### Info

**CC006**: `.claude/settings.json`
- **Issue**: No .claude/settings.json found
- **Fix**: Create settings.json to configure Claude Code behavior


## Terminology Issues

### Warning

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


