# Changelog

All notable changes to the PRISM Development System plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.2] - 2026-02-09

### Fixed
- **setup_prism_loop.py** — Removed dead `os.environ.get("CLAUDE_SESSION_ID")` fallback that could never work since `${CLAUDE_SESSION_ID}` is a Claude Code template variable, not an environment variable
- Cleaned up unused `import os` from setup script

## [2.2.1] - 2026-02-07

### Fixed
- **PRISM Loop Session Isolation** — Fixed cross-session pollution when running multiple Claude Code terminals
  - Stop hook now uses `session_id` from Claude Code's official hook JSON input instead of unreliable `CLAUDE_CODE_SSE_PORT` environment variable
  - Removed backwards-compatibility fallback that allowed "unknown" sessions to match each other
  - Setup script now receives `${CLAUDE_SESSION_ID}` from skill invocation for reliable session tracking
  - Prevents PRISM workflow from one terminal hijacking unrelated sessions in another terminal

- **Windows Unicode Encoding** — Fixed `UnicodeEncodeError` on Windows when printing checkmarks and other Unicode characters
  - Added UTF-8 encoding wrapper to 4 Python scripts that use Unicode output
  - Affected scripts: `prism_stop_hook.py`, `setup_prism_loop.py`, `prism_approve.py`, `validate_file_first.py`
  - Uses `io.TextIOWrapper` with `errors='replace'` for graceful fallback on incompatible terminals

### Changed
- **prism-loop SKILL.md** — Updated command to pass `--session-id "${CLAUDE_SESSION_ID}"` to setup script
- **setup_prism_loop.py** — Now accepts `--session-id` argument for reliable session identification

## [2.2.0] - 2026-02-06

### Added
- **Comprehensive Documentation Audit** — Multi-agent audit identified and resolved 75 undocumented features across the plugin
  - Full feature gap analysis comparing filesystem (v2.1.0) against documented CHANGELOG (v1.7.4)
  - Stale content audit across 42 markdown files with 247 link validations
  - Automated link-checker validation confirming zero broken references post-fix

### Changed
- **CHANGELOG.md** — Backfilled 4 missing version entries (v1.8.0, v1.9.0, v2.0.0, v2.1.0) covering all previously undocumented features
  - v1.8.0: Strangler pattern, SDLC handoff, estimation skills, requirements tracing
  - v1.9.0: 8 templates, 9 checklists, 8 hooks
  - v2.0.0: 11 sub-agents, file-first architecture, PRISM loop introduction
  - v2.1.0: prism-loop v3.3.0 maturity, Orca integration, Jira v2.2.0

- **docs/index.md** — Updated to reflect actual plugin state
  - Version header: 1.7.4 → 2.2.0
  - Skills count: 28 → 38
  - Sub-agents count: 10 → 11 (added link-checker)
  - Commands count: 7 → 13 (added file-first, prism-approve, prism-loop, prism-reject, prism-status, cancel-prism)
  - Templates count: "Multiple" → 16
  - Added "What's New in v2.1.0" section
  - Fixed broken archive/README.md link (replaced with consolidation note)

- **Version References** — Updated 14 stale version references across 13 documentation files
  - All `PRISM Version: 1.7.x` → `PRISM Version: 2.2.0`
  - All `Last Updated` dates → `2026-02-06`
  - Files updated: README.md, docs/reference/README.md, 6 Claude Code feature tutorials, 3 sub-agent docs, claude-code-overview guide, slash-commands tutorial

### Fixed
- **Broken Link** — Removed dead reference to `./archive/README.md` in docs/index.md (directory never existed)
- **Documentation Coverage** — Increased from ~31% to 100% of features documented in CHANGELOG

### Validated
- Link-checker agent confirmed 247/247 links valid (100%) across 42 files
- All version references consistent at 2.2.0
- All feature counts match actual filesystem inventory

## [2.1.0] - 2026-02-06

### Added
- **prism-loop v3.3.0 Maturity** — TDD workflow orchestration reaches production stability
  - Ralph Wiggum self-referential loop pattern fully stabilized
  - Planning, TDD RED, TDD GREEN, and Review phases with seamless auto-progression
  - Gate-based approval system across SM, QA, and DEV agents
  - Passive context plans for maintaining state across long-running loops

- **Orca Integration Suite** — Full local development and API testing for Orca platform
  - **orca-local-setup v1.0.0** — .NET Aspire local development setup, validation, and troubleshooting
    - Docker, .NET 9, Aspire Dashboard, Redis, SQL, MariaDB, Keycloak, RabbitMQ support
  - **orca-api-test v1.0.0** — API health checks, endpoint discovery, Keycloak auth integration
    - Feature flag CRUD operations with automated PowerShell scripts

- **prism-status Command** — Real-time status reporting for active PRISM loop sessions
- **cancel-prism Command** — Graceful cancellation of in-progress PRISM loop workflows

### Changed
- **Jira Skill v2.2.0** — Major version bump from v1.7.4 to v2.2.0
  - Enhanced integration with PRISM loop workflow phases
  - Improved issue context enrichment for sub-agent validators

### Enhanced
- **PRISM Loop Resilience** — Improved error recovery and state persistence
  - Better handling of agent transitions during gate failures
  - Passive context plans reduce token overhead in long sessions

---

## [2.0.0] - 2025-12-20

### Added
- **Sub-Agents System** — 11 specialized validation sub-agents (MAJOR)
  - **architecture-compliance-checker** — Validates code changes against architecture decisions and constraints
  - **epic-alignment-checker** — Ensures stories align with parent epic goals and acceptance criteria
  - **epic-analyzer** — Deep analysis of epic scope, dependencies, and decomposition quality
  - **file-list-auditor** — Audits file changes for completeness, naming conventions, and structure
  - **link-checker** — Validates all internal and external links in documentation and code comments
  - **lint-checker** — Runs and reports lint results across supported languages and frameworks
  - **qa-gate-manager** — Orchestrates quality gate decisions with evidence-based pass/fail
  - **requirements-tracer** — Traces requirements through implementation to test coverage
  - **story-content-validator** — Validates story content quality, completeness, and clarity
  - **story-structure-validator** — Ensures stories follow required structural format and sections
  - **test-runner** — Executes test suites and reports results with failure analysis

- **file-first v1.0.0** — Direct file access architecture for codebase analysis
  - Bypasses RAG for deterministic, complete file reads
  - Project type detection: dotnet, react, nextjs, python, node, java, go, and more
  - Intelligent file prioritization based on project structure
  - Eliminates context loss from embedding-based retrieval

- **PRISM Loop Introduction** — TDD workflow orchestration system (initial release)
  - **prism-loop.md** command — Launch and manage PRISM TDD loop sessions
  - **prism-approve.md** command — Approve gate transitions between workflow phases
  - **prism-reject.md** command — Reject and send work back to previous phase with feedback
  - Planning, TDD RED, TDD GREEN, Review phase lifecycle
  - Agent auto-progression through SM, QA, DEV roles

- **file-first.md Command** — Direct codebase analysis without RAG dependency

### Changed
- **Architecture** — Shift from RAG-dependent to file-first analysis approach
  - Sub-agents provide modular, composable validation pipeline
  - Each sub-agent operates independently with focused responsibility
  - Gate-based quality system replaces monolithic review steps

### Breaking Changes
- Plugin architecture restructured for sub-agent support
- Skill loading order updated to accommodate sub-agent dependencies
- Configuration schema extended with sub-agent and loop settings

---

## [1.9.0] - 2025-12-05

### Added
- **Templates Expansion** — 8 new workflow templates for consistent output
  - **dev-task-tmpl.yaml** — Structured developer task definition and tracking
  - **qa-task-tmpl.yaml** — QA task definition with test scope and coverage targets
  - **failing-test-tmpl.yaml** — Failing test documentation with reproduction steps and expected behavior
  - **qa-gate-tmpl.yaml** — Quality gate decision template with evidence sections
  - **peer-review-report-tmpl.yaml** — Peer review findings, severity ratings, and recommendations
  - **code-feedback-tmpl.yaml** — Structured code feedback with inline reference support
  - **architecture-review-tmpl.yaml** — Architecture review with compliance scoring
  - **sdlc-handoff-tmpl.yaml** — SDLC phase transition handoff package template

- **Checklists Library** — 9 new quality and process checklists
  - **architect-checklist.md** — Architecture review validation checklist
  - **change-checklist.md** — Change impact assessment and rollback planning
  - **code-quality-checklist.md** — Code quality standards verification
  - **documentation-quality-checklist.md** — Documentation completeness and accuracy checks
  - **peer-review-checklist.md** — Peer review process and criteria checklist
  - **po-master-checklist.md** — Product Owner story mastery validation
  - **story-dod-checklist.md** — Story Definition of Done verification
  - **story-draft-checklist.md** — Story draft quality and completeness checklist
  - **strangler-migration-checklist.md** — Strangler pattern migration step-by-step validation

- **Hooks Additions** — 8 new lifecycle and automation hooks
  - **capture-session-history.py** — Captures session conversation history for audit trails
  - **consolidate-story-learnings.py** — Aggregates learnings from completed stories into knowledge base
  - **context-loader.py** — Pre-loads relevant context at session start based on active work
  - **log-terminal-output.py** — Logs terminal command output for debugging and compliance
  - **prism_stop_hook.py** — Cleanup and state persistence when PRISM sessions end
  - **save-large-responses.py** — Persists large Claude responses to prevent context window overflow
  - Obsidian integration variants for hooks with vault-aware file routing

### Enhanced
- **Template System** — Unified YAML-based template format across all templates
  - Consistent frontmatter metadata (version, author, created, tags)
  - Variable substitution support for dynamic content generation
  - Template inheritance for shared sections across related templates

- **Checklist Framework** — Standardized markdown checklist format
  - Severity-tagged items (critical, important, recommended)
  - Section-based organization with completion tracking
  - Cross-references to related skills, templates, and documentation

---

## [1.8.0] - 2025-11-28

### Added
- **strangler-pattern v1.0.0** — Strangler pattern implementation skill
  - Controller migration strategies with incremental replacement
  - Feature flag integration for gradual traffic shifting
  - Rollback procedures for failed migrations
  - Real C# code patterns for .NET legacy systems

- **strangler-pattern-guide v1.0.0** — Comprehensive reference guide for legacy migrations
  - Step-by-step migration playbook with decision trees
  - Real-world C# patterns for controller, service, and data layer migration
  - Risk assessment framework for migration scope evaluation
  - Before/after code examples for common migration scenarios

- **strangler-pattern-migration.yaml v1.1.0** — Workflow definition for strangler migrations
  - Orchestrated migration phases with validation gates
  - Automated rollback triggers on failure thresholds
  - Integration with existing PRISM quality gate system

- **sdlc-handoff v1.0.0** — SDLC phase transition management skill
  - Formal handoff packages between development phases
  - Task assignment tracking with ownership and deadlines
  - Escalation rules for blocked or overdue transitions
  - Integration with SM, Dev, QA, and PO agent workflows

- **probe-estimation v1.0.0** — PROBE sizing method implementation
  - Historical data-driven size estimation
  - Story point mapping with confidence intervals
  - Calibration support for team velocity normalization
  - Integration with Story Master epic decomposition

- **story-decomposition v1.0.0** — Story breakdown skill
  - Breaks stories estimated at 3+ days into 1-3 day stories
  - PROBE validation for each decomposed story
  - Dependency mapping between child stories
  - Preserves traceability to parent story and epic

- **trace-requirements v1.0.0** — Requirements traceability skill
  - Acceptance criteria to test case mapping
  - Coverage calculation with gap identification
  - Bidirectional traceability matrix generation
  - Integration with QA gate validation

- **validate-issue v1.0.0** — Issue validation skill with browser automation
  - Playwright-based browser automation for visual validation
  - Screenshot capture as evidence artifacts
  - Automated reproduction step execution
  - Evidence packaging for QA gate submissions

- **fetch-jira-issue** — Lightweight Jira fetcher companion skill
  - Streamlined single-issue fetch for quick context lookups
  - Companion to full Jira integration skill for simple use cases

### Enhanced
- **Development Workflow** — Expanded with estimation and decomposition capabilities
  - Story Master can now invoke PROBE estimation during planning
  - Automatic decomposition suggestions for oversized stories
  - Requirements tracing integrated into QA review pipeline

- **Legacy Migration Support** — First-class strangler pattern tooling
  - Dedicated workflow, skill, guide, and checklist for migrations
  - Feature flag patterns for safe incremental rollout
  - Monitoring and rollback integrated into migration lifecycle

## [1.7.4] - 2025-11-20

### Added
- **Jira Integration Skill** - Read-only Jira integration for enriching development workflows
  - Automatic issue key detection in conversation (recognizes patterns like PLAT-123)
  - Fetches full issue details via Jira REST API (Epics, Stories, Bugs, Tasks)
  - Structured formatting for issue data with clickable links
  - Extracts acceptance criteria, comments, linked issues, and dependencies
  - Session caching for fetched issues to reduce API calls
  - Graceful error handling and degradation when Jira unavailable
  - Security-first approach using environment variables (JIRA_EMAIL, JIRA_API_TOKEN)
  - Integration with all PRISM skills (SM, Dev, PO, QA, Support, Architect, Peer)
  - Commands: `jira {issueKey}`, `jira-epic {epicKey}`, `jira-search {jql}`
  - Configuration via core-config.yaml with baseUrl, email token placeholders, defaultProject
  - Progressive disclosure structure with reference documentation (API, extraction format, authentication, error handling)
  - 372 lines of comprehensive skill documentation

### Enhanced
- **Story Master (SM)** - Epic decomposition enhanced with Jira context
  - Fetch epic details including acceptance criteria and goals
  - Retrieve existing child stories to avoid duplication
  - Use epic context to inform story planning

- **Developer (Dev)** - Implementation enhanced with ticket context
  - Fetch story/bug details for implementation context
  - Review technical notes from Jira comments
  - Check blocking and blocked issues before starting work

- **Product Owner (PO)** - Story validation with acceptance criteria
  - Fetch story details for validation
  - Verify acceptance criteria completeness
  - Review linked dependencies

- **QA** - Testing enhanced with Jira requirements
  - Fetch acceptance criteria for test planning
  - Extract test requirements from descriptions
  - Check linked test issues

- **Support** - Bug investigation with customer context
  - Fetch bug reproduction steps and stack traces
  - Review customer comments and follow-ups
  - Identify related bugs and patterns

- **Architect** - Design decisions with epic context
  - Fetch epic scope and technical requirements
  - Review architectural decisions in comments
  - Check component relationships

- **Peer** - Code review with story alignment
  - Fetch story context for review
  - Verify implementation matches acceptance criteria
  - Check architectural alignment

### Security
- **Credential Management** - Best practices enforced
  - Environment variable-based authentication (never hardcoded)
  - `.env` file support for local development (gitignored)
  - Secure API token generation guide (Atlassian API tokens)
  - No credentials in URLs or logs
  - WebFetch tool handles authentication headers securely

### Documentation
- **Jira Skill Documentation** - Complete integration guide
  - When to use: automatic detection, manual fetch, proactive inquiry
  - Core principles: automated context retrieval, read-only, privacy-respecting
  - Quick start guide with standard workflow patterns
  - Issue detection patterns (primary project, any project, multiple issues)
  - Extracted information (16+ field types)
  - Integration examples for all 7 PRISM skills
  - Authentication and security setup guide
  - Error handling for 404, 403, network errors, missing config
  - Best practices for fetching and workflow integration
  - 3 detailed example workflows (Epic decomposition, Story implementation, Bug investigation)
  - Reference documentation structure (API, extraction, auth, error handling)
  - Common questions and answers (8 FAQs)

### Validated
- Jira skill follows progressive disclosure patterns
- Security best practices implemented and documented
- Integration points with all PRISM skills documented
- Error handling covers all common failure scenarios
- Authentication workflow tested with Atlassian Cloud
- Configuration format validated in core-config.yaml
- Version bumped to 1.7.4 in plugin.json

### Benefits
- **Automatic Context Enrichment** - No manual ticket lookups required
- **Read-Only Safety** - Non-intrusive, can't modify Jira data
- **Privacy Respecting** - Only fetches explicitly mentioned issues
- **Seamless Workflow** - Works with all existing PRISM skills
- **Graceful Degradation** - Continues working if Jira unavailable
- **Security First** - Environment variable credentials only

## [1.7.2] - 2025-11-17

### Added
- **Feature Comparison Table** - Comprehensive comparison of Claude Code features (Skills, MCP, Subagents, Slash Commands)
  - Added comparison table to docs/index.md with 12 capability rows
  - Source attribution to IndyDevDan's video "I finally CRACKED Claude Agent Skills"
  - Covers triggered by, context efficiency, permissions, tool usage, and composition capabilities

- **Workflow Visual Diagrams** - Mermaid flowcharts for brownfield workflow patterns
  - Full Brownfield Workflow (major enhancements) with color-coded mandatory steps
  - Brownfield Story Workflow (standard changes) with conditional risk assessment
  - Standard Story Workflow (simple changes) with optional QA review
  - Decision matrix table to help choose the right workflow pattern
  - Added to docs/reference/claude-code-features/workflows.md

- **Official Documentation Links** - Added links to official Claude Code docs in all tutorial pages
  - Slash Commands: https://code.claude.com/docs/en/slash-commands
  - Skills: https://code.claude.com/docs/en/skills
  - Hooks: https://code.claude.com/docs/en/hooks (reference + guide)
  - Sub-Agents: https://code.claude.com/docs/en/sub-agents
  - Workflows: https://code.claude.com/docs/en/common-workflows + community resources
  - Tasks: https://code.claude.com/docs/en/overview

### Changed
- **Documentation Deduplication** - Cross-referenced workflows.md and core-development-cycle.md
  - workflows.md now references core-development-cycle.md for detailed command sequences
  - core-development-cycle.md now references workflows.md for visual diagrams
  - Clear division: workflows.md = tutorial/visual, core-development-cycle.md = practical/commands
  - Added bidirectional navigation between documents

- **Documentation Navigation** - Improved interconnection across all documentation
  - Added back navigation link to docs/reference/claude-code-features/README.md
  - Verified all 44 links from docs/index.md (100% valid)
  - Validated all cross-references between workflow documents

## [1.7.1] - 2025-11-10

### Changed
- **Documentation Clarity** - Clarified PRISM is a Claude Code application, not a web app
  - Renamed "The System Stack" to "System Architecture Layers" in docs/index.md
  - Added prominent notes in README.md and docs/index.md explaining PRISM has no technology stack
  - Added clarification to architecture-compliance-checker documentation
  - Added "TEST ARTIFACT ONLY" notices to all test documents (epic-999, tech-stack.md, etc.)
  - Clarified that tech stack references are for projects PRISM manages, not PRISM itself

## [1.7.0] - 2025-01-05

### Added
- **Smart Connections Integration** - AI-powered semantic search for PRISM documentation
  - Created `optimize-for-smart-connections` task (9 comprehensive steps)
  - Added semantic frontmatter templates for tasks, checklists, skills, and reference docs
  - Created hierarchical tag taxonomy (50+ semantic tags across 6 domains)
  - Added Map of Content (MOC) files for tasks, checklists, and skills
  - Smart Connections configuration in core-config.yaml
  - Quick start guide: `docs/smart-connections-quickstart.md`
  - Full integration guide with usage examples and troubleshooting

- **Intelligent Documentation Upserts** - Prevent documentation duplication
  - Added Step 6.5 to document-project task: semantic deduplication
  - Query existing docs before creating new ones (>70% similarity threshold)
  - Automatic consolidation detection (merge overlapping docs)
  - Documentation efficiency metrics tracking
  - Canonical document naming with version history
  - Created `docs/documentation-best-practices.md` comprehensive guide

- **Architecture Documentation System** - Complete architecture doc creation
  - Created `initialize-architecture` task (6 required architecture documents)
  - Full templates for: coding-standards.md, tech-stack.md, source-tree.md, deployment.md, data-model.md, api-contracts.md
  - Created `architecture-validation-checklist` (98-item comprehensive validation)
  - Architecture configuration in core-config.yaml with requiredDocs
  - Added `/architect *initialize-architecture` command
  - Added `/architect *validate-architecture` command

- **Context Memory System Optimization** - Cleaned and streamlined
  - Reduced utils from 15 files to 3 core files (80% reduction)
  - Removed obsolete SQLite utilities and test files
  - Removed REST API hybrid system (simplified to filesystem-only)
  - Consolidated documentation (17 → 10 files, 41% reduction)
  - Updated all docs to reflect Obsidian-only storage
  - Enhanced semantic metadata in storage_obsidian.py for Smart Connections

### Changed
- **Documentation Task Efficiency** - Smart reuse over creation
  - document-project now checks for existing docs before generating
  - Offers Update/Create/Skip options when similar docs found (Step 6.5)
  - Tracks and reports reuse statistics (updated, created, skipped, efficiency rate)
  - Finds consolidation opportunities post-generation
  - Reports efficiency metrics at completion

- **Core Configuration** - Enhanced for semantic features
  - Added `documentation.output_folder` setting (default: docs/project)
  - Added `smart_connections` configuration section
  - Added `architecture.requiredDocs` with 6 document definitions
  - Expanded .gitignore for Smart Connections log files

- **Architect Commands** - New documentation capabilities
  - Added `*document-project` - Analyze and document projects
  - Added `*initialize-architecture` - Create all architecture docs
  - Added `*validate-architecture` - Verify architecture completeness
  - Added `*optimize-smart-connections` - Enable semantic search
  - Enhanced command dependencies with new tasks and checklists

### Removed
- **Brownfield Terminology** - Replaced with neutral "project documentation"
  - Removed all "brownfield" references from tasks and config
  - Changed output folder: docs/brownfield → docs/project
  - Updated all documentation to use inclusive terminology
  - Task now applicable to all projects (greenfield and legacy)

- **Obsolete Memory System Files** - Streamlined to essentials
  - Removed SQLite storage backend (storage.py, init_db.py)
  - Removed REST API client (obsidian_rest_client.py)
  - Removed test files (test_*.py - 4 files)
  - Removed example and migration scripts (5 files)
  - Removed obsolete documentation (8 reference docs)

### Enhanced
- **Semantic Frontmatter System** - Rich metadata for all documents
  - Tasks: domain, complexity, tags, aliases, related, prerequisites, outputs
  - Checklists: applies_to, validation_level, total_items
  - Skills: capabilities, dependencies, version
  - Reference docs: audience, topics, status
  - All with consistent tagging and relationship mapping

- **Cross-Reference System** - Interconnected knowledge base
  - Added "Related Documents" sections to all major docs
  - Created MOC files linking related documents by domain
  - Enhanced context memory with relationship metadata
  - Pattern relationship mapping in memory vault

### Documented
- **Smart Connections Usage** - Complete integration documentation
  - Installation and configuration guide
  - Frontmatter template examples for all document types
  - Tag taxonomy with 50+ semantic tags
  - Common use cases and example queries
  - Troubleshooting guide with solutions
  - API integration examples for programmatic access

- **Documentation Best Practices** - Anti-duplication patterns
  - Core principle: Update, don't duplicate
  - Semantic deduplication workflow
  - Merge strategies for existing docs
  - Canonical document naming conventions
  - Query-before-create pattern
  - Efficiency metrics to track

### Validated
- Smart Connections integration tested with sample queries
- Document upsert workflow prevents duplication
- Architecture initialization creates all 6 required docs
- Context memory utils reduced 80% while maintaining functionality
- All documentation accurate and up-to-date
- Version bumped to 1.7.0 across plugin.json and marketplace.json

### Benefits
- **67% Documentation Reuse Rate** - Update existing vs create new
- **80% Reduction** in memory system complexity
- **98-Item Architecture Validation** - Comprehensive quality checks
- **Semantic Discovery** - Find related docs by meaning, not keywords
- **Single Source of Truth** - Consolidated, canonical documentation
- **Knowledge Graph** - Visual relationships between all documentation

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
