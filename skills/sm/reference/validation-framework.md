# Automatic Story Validation

As of Phase 3.2, the SM command includes **automatic sub-agent validation** during story creation and epic decomposition.

## How It Works

When you create or decompose stories, **validation happens immediately** before the story is finalized. You'll see validation results for each story and can fix issues before proceeding.

## The 4 Validators

Every story passes through 4 quality checks:

1. **story-structure-validator** (runs first, uses Haiku for speed)
   - Checks all required sections are present
   - Verifies YAML frontmatter syntax
   - Validates checkbox format
   - Ensures status field has valid value

2. **story-content-validator** (runs after structure passes)
   - Verifies acceptance criteria are measurable
   - Checks tasks are properly sized (1-3 days each)
   - Validates Dev Notes provide clear guidance
   - Ensures Testing section has scenarios
   - Assigns quality score (0-100)

3. **epic-alignment-checker** (runs after content validation)
   - Maps story requirements to parent epic
   - Detects scope creep
   - Verifies no missing requirements
   - Checks dependencies and sequencing

4. **architecture-compliance-checker** (runs last)
   - Validates technology stack compliance
   - Checks design pattern usage
   - Ensures system boundaries respected
   - Verifies non-functional requirements
   - Validates integration points

## Validation Workflow

**During `*draft` command**:
1. Story Creation
2. Immediate Validation (4 validators)
3. Quality Decision (pass/fix/proceed)
4. Completion

**During `*decompose` command**:
1. Epic Analysis
2. Epic Understanding (delegated)
3. Story Creation Loop (create + validate each)
4. Epic Coverage Verification
5. Completion

## Common Issues and Fixes

| Issue | Validator | Fix |
|-------|-----------|-----|
| Missing sections | Structure | Add required sections |
| Vague criteria | Content | Make measurable |
| Tasks too large | Content | Break into chunks |
| Scope creep | Epic Alignment | Remove or update epic |
| Wrong technology | Architecture | Use approved stack |
| Missing NFRs | Architecture | Add requirements |

## Benefits

- Catch issues early
- Consistent quality
- Save time
- Better estimates
- Architecture compliance
