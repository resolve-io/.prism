# Architect Commands Reference

Complete reference for all architect skill commands and capabilities.

## Command Format

All commands follow this pattern:
```
command-name [arguments]
```

Commands can be invoked by:
- Mentioning the action (e.g., "create a backend architecture document")
- Using explicit command name
- Natural language that maps to command intent

## Document Creation Commands

### create-backend-architecture

**Purpose**: Create comprehensive backend system architecture document

**What it does**:
- Uses `create-doc` task with `architecture-tmpl.yaml` template
- Guides through backend system design
- Documents APIs, services, databases, infrastructure
- Includes security, performance, scalability considerations

**When to use**:
- Designing new backend systems
- Documenting existing backend architecture
- Planning API-first applications
- Microservices or monolithic architectures

**Example**:
```
"I need to design the backend architecture for our inventory management system"
```

**Output**: Backend architecture document with:
- System overview and components
- API design and endpoints
- Database schema and data flow
- Service architecture
- Security architecture
- Deployment and scaling strategy

---

### create-frontend-architecture

**Purpose**: Create comprehensive frontend application architecture document

**What it does**:
- Uses `create-doc` task with `front-end-architecture-tmpl.yaml` template
- Guides through frontend system design
- Documents UI components, state management, routing
- Includes performance, accessibility, user experience

**When to use**:
- Designing new web or mobile applications
- Documenting frontend architecture
- Planning React, Vue, Angular, or other framework projects
- SPA or MPA architecture decisions

**Example**:
```
"Design the frontend architecture for our customer portal"
```

**Output**: Frontend architecture document with:
- Application structure and routing
- Component hierarchy
- State management strategy
- API integration patterns
- Performance optimization
- Build and deployment

---

### create-fullstack-architecture

**Purpose**: Create complete application architecture (frontend + backend + infrastructure)

**What it does**:
- Uses `create-doc` task with `fullstack-architecture-tmpl.yaml` template
- Guides through entire system design
- Documents all layers: UI, API, services, data, infrastructure
- Includes end-to-end workflows

**When to use**:
- Designing complete applications
- Planning new products from scratch
- Documenting full-stack systems
- Coordinating frontend and backend development

**Example**:
```
"Create full-stack architecture for our SaaS platform"
```

**Output**: Full-stack architecture document with:
- System overview (all layers)
- Frontend architecture
- Backend architecture
- Data architecture
- Infrastructure and deployment
- Integration patterns
- End-to-end workflows

---

### create-brownfield-architecture

**Purpose**: Assess and redesign existing systems

**What it does**:
- Uses `create-doc` task with `brownfield-architecture-tmpl.yaml` template
- Analyzes current system state
- Identifies problems and technical debt
- Proposes modernization strategy
- Plans phased migration

**When to use**:
- Modernizing legacy systems
- Planning major refactoring
- Assessing technical debt
- Migration to new technologies
- System rescue/recovery

**Example**:
```
"We need to modernize our 10-year-old monolithic PHP application"
```

**Output**: Brownfield architecture document with:
- Current system assessment
- Problems and pain points
- Proposed target architecture
- Migration strategy (e.g., strangler fig pattern)
- Phased implementation plan
- Risk mitigation

---

## Analysis & Research Commands

### research {topic}

**Purpose**: Conduct deep technical research on architecture topics

**What it does**:
- Executes `create-deep-research-prompt` task
- Generates comprehensive research on specified topic
- Provides pros/cons, trade-offs, recommendations
- Includes current best practices and emerging patterns

**When to use**:
- Evaluating new technologies
- Comparing architecture patterns
- Investigating specific technical challenges
- Learning about unfamiliar domains

**Arguments**:
- `{topic}`: The subject to research (required)

**Example**:
```
research "microservices vs monolithic architecture for e-commerce"
research "GraphQL vs REST for mobile APIs"
research "serverless architecture patterns"
```

**Output**: Research report with:
- Topic overview and context
- Options and alternatives
- Pros and cons analysis
- Trade-offs and considerations
- Recommendations
- References and resources

---

### document-project

**Purpose**: Document architecture of existing project

**What it does**:
- Executes `document-project.md` task
- Analyzes current codebase structure
- Identifies components and dependencies
- Creates comprehensive architecture documentation

**When to use**:
- Documenting undocumented systems
- Onboarding new team members
- Creating architecture reference
- Preparing for refactoring

**Example**:
```
"Document the architecture of our current project"
```

**Output**: Project architecture documentation with:
- System overview
- Component inventory
- Dependencies and integrations
- Data flow
- Deployment architecture
- Technical debt notes

---

## Quality Assurance Commands

### execute-checklist

**Purpose**: Run architecture quality checklist

**What it does**:
- Executes `execute-checklist` task
- Runs through architect quality checklist
- Validates architecture against best practices
- Identifies gaps and improvements

**When to use**:
- Reviewing architecture documents
- Quality gate before implementation
- Peer review preparation
- Continuous architecture improvement

**Default checklist**: `architect-checklist.md`

**Example**:
```
"Run the architecture quality checklist"
execute-checklist architect-checklist
```

**Output**: Checklist results with:
- Completed items ✓
- Missing or incomplete items ✗
- Recommendations for improvement
- Critical issues to address

---

### shard-prd

**Purpose**: Break architecture document into implementable pieces

**What it does**:
- Executes `shard-doc.md` task
- Analyzes architecture document
- Breaks into phases and milestones
- Creates implementation roadmap

**When to use**:
- Planning implementation phases
- Breaking large projects into sprints
- Creating development roadmap
- Estimating work breakdown

**Example**:
```
"Break this architecture into implementation phases"
```

**Output**: Sharded implementation plan with:
- Phase definitions
- Dependencies between phases
- Milestone deliverables
- Estimated complexity
- Risk assessment per phase

---

## Integration Commands

### jira {issueKey}

**Purpose**: Fetch context from Jira issue

**What it does**:
- Executes `fetch-jira-issue` task
- Retrieves issue details from Jira
- Integrates context into architecture workflow
- Provides user stories, requirements, acceptance criteria

**When to use**:
- Starting architecture from Jira Epic/Story
- Getting context for architecture decisions
- Linking architecture to requirements

**Arguments**:
- `{issueKey}`: Jira issue key (e.g., PLAT-123)

**Example**:
```
jira PLAT-456
"Design architecture for PLAT-456"
```

**Output**: Jira issue context including:
- Issue summary and description
- User stories or requirements
- Acceptance criteria
- Comments and discussions
- Related issues

**Automatic detection**: The skill automatically detects Jira keys mentioned in conversation and offers to fetch context.

---

### doc-out

**Purpose**: Output complete document to file

**What it does**:
- Outputs the current architecture document
- Saves to specified or default location
- Formats for readability

**When to use**:
- Finalizing architecture document
- Saving work in progress
- Exporting for review

**Example**:
```
"Output the architecture document"
doc-out
```

---

## Utility Commands

### exit

**Purpose**: Exit architect mode

**What it does**:
- Gracefully exits architect persona
- Returns to normal Claude mode

**When to use**:
- Finished with architecture work
- Switching to different task

**Example**:
```
exit
```

---

### yolo

**Purpose**: Toggle YOLO mode (relaxed constraints)

**What it does**:
- Toggles between strict and relaxed architecture mode
- In YOLO mode: faster, less thorough, more experimental
- Normal mode: comprehensive, thorough, best practices

**When to use**:
- Rapid prototyping
- Brainstorming sessions
- Experimental designs
- Trade speed for completeness

**Example**:
```
yolo  # Toggle on
yolo  # Toggle off
```

---

## Command Workflow Examples

### Complete Architecture Flow

```
1. Start with requirements:
   jira PLAT-789  # Get context

2. Create architecture:
   create-fullstack-architecture

3. Research specific topics:
   research "authentication patterns for SaaS"

4. Quality check:
   execute-checklist

5. Break into phases:
   shard-prd

6. Export document:
   doc-out
```

### Brownfield Modernization Flow

```
1. Document current state:
   document-project

2. Create modernization plan:
   create-brownfield-architecture

3. Research migration patterns:
   research "strangler fig pattern for legacy migration"

4. Quality check:
   execute-checklist

5. Plan implementation:
   shard-prd
```

---

## Dependencies

Commands rely on:

### Tasks (`.prism/tasks/`)
- `create-doc.md` - Document creation workflow
- `document-project.md` - Project documentation
- `execute-checklist.md` - Checklist execution
- `fetch-jira-issue.md` - Jira integration
- `create-deep-research-prompt.md` - Research generation
- `shard-doc.md` - Document sharding

### Templates (`.prism/templates/`)
- `architecture-tmpl.yaml` - Backend architecture
- `front-end-architecture-tmpl.yaml` - Frontend architecture
- `fullstack-architecture-tmpl.yaml` - Full-stack architecture
- `brownfield-architecture-tmpl.yaml` - Legacy system assessment

### Checklists (`.prism/checklists/`)
- `architect-checklist.md` - Architecture quality checklist

### Utils (`.prism/utils/`)
- `jira-integration.md` - Jira API integration

---

## Natural Language Command Mapping

You don't need to memorize command names. The skill understands natural language:

| You say | Maps to |
|---------|---------|
| "Design backend architecture" | `create-backend-architecture` |
| "Create frontend architecture doc" | `create-frontend-architecture` |
| "Full-stack design" | `create-fullstack-architecture` |
| "Assess legacy system" | `create-brownfield-architecture` |
| "Research GraphQL vs REST" | `research "GraphQL vs REST"` |
| "Document this project" | `document-project` |
| "Run quality checklist" | `execute-checklist` |
| "Get context from PLAT-123" | `jira PLAT-123` |
| "Break into phases" | `shard-prd` |

The skill flexibly matches your intent to the appropriate command.

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
