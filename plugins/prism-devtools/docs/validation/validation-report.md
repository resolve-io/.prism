# PRISM Documentation Validation Report

**Generated**: 2026-02-12 19:17:01

---

## Executive Summary

- **Files Checked**: 179/204
- **Coverage**: 87.7%
- **Total Issues**: 160

### Issues by Severity

- **Critical**: 4
- **Warning**: 30
- **Info**: 126

### Issues by Category

- **Cross Reference**: 35
- **Progressive Disclosure**: 86
- **Structure**: 1
- **Claude Code Features**: 1
- **Terminology**: 37

---

## Cross Reference Issues

### Critical

**CR001**: `skills/README.md`:58
- **Issue**: Broken link: './orca-local-setup/SKILL.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `skills/README.md`:59
- **Issue**: Broken link: './orca-api-test/SKILL.md' does not exist
- **Fix**: Verify the target file exists or update the link path

**CR001**: `artifacts/stories/story-001-prism-system-validation.md`:130
- **Issue**: Broken link: 'path' does not exist
- **Fix**: Verify the target file exists or update the link path

### Warning

**SB021**: `skills/file-first/reference/README.md`
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
- **Issue**: Circular reference detected: skills/jira/SKILL.md → skills/jira/reference/README.md → skills/jira/reference/extraction-format.md → skills/jira/SKILL.md
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
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/progressive-disclosure.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/progressive-disclosure.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/reference/dynamic-manifests.md`
- **Issue**: Circular reference detected: skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/reference/dynamic-manifests.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

**SB013**: `skills/skill-builder/SKILL.md`
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/SKILL.md
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
- **Issue**: Circular reference detected: skills/skill-builder/SKILL.md → skills/skill-builder/reference/quick-reference.md → skills/skill-builder/reference/philosophy.md → skills/skill-builder/reference/skill-creation-process.md → skills/skill-builder/reference/progressive-disclosure.md → skills/skill-builder/reference/dynamic-manifests.md → skills/skill-builder/reference/deferred-loading.md → skills/skill-builder/SKILL.md
- **Fix**: Consider if this cycle is intentional for navigation, or remove one link to break the cycle

*... and 11 more Info issues*


## Progressive Disclosure Issues

### Warning

**SB016**: `skills/file-first/SKILL.md`
- **Issue**: Missing recommended section: 'quick start' (immediate action path)
- **Fix**: Add a section about immediate action path

### Info

**PD005**: `CHANGELOG.md`
- **Issue**: Long document (704 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `CLAUDE.md`
- **Issue**: Long document (596 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `README.md`
- **Issue**: Long document (263 lines) missing disclosure techniques
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
- **Issue**: Long document (461 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/requirements-tracer.md`
- **Issue**: Long document (522 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `agents/test-runner.md`
- **Issue**: Long document (218 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/architect-checklist.md`
- **Issue**: Long document (440 lines) missing disclosure techniques
- **Fix**: Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files

**PD005**: `checklists/architecture-validation-checklist.md`
- **Issue**: Long document (273 lines) missing disclosure techniques
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

*... and 65 more Info issues*


## Structure Issues

### Critical

**SB001**: `skills/file-first/TESTING.md`
- **Issue**: Reference file 'TESTING.md' in skill root instead of /reference/
- **Fix**: Move to skills/file-first/reference/TESTING.md


## Claude Code Features Issues

### Info

**CC006**: `.claude/settings.json`
- **Issue**: No .claude/settings.json found
- **Fix**: Create settings.json to configure Claude Code behavior


## Terminology Issues

### Warning

**TC005**: `commands/architect.md`:24
- **Issue**: Conflating declaration found: '- TASKS ARE SKILLS: tasks map to .prism/skills/{task-name}/SKILL.md (e.g., document-project.md → .prism/skills/document-project/SKILL.md)'
- **Fix**: Remove or rewrite. Skills (/slash-commands) are distinct from Task tool (delegation).

**TC001**: `commands/architect.md`:79
- **Issue**: Skill 'fetch-jira-issue' referred to as 'task'
- **Fix**: Replace with '/fetch-jira-issue' or 'fetch-jira-issue skill'

**TC005**: `commands/po.md`:24
- **Issue**: Conflating declaration found: '- TASKS ARE SKILLS: tasks map to .prism/skills/{task-name}/SKILL.md (e.g., create-epic.md → .prism/skills/create-epic/SKILL.md)'
- **Fix**: Remove or rewrite. Skills (/slash-commands) are distinct from Task tool (delegation).

**TC001**: `commands/po.md`:79
- **Issue**: Skill 'fetch-jira-issue' referred to as 'task'
- **Fix**: Replace with '/fetch-jira-issue' or 'fetch-jira-issue skill'

**TC001**: `commands/po.md`:81
- **Issue**: Skill 'create-epic' referred to as 'task'
- **Fix**: Replace with '/create-epic' or 'create-epic skill'

**TC001**: `commands/po.md`:83
- **Issue**: Skill 'correct-course' referred to as 'task'
- **Fix**: Replace with '/correct-course' or 'correct-course skill'

**TC005**: `commands/qa.md`:24
- **Issue**: Conflating declaration found: '- TASKS ARE SKILLS: tasks map to .prism/skills/{task-name}/SKILL.md (e.g., qa-gate.md → .prism/skills/qa-gate/SKILL.md)'
- **Fix**: Remove or rewrite. Skills (/slash-commands) are distinct from Task tool (delegation).

**TC001**: `commands/qa.md`:88
- **Issue**: Skill 'fetch-jira-issue' referred to as 'task'
- **Fix**: Replace with '/fetch-jira-issue' or 'fetch-jira-issue skill'

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

**TC005**: `commands/sm.md`:24
- **Issue**: Conflating declaration found: '- TASKS ARE SKILLS: tasks map to .prism/skills/{task-name}/SKILL.md (e.g., create-epic.md → .prism/skills/create-epic/SKILL.md)'
- **Fix**: Remove or rewrite. Skills (/slash-commands) are distinct from Task tool (delegation).

**TC001**: `commands/sm.md`:99
- **Issue**: Skill 'fetch-jira-issue' referred to as 'task'
- **Fix**: Replace with '/fetch-jira-issue' or 'fetch-jira-issue skill'

**TC001**: `commands/sm.md`:102
- **Issue**: Skill 'create-epic' referred to as 'task'
- **Fix**: Replace with '/create-epic' or 'create-epic skill'

**TC001**: `commands/sm.md`:186
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC001**: `commands/sm.md`:264
- **Issue**: Skill 'probe-estimation' referred to as 'task'
- **Fix**: Replace with '/probe-estimation' or 'probe-estimation skill'

**TC001**: `commands/sm.md`:286
- **Issue**: Skill 'correct-course' referred to as 'task'
- **Fix**: Replace with '/correct-course' or 'correct-course skill'

*... and 8 more Warning issues*

### Info

**TC006**: `commands/dev.md`:77
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC006**: `commands/po.md`:27
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC006**: `commands/qa.md`:27
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC006**: `commands/sm.md`:27
- **Issue**: Skill 'create-next-story' referred to as 'task'
- **Fix**: Replace with '/create-next-story' or 'create-next-story skill'

**TC006**: `commands/support.md`:27
- **Issue**: Skill 'validate-issue' referred to as 'task'
- **Fix**: Replace with '/validate-issue' or 'validate-issue skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:66
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:70
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:74
- **Issue**: Skill 'test-design' referred to as 'task'
- **Fix**: Replace with '/test-design' or 'test-design skill'

**TC006**: `docs/reference/claude-code-features/tasks.md`:451
- **Issue**: Skill 'probe-estimation' referred to as 'task'
- **Fix**: Replace with '/probe-estimation' or 'probe-estimation skill'


