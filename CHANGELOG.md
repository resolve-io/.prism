# Changelog

All notable changes to the PRISM Development System plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-10-27

### Added
- **Hooks Manager Skill** - Complete skill for managing Claude Code hooks
  - Created comprehensive hooks-manager skill with 15 commands
  - Reference documentation: commands.md (819 lines), event-types.md (764 lines), examples.md (648 lines)
  - New security.md (378 lines) with threat models, checklists, and secure patterns
  - 13 pre-built hook patterns for logging, safety, automation, and notifications
  - Progressive disclosure structure following skill-builder patterns

- **PRISM Workflow Hooks** - Active hooks enforcing core-development-cycle workflow
  - enforce-story-context: Blocks workflow commands requiring story context
  - track-current-story: Captures story file path from *draft command
  - validate-story-updates: Ensures required sections in story files
  - validate-required-sections: Status-based validation of story completeness

### Changed
- **Hooks Configuration Format** - Updated to official Claude Code format
  - Migrated from flat array to nested `hooks.EventName[].matcher.hooks[]` structure
  - Added `${CLAUDE_PLUGIN_ROOT}` variable for all plugin hook paths
  - Added `"type": "command"` property to all hook definitions
  - Updated hooks/hooks.json with correct nested format

- **Progressive Disclosure Compliance** - hooks-manager skill optimization
  - Reduced SKILL.md from 363 lines to 179 lines (51% reduction)
  - Moved detailed content to reference files (Level 3 progressive disclosure)
  - Added quick start with 3-level learning path (30 sec → 2 min → deep dive)
  - All reference .md files properly organized in /reference/ folder

### Fixed
- **Hook Event Accuracy** - Corrected blocking behavior per official docs
  - Updated exit code 2 behavior documentation per event type
  - Fixed PostToolUse blocking description (tool already executed, stderr to Claude)
  - Added accurate exit code behavior to all 9 event types
  - Documented UserPromptSubmit blocking (erases prompt, stderr to user)
  - Clarified Stop/SubagentStop blocking behavior (blocks stoppage)

### Documented
- **Complete Hook Schema** - Canonical configuration reference
  - Added Configuration Format section to commands.md (142 lines)
  - Documented plugin vs user-level hooks differences
  - Complete TypeScript schema notation for hooks.json
  - All 9 event names with timing and blocking capabilities
  - Matcher patterns, exit codes, and timeout configurations
  - PRISM's actual working configuration as reference example

### Validated
- All 4 PRISM hooks correctly formatted and functional
- hooks-manager skill follows progressive disclosure patterns
- 2,788 lines of comprehensive hooks documentation
- Configuration matches official docs.claude.com specification
- Security best practices documented with 5 threat models

## [1.3.0] - 2025-10-24

### Added
- **Complete Token Documentation** - Comprehensive token flow analysis and documentation
  - Documented distinction between runtime tokens and template placeholders
  - Added TOKEN RESOLUTION section to workflow header explaining {epic} and {story} are templates
  - Enhanced draft_story output documentation with concrete examples
  - Added `actual` field to all artifacts showing example resolved paths
  - Documented how SM agent determines epic/story identifiers during execution
  - Documented how QA agent generates {YYYYMMDD} timestamps and {slug} values

### Changed
- **Command Parameter Consistency** - Fixed all token naming drift
  - Updated all QA commands: `{story_file}` → `{story}` to match skill signatures
  - Fixed: `*risk {story}`, `*design {story}`, `*review {story}`, `*gate {story}`
  - Fixed: `*validate-story-draft {story}` to match PO skill signature
  - All commands now include clarification: "Parameter {story} receives value from: $draft_story.output.story_file"
  - Established clear pattern: workflow internal variables use `story_file`, commands use `{story}`

- **Strangler Pattern Workflow** - Complete rewrite to use actual dev commands
  - Removed non-existent commands: `task`, `execute-checklist`, `develop`, `validate`
  - Simplified from 7 granular steps to 2 high-level orchestration steps
  - Now uses actual commands: `strangler` (delegates to tasks/strangler-pattern.md) and `run-tests`
  - Updated version to 1.1.0
  - Workflow now properly separates orchestration (workflow) from implementation (skills/tasks)

### Fixed
- **Token Flow Validation** - All tokens fully accounted for
  - Verified single runtime token (`story_file`) flows correctly through all 7 dependent steps
  - Confirmed all dependency chains ensure token availability
  - Validated all template placeholders are properly documented as patterns, not runtime values
  - All artifacts section now clearly shows template patterns vs actual examples

### Validated
- 100% token accountability: 1 runtime token, 7 consumers, 0 undefined references
- All workflow actions (11 total) map to existing skill commands
- Token dependency chain verified: all steps requiring story_file properly depend on draft_story
- Command parameter consistency: all skills and workflows use matching token names
- Cross-system validation: skills, workflows, shared docs, utils all consistent

## [1.2.0] - 2025-10-24

### Added
- **Explicit Story Context Pattern** - CRITICAL FIX for workflow continuity
  - Added `output.story_file` to `draft_story` step to capture created story path
  - Added `input.story_file` to ALL subsequent workflow steps (risk_assessment, test_design, validate_story, implement_tasks, qa_review, address_review_issues, update_gate)
  - Story file path explicitly flows from draft_story through all phases
  - Added comprehensive header documentation explaining story context pattern
  - Each step now documents the exact command with {story_file} parameter

### Changed
- **Workflow Documentation** - Enhanced clarity for story file handling
  - All QA commands now show explicit `Command: *risk {story_file}` format
  - All Dev commands document story file context awareness
  - Updated workflow notes to emphasize single source of truth pattern
  - Added "Uses story file from draft_story step as input" to all relevant steps

### Fixed
- **Story Context Continuity** - Resolved critical ambiguity in workflow
  - Previous version: Workflow didn't specify which story file to work on after creation ❌
  - Current version: Explicitly passes story_file path from draft_story to all dependent steps ✅
  - Ensures all agents (QA, PO, Dev) work on the SAME story throughout lifecycle
  - Eliminates confusion about which file in docs/stories/ to operate on

## [1.1.0] - 2025-10-24

### Changed
- **Core Development Cycle Workflow** - Major cleanup and validation
  - Fixed all skill command mappings to use correct command names
  - Updated `validate_story` to use `validate-story-draft` (PO command)
  - Updated `implement_tasks` to use `develop-story` (Dev command)
  - Updated `address_review_issues` to use `review-qa` (Dev command)
  - Consolidated validation steps into single `develop-story` command
  - Removed intermediate `run_validations` and `mark_ready_for_review` steps

### Removed
- **Early Validation QA Commands** - Simplified brownfield workflow
  - Removed `trace` (requirements tracing) from mid-development
  - Removed `nfr-assess` (non-functional requirements) from early validation
  - Removed references from workflow, skills, and shared commands
  - Updated workflow notes to reflect streamlined brownfield process

### Fixed
- **Progressive Disclosure References** - Cleaned up broken file references
  - Removed references to non-existent SM reference files (epic-decomposition, psp-sizing, story-planning)
  - Removed references to non-existent PO reference files (validation-checklist)
  - Removed references to non-existent Dev reference files (tdd-methodology, coding-standards, testing-patterns)
  - Removed references to non-existent QA reference files (risk-assessment, review-methodology)
  - SM and PO skills now self-contained with inline guidance
  - Dev and QA skills reference only existing files (development-workflow.md, test-framework.md)

### Added
- **Directory Structure** - Created missing artifact directories
  - Added `docs/qa/assessments/` for risk and test-design outputs
  - Added `docs/qa/gates/` for quality gate decision files
  - Added `docs/stories/` for story documents
  - Added `docs/epics/` for epic documents

### Validated
- All 9 workflow actions map to existing skill commands (100% coverage)
- All 4 progressive disclosure chains verified and complete
- All file references point to existing files
- Complete workflow execution path validated
- All artifact output directories exist and ready

## [1.0.0] - 2024-10-23

### Added
- Initial release of PRISM Development System plugin
- Seven specialized agent personas:
  - **Architect** - System architecture and design
  - **Dev** - Full-stack development with TDD workflow
  - **QA** - Quality assurance and testing
  - **Product Owner** - Requirements and story validation
  - **Story Master** - Epic decomposition and PSP sizing
  - **Peer** - Code review and mentoring
  - **Support** - Issue validation and triage
- Skill-builder toolkit for creating new skills with progressive disclosure patterns
- Comprehensive task library for common development workflows
- Template system for consistent documentation
- Checklist framework for quality gates
- Jira integration for issue context (optional)
- Security best practices with environment variable management
- Validation tools for skill structure and quality

### Documentation
- Complete PRISM methodology documentation
- Security guidelines for credential management
- Installation instructions for Claude Code
- Jira integration setup guide
- Progressive disclosure pattern reference
- Development workflow guides

### Infrastructure
- MIT License
- Semantic versioning
- Git-based distribution
- Plugin marketplace ready

[1.0.0]: https://github.com/resolve-io/.prism/releases/tag/v1.0.0
