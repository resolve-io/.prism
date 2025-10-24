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

### create-architecture

**Purpose**: Intelligently create architecture documentation based on your project type

**What it does**:
- Analyzes your PRD (`docs/prd.md`) and project context
- Recommends the appropriate template:
  - **Full-Stack** (`fullstack-architecture-tmpl.yaml`): Frontend + backend + infrastructure
  - **Backend/Services** (`architecture-tmpl.yaml`): APIs, databases, services, microservices
  - **Frontend Only**: Discusses standalone frontend architecture needs
- Explains recommendation with clear rationale
- Gets explicit user confirmation
- Executes `create-doc` task with confirmed template

**When to use**:
- Designing any new system architecture
- Documenting existing architecture
- Planning application structure
- Technology selection and evaluation

**Examples**:
```
"Create architecture for our project"
→ Analyzes docs/prd.md
→ Detects web app with API backend
→ Recommends fullstack template
→ Creates comprehensive architecture covering both layers

"Design the architecture"
→ Detects backend-only microservice project
→ Recommends backend-focused template
→ Creates service architecture with API specs
```

**Output varies by project type**:

**Full-Stack Projects**:
- System overview (all layers)
- Platform and infrastructure choices
- Frontend architecture (components, routing, state)
- Backend architecture (APIs, services, data)
- Unified project structure (monorepo)
- Integration patterns
- End-to-end workflows
- Development and deployment

**Backend/Services Projects**:
- System overview and components
- API design and endpoints
- Service architecture
- Database schema and data flow
- Security architecture
- Error handling and logging
- Infrastructure and deployment

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

2. Create architecture (intelligently adapts to project type):
   create-architecture

3. Research specific topics as needed:
   research "authentication patterns for SaaS"

4. Quality check:
   execute-checklist

5. Break into phases:
   shard-prd

6. Export document:
   doc-out
```

### Project Documentation Flow

```
1. Document current state:
   document-project

2. Research improvement patterns:
   research "microservices migration strategies"

3. Quality check:
   execute-checklist

4. Plan implementation:
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
- `architecture-tmpl.yaml` - Backend/services architecture
- `fullstack-architecture-tmpl.yaml` - Full-stack architecture

### Checklists (`.prism/checklists/`)
- `architect-checklist.md` - Architecture quality checklist

### Utils (`.prism/utils/`)
- `jira-integration.md` - Jira API integration

---

## Natural Language Command Mapping

You don't need to memorize command names. The skill understands natural language:

| You say | Maps to |
|---------|---------|
| "Design the architecture" | `create-architecture` |
| "Create architecture document" | `create-architecture` |
| "Design backend architecture" | `create-architecture` (recommends backend template) |
| "Full-stack architecture" | `create-architecture` (recommends fullstack template) |
| "Research GraphQL vs REST" | `research "GraphQL vs REST"` |
| "Document this project" | `document-project` |
| "Run quality checklist" | `execute-checklist` |
| "Get context from PLAT-123" | `jira PLAT-123` |
| "Break into phases" | `shard-prd` |

The skill flexibly matches your intent to the appropriate command.

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
