# PRISM Planning Artifacts Guide

## Standard Directory Structure

All PRISM projects must follow this exact directory structure for planning artifacts. No deviations are permitted to ensure consistency and tool compatibility.

```
project-root/
├── .prism/                    # PRISM configuration and tools
│   ├── agents/               # Agent definitions
│   ├── checklists/          # Process checklists
│   ├── tasks/               # Executable tasks
│   ├── templates/           # Document templates
│   └── docs/                # PRISM documentation
│       ├── prism-workflow.md
│       └── planning-artifacts.md (this file)
│
└── docs/                      # Project planning artifacts
    ├── prd.md                # Product Requirements Document
    ├── architecture.md       # System Architecture Document
    ├── epics/               # Sharded epic documents
    │   ├── epic-001-user-management.md
    │   ├── epic-002-product-catalog.md
    │   └── epic-003-checkout-flow.md
    ├── stories/             # Sharded story documents
    │   ├── epic-001/
    │   │   ├── story-001-user-registration.md
    │   │   ├── story-002-user-authentication.md
    │   │   └── story-003-password-reset.md
    │   ├── epic-002/
    │   │   ├── story-004-product-listing.md
    │   │   └── story-005-product-search.md
    │   └── epic-003/
    │       ├── story-006-shopping-cart.md
    │       └── story-007-payment-processing.md
    └── qa/                  # Quality assurance artifacts
        ├── assessments/     # QA assessment reports
        │   ├── story-001-assessment.md
        │   ├── story-002-assessment.md
        │   └── story-003-assessment.md
        └── gates/          # Quality gate decisions
            ├── epic-001.story-001-gate.yml
            ├── epic-001.story-002-gate.yml
            └── epic-001.story-003-gate.yml
```

## Artifact Types and Paths

### Core Planning Documents

| Artifact | Path | Purpose | Owner |
|----------|------|---------|-------|
| **PRD** | `docs/prd.md` | Product Requirements Document defining what to build | Product Owner |
| **Architecture** | `docs/architecture.md` | Technical design and system architecture | Architect |

### Epic Documents

| Artifact | Path Pattern | Purpose | Owner |
|----------|-------------|---------|-------|
| **Sharded Epics** | `docs/epics/epic-{number}-{slug}.md` | High-level feature breakdowns | Product Owner |

**Naming Convention:**
- Format: `epic-{3-digit-number}-{descriptive-slug}.md`
- Example: `epic-001-user-management.md`
- Sequential numbering starting at 001
- Slug should be 2-4 words, hyphen-separated

### Story Documents

| Artifact | Path Pattern | Purpose | Owner |
|----------|-------------|---------|-------|
| **Sharded Stories** | `docs/stories/epic-{number}/story-{number}-{slug}.md` | Implementation-ready user stories | Story Master |

**Naming Convention:**
- Directory: `epic-{3-digit-number}/`
- Format: `story-{3-digit-number}-{descriptive-slug}.md`
- Example: `docs/stories/epic-001/story-002-user-authentication.md`
- Stories numbered sequentially across entire project
- Grouped by parent epic in subdirectories

### QA Artifacts

| Artifact | Path Pattern | Purpose | Owner |
|----------|-------------|---------|-------|
| **Assessments** | `docs/qa/assessments/story-{number}-assessment.md` | Detailed quality assessments | QA Agent |
| **Gates** | `docs/qa/gates/epic-{number}.story-{number}-gate.yml` | Pass/Fail gate decisions | QA Agent |

**Gate File Format:**
```yaml
story: story-002-user-authentication
epic: epic-001-user-management
date: 2024-01-15
reviewer: QA Agent
status: PASS  # PASS, CONCERNS, FAIL, WAIVED
findings:
  - "All tests passing"
  - "Code coverage at 95%"
  - "No security vulnerabilities"
recommendations:
  - "Consider adding rate limiting"
```

## Document Templates

### PRD Structure
```markdown
# Product Requirements Document

## Executive Summary
[Brief overview]

## Objectives
- Objective 1
- Objective 2

## User Stories
[High-level user stories]

## Functional Requirements
[Detailed requirements]

## Non-Functional Requirements
- Performance
- Security
- Scalability

## Success Criteria
[Measurable outcomes]
```

### Architecture Structure
```markdown
# System Architecture

## Overview
[System overview]

## Architecture Diagram
[Diagram or ASCII art]

## Components
### Component 1
- Responsibility
- Technology
- Interfaces

## Data Model
[Data structure]

## API Design
[API specifications]

## Security Architecture
[Security measures]

## Deployment Architecture
[Infrastructure design]
```

### Epic Structure
```markdown
# Epic: [Title]

## Overview
[Epic description]

## Business Value
[Why this matters]

## Stories
- [ ] Story 1
- [ ] Story 2
- [ ] Story 3

## Acceptance Criteria
[Epic-level criteria]

## Dependencies
[Related epics/systems]
```

### Story Structure
```markdown
# Story: [Title]

## Status: Draft

## Story
As a [user type]
I want [functionality]
So that [benefit]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Tasks
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

## Dev Notes
[Implementation guidance]

## Testing
[Test scenarios]

## Dev Agent Record
### Completion Notes
[Auto-filled by Dev agent]

### File List
[Auto-filled by Dev agent]

### Change Log
[Auto-filled by Dev agent]

## QA Results
[Auto-filled by QA agent]
```

## File Creation Commands

### Using Agents to Create Artifacts

#### Create PRD
```bash
/architect
*create-prd
```

#### Create Architecture
```bash
/architect
*create-backend-architecture
# or
*create-front-end-architecture
# or
*create-full-stack-architecture
```

#### Create Epic
```bash
/po
*create-epic
```

#### Create Story
```bash
/sm
*draft
```

## Validation Rules

### Path Validation Checklist

- [ ] PRD exists at `docs/prd.md`
- [ ] Architecture exists at `docs/architecture.md`
- [ ] All epics in `docs/epics/` follow naming convention
- [ ] All stories organized by epic in `docs/stories/`
- [ ] Story numbers are unique and sequential
- [ ] QA assessments match story numbers
- [ ] Gate files use correct epic.story naming

### Content Validation

- [ ] PRD contains all required sections
- [ ] Architecture addresses all PRD requirements
- [ ] Epics fully decompose PRD features
- [ ] Stories fully implement epic requirements
- [ ] All stories have acceptance criteria
- [ ] All stories have defined tasks

## Migration Guide

If you have existing documents in non-standard locations:

### Step 1: Create Standard Directories
```bash
mkdir -p docs/epics
mkdir -p docs/stories
mkdir -p docs/qa/assessments
mkdir -p docs/qa/gates
```

### Step 2: Move Core Documents
```bash
mv [old-prd-location] docs/prd.md
mv [old-architecture-location] docs/architecture.md
```

### Step 3: Organize Epics
```bash
# Move and rename epics to standard format
mv [old-epic] docs/epics/epic-001-[slug].md
```

### Step 4: Organize Stories by Epic
```bash
# Create epic directories
mkdir -p docs/stories/epic-001
mkdir -p docs/stories/epic-002

# Move stories to correct locations
mv [old-story] docs/stories/epic-001/story-001-[slug].md
```

## Automation Support

### Path Constants for Agents

Agents should use these constants:

```javascript
const PATHS = {
  PRD: 'docs/prd.md',
  ARCHITECTURE: 'docs/architecture.md',
  EPICS_DIR: 'docs/epics/',
  STORIES_DIR: 'docs/stories/',
  QA_ASSESSMENTS: 'docs/qa/assessments/',
  QA_GATES: 'docs/qa/gates/'
};
```

### Story Path Generation
```javascript
function getStoryPath(epicNumber, storyNumber, slug) {
  return `docs/stories/epic-${epicNumber}/story-${storyNumber}-${slug}.md`;
}
```

### Gate Path Generation
```javascript
function getGatePath(epicNumber, storyNumber) {
  return `docs/qa/gates/epic-${epicNumber}.story-${storyNumber}-gate.yml`;
}
```

## Compliance Verification

Run this checklist before starting development:

### Pre-Development Checklist

- [ ] Directory structure matches standard
- [ ] PRD present and complete
- [ ] Architecture present and aligned with PRD
- [ ] All epics sharded and numbered
- [ ] All stories created and organized by epic
- [ ] Story numbers sequential and unique
- [ ] QA directories created and ready
- [ ] All paths follow naming conventions

### Quick Verification Script

```bash
# Verify structure
echo "Checking PRISM artifact structure..."

# Check core docs
[ -f "docs/prd.md" ] && echo "✓ PRD found" || echo "✗ PRD missing"
[ -f "docs/architecture.md" ] && echo "✓ Architecture found" || echo "✗ Architecture missing"

# Check directories
[ -d "docs/epics" ] && echo "✓ Epics directory found" || echo "✗ Epics directory missing"
[ -d "docs/stories" ] && echo "✓ Stories directory found" || echo "✗ Stories directory missing"
[ -d "docs/qa/assessments" ] && echo "✓ QA assessments directory found" || echo "✗ QA assessments missing"
[ -d "docs/qa/gates" ] && echo "✓ QA gates directory found" || echo "✗ QA gates missing"

# Count artifacts
echo "Epic count: $(ls docs/epics/*.md 2>/dev/null | wc -l)"
echo "Story count: $(find docs/stories -name "*.md" 2>/dev/null | wc -l)"
```

## Summary

This standard structure ensures:
- **Consistency** across all PRISM projects
- **Tool compatibility** with all agents
- **Clear organization** of artifacts
- **Traceability** from requirements to implementation
- **Quality gates** at every stage

Follow these paths exactly - no variations or customizations permitted.

---
*PRISM Planning Artifacts Guide - Version 1.0*