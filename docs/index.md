# PRISM Documentation Index

## Core Documentation

### 📋 Workflow & Process
- **[PRISM Development Workflow](./prism-workflow.md)**
  - Complete development cycle
  - Mandatory quality gates
  - No optional steps - unambiguous process
  - Stage-by-stage implementation guide

### 📁 Planning & Organization
- **[Planning Artifacts Guide](./planning-artifacts.md)**
  - Standard directory structure
  - File naming conventions
  - Document templates
  - Path validation rules

## Quick Start

### For New Projects
1. Read the [PRISM Development Workflow](./prism-workflow.md)
2. Set up directories per [Planning Artifacts Guide](./planning-artifacts.md)
3. Create PRD at `docs/prd.md`
4. Create Architecture at `docs/architecture.md`
5. Begin development cycle

### For Existing Projects
1. Review [Planning Artifacts Guide](./planning-artifacts.md) migration section
2. Reorganize files to standard structure
3. Validate using compliance checklist
4. Begin PRISM workflow

## Key Concepts

### PRISM Principles
- **P**redictability - Consistent patterns and processes
- **R**esilience - Robust error handling and recovery
- **I**ntentionality - Clear purpose in every decision
- **S**ustainability - Long-term maintainability focus
- **M**aintainability - Easy to understand and modify

### Mandatory Workflow Steps
1. SM drafts story from epic
2. PO validates story (MANDATORY)
3. User approves story
4. Dev implements with tests
5. QA reviews and gates
6. Final verification and commit

### Standard Paths
```
docs/
├── prd.md                 # Product Requirements
├── architecture.md        # System Architecture
├── epics/                # Sharded Epics
├── stories/              # Sharded Stories
└── qa/                   # Quality Artifacts
    ├── assessments/      # QA Assessments
    └── gates/           # Quality Gates
```

## Agent Commands Reference

### Story Master (SM)
- `/sm` - Story planning and drafting
- Key: `*draft`, `*decompose`

### Product Owner (PO)
- `/po` - Story validation
- Key: `*validate-story-draft` (MANDATORY)

### Developer (Dev)
- `/dev {story}` - Implementation
- Key: `*develop-story`

### QA Test Architect (QA)
- `/qa` - Quality review
- Key: `*review`, `*gate`

## No Ambiguity Policy

PRISM enforces:
- **No optional steps** - Every step is mandatory
- **No shortcuts** - Full process for every story
- **No exceptions** - Same workflow for all work
- **Clear gates** - Pass/Fail at each checkpoint
- **Documented decisions** - Everything traceable

---
*PRISM Documentation - Version 1.0*