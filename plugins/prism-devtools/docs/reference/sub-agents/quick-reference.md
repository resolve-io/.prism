# Sub-Agent Quick Reference

One-page cheat sheet for PRISM's 10 validation sub-agents.

## Quick Navigation

- [When Sub-Agents Run](#when-sub-agents-run)
- [All Sub-Agents at a Glance](#all-sub-agents-at-a-glance)
- [Output Format](#output-format)
- [Common Issues & Quick Fixes](#common-issues--quick-fixes)
- [Best Practices Checklist](#best-practices-checklist)

---

## When Sub-Agents Run

| Role | Command | Phase | Sub-Agents | Purpose |
|------|---------|-------|------------|---------|
| **SM** | `/sm *draft` | Story Creation | structure → content → epic-align → arch-comply | Validate story structure and quality |
| **SM** | `/sm *decompose` | Epic Breakdown | epic-analyzer | Suggest story decomposition |
| **Dev** | `/dev *develop-story` | Pre-Review | file-list → test-runner → lint-checker | Verify implementation quality |
| **QA** | `/qa *review` | Review | requirements-tracer → qa-gate-manager | Trace requirements, create gate |

---

## All Sub-Agents at a Glance

### Story Master (SM) - 5 Validators

| # | Name | Model | Purpose | Output |
|---|------|-------|---------|--------|
| 1 | **story-structure-validator** | Haiku | Check 9 required sections | valid (bool), issues (list) |
| 2 | **story-content-validator** | Sonnet | Validate AC/tasks/sizing | quality_score (0-100), checks (obj) |
| 3 | **epic-alignment-checker** | Sonnet | Detect scope creep | aligned (bool), gaps (list) |
| 4 | **architecture-compliance-checker** | Sonnet | Verify tech/patterns | compliant (bool), violations (list) |
| 5 | **epic-analyzer** | Sonnet | Suggest decomposition | stories (list), dependencies (graph) |

### Developer (Dev) - 3 Validators

| # | Name | Model | Purpose | Output |
|---|------|-------|---------|--------|
| 6 | **file-list-auditor** | Haiku | Match File List to git | status (MATCH/DISCREPANCY), missing (list) |
| 7 | **test-runner** | Haiku | Execute test suite | passed (int), failed (int), framework (str) |
| 8 | **lint-checker** | Haiku | Run linters/formatters | violations (int), files (list), linter (str) |

### QA - 2 Validators

| # | Name | Model | Purpose | Output |
|---|------|-------|---------|--------|
| 9 | **requirements-tracer** | Sonnet | Trace PRD→Epic→Story→Code→Tests | coverage (%), untested_acs (list), orphaned (list) |
| 10 | **qa-gate-manager** | Sonnet | Create gate YAML | gate_id (str), status (PASS/CONCERNS/FAIL/WAIVED) |

---

## Output Format

All sub-agents return **structured JSON**:

```json
{
  "valid": true|false,                    // Pass/fail
  "story_path": "docs/stories/...",      // File validated
  "checks": { ... },                      // Detailed checks
  "issues": ["..."],                      // Problems found
  "recommendation": "ACTION_REQUIRED"     // Next steps
}
```

### Special Fields

| Sub-Agent | Special Field | Values |
|-----------|---------------|--------|
| story-content-validator | `quality_score` | 0-100 |
| file-list-auditor | `status` | MATCH / DISCREPANCY |
| test-runner | `passed`, `failed` | Integer counts |
| lint-checker | `violations` | Integer count |
| requirements-tracer | `coverage` | Percentage |
| qa-gate-manager | `status` | PASS / CONCERNS / FAIL / WAIVED |

---

## Common Issues & Quick Fixes

### SM: story-structure-validator

| Issue | Quick Fix |
|-------|-----------|
| Missing '## Testing' section | Add `## Testing` heading with test scenarios |
| Checkboxes not `- [ ]` format | Change `*` or `-` to `- [ ]` |
| Invalid Status value | Use: Draft / Approved / InProgress / Review / Done |
| Missing As a/I want/So that | Rewrite story statement with user story template |

### SM: story-content-validator

| Issue | Quick Fix |
|-------|-----------|
| AC not measurable | Avoid "properly", "correctly" - use specific outcomes |
| Tasks too large (>3 days) | Split into smaller sub-tasks (1-3 days each) |
| Dev Notes too vague | Add architecture references, patterns, challenges |
| Testing section placeholder | Write actual test scenarios and edge cases |
| Quality score <70 | Address all CONCERNS/FAIL checks |

### SM: epic-alignment-checker

| Issue | Quick Fix |
|-------|-----------|
| Scope creep detected | Remove ACs outside epic scope OR update epic first |
| AC doesn't map to epic | Add missing requirement to epic OR remove from story |
| Missing epic reference | Add epic number to story frontmatter or path |

### SM: architecture-compliance-checker

| Issue | Quick Fix |
|-------|-----------|
| Unapproved technology | Use approved alternatives from tech-stack.md |
| Pattern violation | Follow architecture patterns (no direct DB access in controller) |
| Boundary violation | Respect module/service boundaries |

### Dev: file-list-auditor

| Issue | Quick Fix |
|-------|-----------|
| Files missing from list | Add to File List: src/utils/helper.ts |
| Extra files in list | Remove deleted files from File List |
| Test files not listed | Include test files in File List |

### Dev: test-runner

| Issue | Quick Fix |
|-------|-----------|
| 3 tests failing | Fix failing tests before marking Review |
| No tests found | Add test files, configure test command |
| Wrong test framework detected | Configure correct command in core-config.yaml |

### Dev: lint-checker

| Issue | Quick Fix |
|-------|-----------|
| ESLint: 12 violations | Run `npm run lint:fix` or fix manually |
| Formatting inconsistent | Run `npm run format` (Prettier, Black, etc.) |
| No linter configured | Add linter to project (ESLint, Pylint, RuboCop) |

### QA: requirements-tracer

| Issue | Quick Fix |
|-------|-----------|
| AC 'Fast load time' not traced | Add performance test OR mark as NFR |
| Missing test for utils.ts | Add test file: utils.test.ts |
| Orphaned code detected | Remove unused files OR document reason |
| Coverage <70% | Add tests for untested code paths |

### QA: qa-gate-manager

| Issue | Quick Fix |
|-------|-----------|
| Status: FAIL | Address critical issues before proceeding |
| Status: CONCERNS | Document concerns, track for future sprint |
| Missing gate file | Check docs/qa/gates/ directory exists |

---

## Best Practices Checklist

### Story Master (SM)

- [ ] Use story template with all 9 sections
- [ ] Write measurable ACs (3-7 criteria)
- [ ] Size tasks appropriately (1-3 days each)
- [ ] Reference architecture in Dev Notes
- [ ] Include specific test scenarios
- [ ] Aim for quality score 85+
- [ ] Verify epic alignment before approving
- [ ] Check tech stack compliance

### Developer (Dev)

- [ ] Update File List as you develop
- [ ] Run tests frequently, fix failures immediately
- [ ] Address linting violations during development
- [ ] Follow story's Dev Notes guidance
- [ ] Implement all Testing section scenarios
- [ ] Mark task checkboxes as you complete
- [ ] Update Change Log with each commit
- [ ] Never mark "Review" with failing validators

### QA Reviewer

- [ ] Verify PRD → Epic → Story → Code → Tests chain
- [ ] Check test quality, not just coverage
- [ ] Validate edge case handling
- [ ] Review non-functional requirements
- [ ] Document findings in structured format
- [ ] Follow gate status logic objectively
- [ ] Create gate YAML file with clear recommendation
- [ ] Track concerns for future improvement

---

## Validator Sequence

### SM Story Creation

```
1. story-structure-validator  [Haiku]   → 9 sections present?
   ↓ (if valid)
2. story-content-validator     [Sonnet]  → Quality score 0-100
   ↓ (if score ≥70)
3. epic-alignment-checker      [Sonnet]  → Maps to epic?
   ↓ (if aligned)
4. architecture-compliance     [Sonnet]  → Approved tech?
   ↓ (if compliant)
✅ STORY APPROVED
```

### Dev Implementation

```
1. [Developer implements code]
   ↓
2. file-list-auditor          [Haiku]   → File List accurate?
   ↓ (if MATCH)
3. test-runner                [Haiku]   → Tests pass?
   ↓ (if passed>0, failed=0)
4. lint-checker               [Haiku]   → Code style OK?
   ↓ (if violations=0)
✅ READY FOR REVIEW
```

### QA Review

```
1. [QA analyzes implementation]
   ↓
2. requirements-tracer        [Sonnet]  → Full traceability?
   ↓ (coverage calculated)
3. qa-gate-manager            [Sonnet]  → Gate status?
   ↓
✅ GATE FILE CREATED (PASS/CONCERNS/FAIL/WAIVED)
```

---

## Time Savings

| Phase | Before Sub-Agents | With Sub-Agents | Savings |
|-------|-------------------|-----------------|---------|
| Story creation | 45min | 19min | **-58%** |
| Dev validation | 20min | 5min | **-75%** |
| QA review | 60min | 15min | **-75%** |
| **Total per story** | **125min** | **39min** | **~1.3 hours** |

## Quality Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Story rework rate | 15-20% | <5% | **-75%** |
| Requirements traceability | 60-70% | 95%+ | **+35 pts** |
| Test coverage | Varies | 80%+ | Consistent |
| Architecture compliance | Manual | 100% | Automated |

---

## File Locations

| Sub-Agent | Path |
|-----------|------|
| All 10 agents | `.claude/agents/*.md` |
| SM commands | `commands/sm.md` |
| Dev commands | `commands/dev.md` |
| QA commands | `commands/qa.md` |
| Gate files | `docs/qa/gates/*.yml` |

---

## Quick Commands

```bash
# View sub-agent definition
cat .claude/agents/story-structure-validator.md

# List all sub-agents
ls .claude/agents/

# Check git changes for file-list-auditor
git diff --name-only main..HEAD

# Run tests manually (what test-runner does)
npm test         # JavaScript
pytest           # Python
rspec            # Ruby
go test ./...    # Go

# Run linter manually (what lint-checker does)
npm run lint     # JavaScript
pylint src/      # Python
rubocop          # Ruby
golint ./...     # Go
```

---

## Decision Matrix

| Situation | Best Action |
|-----------|-------------|
| Story structure invalid | Fix required sections, re-run SM |
| Quality score 60-69 | Address FAIL checks, aim for 70+ |
| Quality score <60 | Major revision needed, start over |
| Scope creep detected | Update epic OR remove ACs |
| File List mismatch | Update to match git changes |
| Tests failing | Fix tests before marking Review |
| Linting violations | Run lint:fix, address manually |
| Coverage <70% | Add tests for untested paths |
| Gate status: FAIL | Fix critical issues before merging |
| Gate status: CONCERNS | Document, track for future work |

---

## Resources

- **Detailed Guide:** [Sub-Agent User Guide](./user-guide.md)
- **Architecture:** [Implementation](./implementation/)
- **Workflows:** [Core Development Cycle](../workflows/core-development-cycle.md)
- **Hooks:** [Hooks Documentation](../../../hooks/README.md)
- **Claude Code:** [Architecture Overview](../guides/claude-code-overview.md)

---

**Last Updated:** 2026-02-06
**PRISM Version:** 2.2.0
