---
name: document-project
description: Use to analyze and document any project codebase. Creates comprehensive reference documentation for AI-assisted development including architecture and patterns.
version: 1.0.0
---
<!-- Powered by PRISMâ„¢ System -->

# Document Project Task

## Purpose

To analyze and document any project by scanning codebase, architecture, and patterns to create comprehensive reference documentation for AI-assisted development. This task provides comprehensive project documentation workflow for PRISM plugin projects and any codebase requiring AI-assisted development context.

## When to Use

- **Project Documentation**: Document any codebase for AI understanding
- **Architecture Assessment**: Analyze current system architecture
- **Knowledge Transfer**: Create comprehensive project documentation
- **PRD Preparation**: Generate context needed for PRD creation
- **Onboarding**: Build complete project reference for new team members

## SEQUENTIAL Task Execution (Do not proceed until current task is complete)

> **Reference:** For a condensed workflow summary, see [./reference/workflow-steps.md](./reference/workflow-steps.md)

### 0. Load Configuration and Determine Output Location

**[[AGENT: Execute this step first, then confirm completion before proceeding]]**

- Load `.prism/core-config.yaml` from the project root
- If file does not exist, HALT and inform user: "core-config.yaml not found. This task requires configuration. Please ensure PRISM is properly installed."
- Look for `documentation.output_folder` in config, default to `docs/project/` if not found
- Store as `{{output_folder}}`
- **Announce to user:** "ðŸ“‹ Document Project Task Starting - Output: {{output_folder}}"
- **Announce to user:** "âœ“ Step 0 Complete: Configuration loaded"

### 1. Check for Existing Documentation and Determine Workflow Mode

**[[AGENT: Execute this step only after Step 0 is complete]]**

Check if `{{output_folder}}/index.md` exists.

**If index.md EXISTS:**

Ask user:
```
I found existing project documentation generated on {{existing_doc_date}}.

What would you like to do?

1. **Re-scan entire project** - Update all documentation with latest changes
2. **Deep-dive into specific area** - Generate detailed documentation for a particular feature/module/folder
3. **Cancel** - Keep existing documentation as-is

Your choice [1/2/3]:
```

- If user selects **1**: Set `workflow_mode = "full_rescan"` â†’ Continue to Step 2
- If user selects **2**: Set `workflow_mode = "deep_dive"` â†’ Jump to Step 6 (Deep-Dive Mode)
- If user selects **3**: Display "Keeping existing documentation. Exiting." â†’ EXIT TASK

**If index.md DOES NOT EXIST:**

- Set `workflow_mode = "initial_scan"`
- **Announce to user:** "No existing documentation found. Starting initial project scan..."
- **Announce to user:** "Workflow mode: initial_scan"
- **Announce to user:** "âœ“ Step 1 Complete: Workflow mode determined"
- **PROCEED IMMEDIATELY TO STEP 2** (do not wait for user input)

### 2. Select Scan Level (initial_scan or full_rescan modes only)

**[[AGENT: Execute this step only after Step 1 is complete and workflow_mode is set]]**

**Announce to user:** "â”â”â” Step 2: Select Scan Depth â”â”â”"

Ask user:
```
Choose your scan depth level:

**1. Quick Scan** (2-5 minutes) [DEFAULT]
   - Pattern-based analysis without reading source files
   - Scans: Config files, package manifests, directory structure
   - Best for: Quick project overview, initial understanding
   - File reading: Minimal (configs, README, package.json, etc.)

**2. Deep Scan** (10-30 minutes)
   - Reads files in critical directories based on project type
   - Scans: All critical paths from documentation requirements
   - Best for: Comprehensive documentation for PRD creation
   - File reading: Selective (key files in critical directories)

**3. Exhaustive Scan** (30-120 minutes)
   - Reads ALL source files in project
   - Scans: Every source file (excludes node_modules, dist, build)
   - Best for: Complete analysis, migration planning, detailed audit
   - File reading: Complete (all source files)

Your choice [1/2/3] (default: 1):
```

- Store user selection as `{{scan_level}}`: "quick" | "deep" | "exhaustive"
- If user presses enter without selecting, use `documentation.default_scan_level` from config, or default to "quick"
- **Announce to user:** "Using {{scan_level}} Scan"
- **Announce to user:** "âœ“ Step 2 Complete: Scan level selected"

### 3. Initialize State File for Resumability

**[[AGENT: Execute this step only after Step 2 is complete]]**

**Announce to user:** "â”â”â” Step 3: Initialize State Tracking â”â”â”"

Create state file at: `{{output_folder}}/project-scan-report.json`

Write initial state:
```json
{
  "workflow_version": "1.2.0-prism",
  "timestamps": {
    "started": "{{current_timestamp}}",
    "last_updated": "{{current_timestamp}}"
  },
  "mode": "{{workflow_mode}}",
  "scan_level": "{{scan_level}}",
  "project_root": "{{project_root_path}}",
  "output_folder": "{{output_folder}}",
  "completed_steps": [],
  "current_step": "step_1",
  "findings": {},
  "outputs_generated": ["project-scan-report.json"],
  "resume_instructions": "Starting from step 1"
}
```

**Announce to user:** "âœ“ Step 3 Complete: State file initialized at {{output_folder}}/project-scan-report.json"

**CRITICAL:** Update this state file after EVERY step completion with:
- Step ID
- Human-readable summary (what was actually done)
- Precise timestamp
- Any outputs written

### 4. Detect Project Structure and Classify Project Type

**[[AGENT: Execute this step only after Step 3 is complete]]**

**Announce to user:** "â”â”â” Step 4: Analyzing Project Structure â”â”â”"

**4.1 Scan Project Root**

Ask user: "What is the root directory of the project to document?" (default: current working directory)

Store as `{{project_root_path}}`

Scan `{{project_root_path}}` for key indicators:
- Directory structure (presence of client/, server/, api/, src/, app/, skills/, etc.)
- Key files (package.json, .prism/, .claude/, commands/, tasks/, etc.)
- Technology markers (Node.js, TypeScript, Python, Go, Ruby, etc.)

**4.2 Detect Project Type**

Based on indicators, classify as one of:
- **claude-code-plugin**: PRISM-style plugins with skills/commands/tasks
- **web**: Web applications (React, Vue, Angular, etc.)
- **mobile**: Mobile apps (React Native, Flutter, etc.)
- **backend**: API servers (Express, FastAPI, Rails, etc.)
- **cli**: Command-line tools
- **library**: Reusable libraries/packages
- **desktop**: Desktop applications (Electron, Tauri, etc.)
- **game**: Game development projects
- **data**: Data pipelines and ETL
- **extension**: Browser extensions
- **infra**: Infrastructure as Code
- **embedded**: Embedded systems

**4.3 Detect Multi-Part Structure**

Check if project has multiple distinct parts (e.g., client/ and server/, or skills/ and commands/):

If multiple parts detected:
```
I detected multiple parts in this project:
{{detected_parts_list}}

Is this correct? Should I document each part separately? [y/n]
```

- If yes: Set `repository_type = "multi-part"` and create entry for each part
- If no: Ask user to specify correct structure

If single cohesive project:
- Set `repository_type = "monolith"`

**4.4 Confirm with User**

Display:
```
I've classified this project:

Type: {{project_type}}
Structure: {{repository_type}}
Parts: {{parts_count}}
{{parts_summary}}

Does this look correct? [y/n/edit]
```

- If no/edit: Allow user to correct classification
- Store final classification in state file
- **Announce to user:** "âœ“ Step 4 Complete: Project classified as {{repository_type}} {{project_type}}"

**4.5 Update State File**

Add to state file:
```json
{
  "completed_steps": [
    {
      "step": "step_4",
      "status": "completed",
      "timestamp": "{{now}}",
      "summary": "Classified as {{repository_type}} {{project_type}} with {{parts_count}} parts"
    }
  ],
  "current_step": "step_5",
  "findings": {
    "project_classification": {
      "repository_type": "{{repository_type}}",
      "project_type": "{{project_type}}",
      "parts_count": {{parts_count}}
    }
  }
}
```

### 5. Comprehensive Project Scanning

**[[AGENT: Execute this step only after Step 4 is complete]]**

**Announce to user:** "â”â”â” Step 5: Scanning Project ({{scan_level}} mode) â”â”â”"

Execute scanning based on `{{scan_level}}` and `{{project_type}}`:

**5.1 For QUICK Scan:**
- Use pattern matching only - do NOT read source files
- Use glob to find files by pattern
- Extract information from filenames, directory structure, and config files
- Identify: Entry points, config files, test patterns, critical directories

**5.2 For DEEP Scan:**
- Read files in critical directories based on project type
- For claude-code-plugin: Read all SKILL.md files, sample tasks, sample commands
- For web: Read key components, API routes, data models
- For backend: Read API endpoints, database models, services
- Apply BATCHING: Process one subfolder at a time, write outputs immediately, purge context

**5.3 For EXHAUSTIVE Scan:**
- Read ALL source files (excluding node_modules, .git, dist, build, coverage)
- Extract complete file inventory with exports, imports, dependencies
- Document all patterns, architectural decisions, code organization
- Apply BATCHING: Process subfolders one at a time to manage token usage

**5.4 Extract Key Information:**

For each part, gather:
- **Technology Stack**: Languages, frameworks, versions, dependencies
- **Architecture Pattern**: MVC, microservices, plugin system, etc.
- **Entry Points**: Main files, initialization code
- **Directory Structure**: Purpose of each major directory
- **Configuration**: Environment variables, config files
- **API Endpoints** (if applicable): Routes, methods, request/response schemas
- **Data Models** (if applicable): Schemas, relationships, validation
- **UI Components** (if applicable): Component inventory, design patterns
- **Testing Strategy**: Test files, frameworks, coverage patterns
- **Build & Deployment**: Scripts, CI/CD, deployment targets

**5.5 Write Documentation Immediately (Write-as-You-Go)**

As you extract information, write documentation files immediately:

1. **project-overview.md** - Executive summary and classification
2. **source-tree-analysis.md** - Annotated directory structure
3. **technology-stack.md** - Complete tech stack with versions
4. **architecture.md** (or per-part) - Detailed architecture documentation
5. **component-inventory.md** (if applicable) - Catalog of major components
6. **development-guide.md** - Local setup and development workflow
7. **api-contracts.md** (if applicable) - API endpoints and schemas
8. **data-models.md** (if applicable) - Database schema and models
9. **deployment-guide.md** (if deployment config found) - Deployment process
10. **integration-architecture.md** (if multi-part) - How parts communicate

**CRITICAL RULES:**
- Write each document to disk IMMEDIATELY after generating content
- Validate document has required sections (no placeholders)
- Update state file with output filename
- PURGE detailed data from context after writing
- Keep only 1-2 sentence summary in context

**5.6 Update State File After Each Document**

After writing each document:
```json
{
  "completed_steps": [
    /* ... previous steps ... */
    {
      "step": "step_5_{{doc_name}}",
      "status": "completed",
      "timestamp": "{{now}}",
      "summary": "{{doc_name}} written with {{section_count}} sections"
    }
  ],
  "outputs_generated": [
    /* ... previous outputs ... */
    "{{doc_name}}.md"
  ]
}
```

### 6. Deep-Dive Mode (if workflow_mode == "deep_dive")

**[[AGENT: Only execute this step if workflow_mode == "deep_dive"]]**

**Announce to user:** "â”â”â” Step 6: Deep-Dive Analysis â”â”â”"

**6.1 Identify Area for Deep-Dive**

Analyze existing documentation to suggest deep-dive options:

Ask user:
```
What area would you like to deep-dive into?

**Suggested Areas Based on Project Structure:**

{{#if has_skills}}
### Skills System ({{skill_count}} skills found)
1. Architect skill - {{file_count}} files in skills/architect/
2. Dev skill - {{file_count}} files in skills/dev/
3. QA skill - {{file_count}} files in skills/qa/
... etc
{{/if}}

{{#if has_agents}}
### Sub-Agent System ({{agent_count}} agents found)
{{#each agent_groups}}
{{agent_index}}. {{agent_name}} - {{file_count}} files in .claude/agents/
{{/each}}
{{/if}}

{{#if has_api_routes}}
### API Routes ({{api_route_count}} endpoints found)
{{#each api_route_groups}}
{{group_index}}. {{group_name}} - {{endpoint_count}} endpoints
{{/each}}
{{/if}}

**Or specify custom:**
- Folder path (e.g., "skills/architect")
- File path (e.g., "tasks/document-project.md")
- Feature name (e.g., "context memory system")

Enter your choice (number or custom path):
```

- Parse user input to determine target
- Store as `{{deep_dive_target}}`
- Confirm with user: "Target: {{target_name}}, Type: {{target_type}}, Path: {{target_path}}, Estimated files: {{file_count}} - Proceed? [y/n]"

**6.2 Exhaustive Scan of Target Area**

Set `scan_mode = "exhaustive"` for deep-dive (override any previous scan level)

For EVERY file in target area:
- Read complete file contents (all lines)
- Extract ALL exports (functions, classes, types, interfaces, constants)
- Extract ALL imports (dependencies)
- Identify purpose from comments and code structure
- Write 1-2 sentences describing behavior, side effects, assumptions
- Extract function signatures with parameter types and return types
- Note any TODOs, FIXMEs, or comments
- Identify patterns (hooks, components, services, etc.)
- Capture contributor guidance: risks, verification steps, suggested tests

**6.3 Build Dependency Graph**

Create dependency graph for scanned area:
- Files as nodes
- Imports as edges
- Identify circular dependencies
- Find entry points (not imported by others)
- Find leaf nodes (don't import others)

**6.4 Find Related Code**

Search codebase OUTSIDE scanned area for:
- Similar file/folder naming patterns
- Similar function signatures
- Similar component structures
- Reusable utilities that could be used

**6.5 Generate Deep-Dive Documentation**

Create: `{{output_folder}}/deep-dive-{{sanitized_target_name}}.md`

Include:
- **Complete File Inventory**: Every file with purpose, exports, imports, patterns
- **Dependency Graph**: Visualization and analysis
- **Data Flow**: How data moves through the system
- **Integration Points**: External dependencies and APIs
- **Testing Analysis**: Test coverage and approach
- **Related Code**: Similar patterns elsewhere in codebase
- **Modification Guidance**: How to add/modify/remove functionality
- **Contributor Checklist**: Risks, verification steps, suggested tests

**6.6 Update Master Index**

Read existing `{{output_folder}}/index.md`

Add deep-dive section if doesn't exist:
```markdown
## Deep-Dive Documentation

Detailed exhaustive analysis of specific areas:

- [{{target_name}} Deep-Dive](./deep-dive-{{sanitized_target_name}}.md) - Comprehensive analysis of {{target_description}} ({{file_count}} files, {{total_loc}} LOC) - Generated {{date}}
```

**6.7 Offer to Continue or Complete**

Ask user:
```
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

## Deep-Dive Documentation Complete! âœ“

**Generated:** {{output_folder}}/deep-dive-{{target_name}}.md
**Files Analyzed:** {{file_count}}
**Lines of Code Scanned:** {{total_loc}}

Would you like to:

1. **Deep-dive another area** - Analyze another feature/module/folder
2. **Finish** - Complete workflow

Your choice [1/2]:
```

- If 1: Clear current target and return to 6.1
- If 2: Continue to Step 7

### 6.5. Check for Existing Documentation (Smart Connections Integration)

**[[AGENT: Execute this step before generating any new documents]]**

**Announce to user:** "â”â”â” Step 6.5: Checking for Existing Documentation â”â”â”"

**Purpose:** Use semantic search to find existing documentation that covers similar topics. **Update existing docs instead of creating duplicates.**

**6.5.1 Check if Smart Connections is Available**

```python
# Check if Smart Connections is enabled
smart_enabled = config.get('smart_connections', {}).get('enabled', False)

if smart_enabled:
    # Try to connect to Smart Connections API
    try:
        response = requests.get('http://localhost:27123/api/status')
        smart_available = response.status_code == 200
    except:
        smart_available = False
else:
    smart_available = False
```

**6.5.2 For Each Document to Generate**

Before creating a new document, check for existing similar content:

```python
def check_existing_documentation(topic: str, description: str) -> Optional[Dict]:
    """
    Query Smart Connections to find existing documentation on this topic.

    Returns:
        None if no similar doc found
        Dict with file path and similarity score if found
    """
    if not smart_available:
        return None

    # Query Smart Connections
    query = f"{topic} {description}"
    response = requests.post('http://localhost:27123/api/search', json={
        'query': query,
        'limit': 5,
        'threshold': 0.7  # High similarity threshold
    })

    if response.status_code == 200:
        results = response.json()['results']
        if results and results[0]['score'] > 0.7:
            return {
                'path': results[0]['path'],
                'score': results[0]['score'],
                'excerpt': results[0]['excerpt']
            }

    return None
```

**6.5.3 Decision Logic for Each Document**

For each document planned in the index:

1. **Query for existing content:**
   ```python
   existing = check_existing_documentation(
       topic="Project Architecture Overview",
       description="High-level system architecture and component relationships"
   )
   ```

2. **If existing document found (similarity > 70%):**

   Ask user:
   ```
   Found existing documentation:

   ðŸ“„ {{existing_path}}
   ðŸŽ¯ Similarity: {{score}}%
   ðŸ“ Excerpt: "{{excerpt}}"

   What would you like to do?

   1. **Update existing** - Merge new information into existing doc
   2. **Create separate** - Create new doc alongside existing
   3. **Skip** - Don't document this topic (use existing as-is)

   Your choice [1/2/3] (default: 1):
   ```

3. **Handle user choice:**

   **If Update (1):**
   - Read existing document
   - Identify new information from current scan
   - Generate merge strategy:
     - New sections to add
     - Existing sections to update
     - Outdated information to remove
   - Create updated version
   - Preserve existing frontmatter and metadata
   - Add update timestamp
   - **Announce:** "âœ… Updated: {{existing_path}}"

   **If Create Separate (2):**
   - Create new document with different focus
   - Add cross-reference to existing doc
   - Add to index with note about relationship
   - **Announce:** "âœ… Created: {{new_path}} (related to {{existing_path}})"

   **If Skip (3):**
   - Mark in index as "See: {{existing_path}}"
   - Don't create duplicate
   - **Announce:** "â­ï¸ Skipped: Using existing {{existing_path}}"

**6.5.4 Track Reuse Statistics**

```python
stats = {
    'documents_planned': 0,
    'documents_updated': 0,
    'documents_created': 0,
    'documents_skipped': 0,
    'duplicate_prevention': 0
}
```

**Announce to user:** "âœ“ Step 6.5 Complete: Checked existing documentation"
**Display:** "ðŸ“Š Reuse: {{updated}} updated, {{created}} created, {{skipped}} skipped"

### 7. Generate Master Index (Primary AI Retrieval Source)

**[[AGENT: Execute this step only after Step 6.5 is complete]]**

**Announce to user:** "â”â”â” Step 7: Generating Master Index â”â”â”"

Create `{{output_folder}}/index.md` as master entry point.

**7.1 Build Index Structure**

For SINGLE-PART projects:
```markdown
# {{project_name}} Documentation Index

**Type:** {{project_type}}
**Primary Language:** {{primary_language}}
**Architecture:** {{architecture_type}}
**Last Updated:** {{date}}

## Project Overview

{{project_description}}

## Quick Reference

- **Tech Stack:** {{tech_stack_summary}}
- **Entry Point:** {{entry_point}}
- **Architecture Pattern:** {{architecture_pattern}}

## Generated Documentation

### Core Documentation

- [Project Overview](./project-overview.md) - Executive summary
- [Source Tree Analysis](./source-tree-analysis.md) - Directory structure
- [Architecture](./architecture.md) - Technical architecture
- [Development Guide](./development-guide.md) - Setup and workflow

{{#if has_api_docs}}- [API Contracts](./api-contracts.md) - API endpoints{{/if}}
{{#if has_data_models}}- [Data Models](./data-models.md) - Database schema{{/if}}
{{#if has_components}}- [Component Inventory](./component-inventory.md) - Component catalog{{/if}}
{{#if has_deployment}}- [Deployment Guide](./deployment-guide.md) - Deployment process{{/if}}

## Getting Started

### Prerequisites

{{prerequisites}}

### Setup

\`\`\`bash
{{setup_commands}}
\`\`\`

### Run Locally

\`\`\`bash
{{run_commands}}
\`\`\`

## For AI-Assisted Development

This documentation enables AI agents to understand and extend this codebase.

**When planning new features:**
- Reference architecture.md for patterns and constraints
- Check component-inventory.md for reusable components
- Review development-guide.md for conventions

---

_Documentation generated by PRISM architect_
```

For MULTI-PART projects, include part-specific sections and integration architecture.

**7.2 Mark Incomplete Documentation**

For any expected document that wasn't generated:
- Add marker: `_(To be generated)_` after the link
- Example: `- [API Contracts](./api-contracts.md) _(To be generated)_`
- This enables detection and completion in validation step

**7.3 Write Index to Disk**

- Write `index.md` immediately
- Validate all links are correct
- Update state file with output
- **Announce to user:** "âœ“ Step 7 Complete: Master index created at {{output_folder}}/index.md"

### 8. Validate and Offer Completion

**[[AGENT: Execute this step only after Step 7 is complete]]**

**Announce to user:** "â”â”â” Step 8: Validation and Completion â”â”â”"

**8.1 Display Summary**

Show user:
```
Documentation generation complete!

**Smart Reuse Statistics:**
ðŸ“Š Documents Planned: {{stats.planned}}
âœ… Existing Updated: {{stats.updated}}
ðŸ†• New Created: {{stats.created}}
â­ï¸ Duplicates Avoided: {{stats.skipped}}
ðŸ“ˆ Reuse Rate: {{(stats.updated + stats.skipped) / stats.planned * 100}}%
```

**8.1.1 Consolidation Opportunities**

If Smart Connections is available, check for consolidation opportunities:

```python
def find_consolidation_opportunities():
    """
    Find documents that cover overlapping topics and could be merged.
    """
    # Get all documents in output folder
    all_docs = glob(f"{output_folder}/**/*.md")

    opportunities = []

    for doc1 in all_docs:
        for doc2 in all_docs:
            if doc1 >= doc2:
                continue

            # Check semantic similarity
            similarity = check_document_similarity(doc1, doc2)

            if similarity > 0.75:  # High overlap
                opportunities.append({
                    'doc1': doc1,
                    'doc2': doc2,
                    'similarity': similarity,
                    'suggested_action': 'merge'
                })

    return opportunities
```

If consolidation opportunities found:

Display:
```
ðŸ” Consolidation Opportunities Found:

1. {{doc1}} <-> {{doc2}} ({{similarity}}% overlap)
   Suggested: Merge into single comprehensive document

2. {{doc3}} <-> {{doc4}} ({{similarity}}% overlap)
   Suggested: Merge and update cross-references

Would you like to consolidate similar documents? [y/n]
```

If yes:
- Merge similar documents
- Preserve all unique information
- Update all references
- Remove redundant files

Show user:
```
Documentation generation complete!

**Summary:**
- Project Type: {{project_type_summary}}
- Parts Documented: {{parts_count}}
- Files Generated: {{files_count}}
- Output Location: {{output_folder}}

**Files Created:**
{{#each generated_files}}
- {{filename}} ({{size}} KB)
{{/each}}
```

**8.2 Detect Incomplete Documentation**

Scan `index.md` for marker: `_(To be generated)_`

If found, extract incomplete items and store in `{{incomplete_docs_list}}`

**8.3 Offer Options**

Ask user:
```
{{#if incomplete_docs_list.length > 0}}
âš ï¸ **Incomplete Documentation Detected:**

I found {{incomplete_docs_list.length}} item(s) marked as incomplete:

{{#each incomplete_docs_list}}
{{@index + 1}}. **{{title}}** ({{doc_type}})
{{/each}}

Would you like to:

1. **Generate incomplete documentation** - Complete any of the items above
2. **Review specific section** [type section name]
3. **Add more detail** [type area name]
4. **Finalize and complete** [type 'done']
{{else}}
Would you like to:

1. **Review specific section** [type section name]
2. **Add more detail** [type area name]
3. **Finalize and complete** [type 'done']
{{/if}}

Your choice:
```

**8.4 Handle User Selection**

- If **Generate incomplete**: Go to Step 9
- If **Review/Add detail**: Execute requested refinement
- If **Done**: Go to Step 10

### 9. Generate Incomplete Documentation (if requested)

**[[AGENT: Only execute this step if user requested it in Step 8]]**

**Announce to user:** "â”â”â” Step 9: Generating Incomplete Documentation â”â”â”"

**9.1 Present Incomplete Items**

Ask user:
```
Which incomplete items would you like to generate?

{{#each incomplete_docs_list}}
{{@index + 1}}. {{title}} ({{doc_type}})
{{/each}}
{{incomplete_docs_list.length + 1}}. All of them

Enter number(s) separated by commas (e.g., "1,3,5"), or type 'all':
```

**9.2 Generate Selected Items**

For each selected item:
1. Identify the part and requirements
2. Route to appropriate generation logic based on doc_type:
   - **architecture**: Re-run architecture generation for that part
   - **api-contracts**: Re-run API scan for that part
   - **data-models**: Re-run data models scan for that part
   - **component-inventory**: Re-run component inventory for that part
   - **development-guide**: Re-run dev guide generation for that part
3. Write document to disk immediately
4. Update state file with newly generated output
5. Display: "âœ“ Generated: {{file_path}}"

**9.3 Update Index to Remove Markers**

- Read current index.md
- For each newly generated document, remove the `_(To be generated)_` marker
- Write updated index back to disk

**9.4 Display Generation Summary**

```
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

âœ“ **Documentation Generation Complete!**

**Successfully Generated:**
{{#each newly_generated_docs}}
- {{title}} â†’ {{file_path}}
{{/each}}

**Documentation is now ready for AI-assisted development!**
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
```

### 10. Finalize and Complete

**[[AGENT: Execute this step as the final step]]**

**Announce to user:** "â”â”â” Step 10: Finalizing Documentation â”â”â”"

**10.1 Update State File as Complete**

Update state file:
```json
{
  "timestamps": {
    "started": "{{start_timestamp}}",
    "last_updated": "{{now}}",
    "completed": "{{now}}"
  },
  "completed_steps": [
    /* ... all steps ... */
    {
      "step": "step_10",
      "status": "completed",
      "timestamp": "{{now}}",
      "summary": "Workflow completed successfully"
    }
  ],
  "current_step": "completed"
}
```

**10.2 Display Final Message**

```
ðŸŽ‰ **Document Project Task Complete!**

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

**Documentation Location:** {{output_folder}}/

**Master Index:** {{output_folder}}/index.md

**Documentation Efficiency:**
- ðŸ“Š Documents Planned: {{stats.planned}}
- âœ… Existing Updated: {{stats.updated}} (reused existing knowledge)
- ðŸ†• New Created: {{stats.created}} (net new documentation)
- â­ï¸ Duplicates Avoided: {{stats.skipped}} (prevented redundancy)
- ðŸ”„ Consolidations: {{consolidation_count}} (merged similar docs)
- **Total Files:** {{total_files_count}} (vs {{stats.planned}} planned)
- **Efficiency Rate:** {{((stats.updated + stats.skipped) / stats.planned * 100)}}%

**Generated Files Breakdown:**
- Core Documentation: {{core_docs_count}} files
{{#if deep_dive_count > 0}}- Deep-Dive Analysis: {{deep_dive_count}} files{{/if}}

**Project Analysis:**
- Type: {{project_type}}
- Structure: {{repository_type}}
- Scan Level: {{scan_level}}
- Parts Documented: {{parts_count}}

**Next Steps:**

âœ… Documentation is ready for:
- AI-assisted PRD creation
- Architecture review and planning
- Team onboarding and knowledge transfer
- Feature planning and estimation

ðŸ“– Start here: {{output_folder}}/index.md

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

Thank you for using the PRISM architect!
```

**10.3 Archive State File**

- Move state file to: `{{output_folder}}/.archive/project-scan-report-{{timestamp}}.json`
- This keeps output folder clean while preserving scan history

---

## Implementation Notes

### Token Management Strategy

This task implements **write-as-you-go** architecture to manage token usage:

1. **Immediate Writing**: Write each document to disk as soon as content is generated
2. **Context Purging**: After writing, purge detailed data from context
3. **Summary Retention**: Keep only 1-2 sentence summaries in context
4. **Batching**: For deep/exhaustive scans, process one subfolder at a time
5. **State Tracking**: Use state file to track progress, not in-memory context

### Resumability

The state file enables resumption if task is interrupted:
- State file checked at task start
- If recent (<24 hours), offer to resume
- Resume loads cached classification and summaries
- Resume skips completed steps and continues from last checkpoint

## References

- PRISM Architecture: `.prism/docs/architecture.md`
- Task Template: `.prism/templates/task-template.md`

