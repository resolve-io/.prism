# PRISM Workflow Hooks

Python-based Claude Code hooks that enforce story file updates throughout the core-development lifecycle workflow.

## Overview

These hooks ensure:
1. **Story Context is Established**: All workflow commands work on the correct story file
2. **Story Files are Updated**: Required sections are present based on workflow phase
3. **Workflow Integrity**: Steps execute in proper order with proper validation

## Hook Files

### Python Scripts

| Hook | Type | Purpose | Blocks? |
|------|------|---------|---------|
| `enforce-story-context.py` | PreToolUse | Ensure workflow commands have active story | ✅ Yes |
| `track-current-story.py` | PostToolUse | Capture story file as current context | ❌ No |
| `validate-story-updates.py` | PostToolUse | Validate story file updates | ❌ No (warns) |
| `validate-required-sections.py` | PostToolUse | Verify all required PRISM sections | ✅ Yes (critical errors) |

### Configuration

`hooks.json` - Hook event configuration for Claude Code

## How It Works

### Story Context Flow

```
1. *draft command creates story in docs/stories/
   ↓
2. track-current-story.py captures path → .prism-current-story.txt
   ↓
3. All workflow commands check enforce-story-context.py
   ↓
4. Commands blocked if no active story ❌
   OR
5. Commands proceed with story context ✅
```

### Validation Flow

```
Story file Edit/Write
   ↓
validate-story-updates.py
   - Warns if editing non-current story
   - Checks for required base sections
   ↓
validate-required-sections.py
   - Comprehensive section validation
   - Blocks if critical sections missing
```

## Generated Files

### `.prism-current-story.txt`
Contains the path to the currently active story file.

**Example**: `docs/stories/platform-1.auth-improvements-2.md`

**Created by**: `track-current-story.py`

### `.prism-workflow.log`
Audit log of all workflow events.

**Format**: `TIMESTAMP | EVENT_TYPE | DETAILS`

**Example**:
```
2025-10-24T15:30:45Z | STORY_ACTIVE | docs/stories/epic-1.story-2.md
2025-10-24T15:31:12Z | COMMAND | develop-story | docs/stories/epic-1.story-2.md
2025-10-24T15:32:08Z | STORY_UPDATED | docs/stories/epic-1.story-2.md
2025-10-24T15:32:09Z | VALIDATION | PASS | docs/stories/epic-1.story-2.md | In Progress
```

## Workflow Integration

### Core Development Cycle Steps

1. **draft_story** (`*draft`)
   - Creates story file in `docs/stories/`
   - **Hook**: `track-current-story.py` captures file path
   - **Result**: Story context established

2. **risk_assessment** (`*risk {story}`)
   - **Hook**: `enforce-story-context.py` verifies story exists

3. **test_design** (`*design {story}`)
   - **Hook**: `enforce-story-context.py` verifies story exists

4. **validate_story** (`*validate-story-draft {story}`)
   - **Hook**: `enforce-story-context.py` verifies story exists

5. **implement_tasks** (`*develop-story`)
   - **Hook**: `enforce-story-context.py` verifies story exists
   - **Hook**: `validate-story-updates.py` validates Dev Agent Record
   - **Hook**: `validate-required-sections.py` ensures required sections

6. **qa_review** (`*review {story}`)
   - **Hook**: `enforce-story-context.py` verifies story exists
   - **Hook**: `validate-story-updates.py` validates QA Results section

7. **address_review_issues** (`*review-qa`)
   - **Hook**: `enforce-story-context.py` verifies story exists

8. **update_gate** (`*gate {story}`)
   - **Hook**: `enforce-story-context.py` verifies story exists

## Error Messages

### No Active Story

```
❌ ERROR: Command 'develop-story' requires an active story

   No current story found in workflow context

   REQUIRED: Draft a story first using the core-development-cycle workflow:
     1. Run: *planning-review (optional)
     2. Run: *draft

   The draft command will create a story file and establish story context.
```

### Missing Required Sections

```
❌ VALIDATION FAILED: Story file has critical errors

   ERROR: Missing required section for In Progress status: ## Dev Agent Record

   Story file: docs/stories/epic-1.story-2.md
   Status: In Progress

   REQUIRED: Fix these errors before proceeding with workflow
```

## Dependencies

- **Python 3.6+**: All hooks are Python scripts
- **json**: Standard library (built-in)
- **pathlib**: Standard library (built-in)
- **re**: Standard library (built-in)

No external packages required!

## Installation

The hooks are automatically loaded by Claude Code from the `hooks/` directory when the plugin is installed.

## Troubleshooting

### Hook Not Running

**Check**:
1. `hooks.json` is valid JSON
2. Python 3 is in PATH: `python --version`
3. Matcher pattern matches tool being used

### Hook Blocking Unexpectedly

**Debug**:
1. Check `.prism-workflow.log` for error messages
2. Run hook manually:
   ```bash
   echo '{"tool_input":{"command":"*develop-story"}}' | python hooks/enforce-story-context.py
   ```
3. Check if `.prism-current-story.txt` exists and contains valid path

### Story Context Lost

**Fix**:
1. Verify story file exists in `docs/stories/`
2. Manually set current story:
   ```bash
   echo "docs/stories/your-story.md" > .prism-current-story.txt
   ```
3. Or run `*draft` to create new story

## Version

**PRISM Hook System Version**: 1.0.0

**Compatible with**:
- PRISM Core Development Cycle: v1.3.0+
- Claude Code: Latest (hooks feature released June 2025)

## Support

For issues or questions:
1. Check `.prism-workflow.log` for detailed event history
2. Review hook output in Claude Code console
3. File issue at PRISM repository

---

**Last Updated**: 2025-10-24
