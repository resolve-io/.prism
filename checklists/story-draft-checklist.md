<!-- Powered by PRISM™ Core -->

# Story Draft Checklist

## Purpose
Validate that a draft story is complete, estimable, and ready for development.

## Required Artifacts
- Story file: {story}.{story}.*.md
- Story definition (if available)
- Architecture documents (referenced sections)
- PRD (if applicable)

## Validation Sections

### 1. Story Structure & Clarity

- [ ] Story follows "As a... I want... So that..." format
- [ ] Role is clearly defined and valid
- [ ] Action is specific and implementable  
- [ ] Benefit/value is clear and measurable
- [ ] Story title is descriptive and concise
- [ ] Status is set to "Draft" or "Approved"

### 2. Acceptance Criteria

- [ ] At least 3 acceptance criteria defined
- [ ] Each AC is specific and testable
- [ ] ACs cover happy path scenarios
- [ ] ACs include error/edge cases where applicable
- [ ] ACs are numbered for reference
- [ ] Success conditions are measurable

### 3. Tasks and Subtasks

- [ ] Story broken into specific tasks
- [ ] Each task references relevant ACs (where applicable)
- [ ] Subtasks provide implementation detail
- [ ] Tasks are sequenced logically
- [ ] Dependencies between tasks noted
- [ ] All tasks have checkbox format [ ]

### 4. PSP/TSP Estimation

- [ ] Story points assigned (1,2,3,5,8)
- [ ] Size category mapped (VS,S,M,L,VL)
- [ ] PROBE estimation completed
- [ ] Similar stories identified as proxies
- [ ] Hour estimates provided (O/L/P)
- [ ] Confidence level stated
- [ ] Estimation date recorded
- [ ] Tracking fields initialized (null)

### 5. Technical Context

- [ ] Dev Notes section populated
- [ ] Relevant architecture referenced
- [ ] Data models identified (if applicable)
- [ ] API specifications included (if applicable)
- [ ] File locations specified
- [ ] Testing standards documented
- [ ] All technical details cite sources

### 6. Dependencies & Risks

- [ ] External dependencies identified
- [ ] Blocking stories noted
- [ ] Technical risks documented
- [ ] Resource needs specified
- [ ] Timeline constraints noted

### 7. Testing Requirements

- [ ] Test approach defined
- [ ] Test file locations specified
- [ ] Coverage requirements stated
- [ ] Test data needs identified
- [ ] Integration points noted

### 8. Team Readiness

- [ ] Story is self-contained for dev agent
- [ ] No need to read extensive external docs
- [ ] Clear enough for automated implementation
- [ ] Questions/ambiguities resolved
- [ ] Ready for sprint planning

## Scoring

Each section worth 10 points:
- All items checked: 10 points
- 1-2 items missing: 7 points  
- 3+ items missing: 3 points
- Section not applicable: Exclude from total

**Passing Score: 75%**

## Common Issues to Flag

**Critical (Must Fix):**
- Missing acceptance criteria
- No estimation data
- Ambiguous requirements
- Missing technical context

**Major (Should Fix):**
- Incomplete task breakdown
- Missing test requirements
- No risk assessment
- Unclear dependencies

**Minor (Could Improve):**
- Could use more detail
- Additional examples helpful
- More specific file paths
- Enhanced error scenarios

## Output Format

```markdown
Story Draft Validation: {story}.{story}
Status: PASS | CONDITIONAL | FAIL
Score: X/Y (Z%)

Critical Issues:
- [Issue if any]

Recommendations:
- [Specific improvements]

Ready for Sprint: YES | NO
```