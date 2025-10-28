# Sub-Agent Quick Reference
**One-Page Cheat Sheet**

## When Sub-Agents Run

| Role | Command | Phase | Sub-Agent | What It Checks |
|------|---------|-------|-----------|----------------|
| **SM** | `*draft` | 2 | story-structure-validator | 9 sections, YAML, checkboxes |
| **SM** | `*draft` | 2 | story-content-validator | AC quality, task sizing (0-100 score) |
| **SM** | `*draft` | 2 | epic-alignment-checker | Scope creep, requirement coverage |
| **SM** | `*draft` | 2 | architecture-compliance-checker | Tech stack, patterns, boundaries |
| **SM** | `*decompose` | 2 | epic-analyzer | Story suggestions, sizing, dependencies |
| **Dev** | `*develop-story` | 2 | lint-checker | ESLint, Pylint, formatting (after each task) |
| **Dev** | `*develop-story` | 3 | file-list-auditor | File List vs git changes |
| **Dev** | `*develop-story` | 3 | test-runner | Jest, pytest, RSpec, coverage % |
| **QA** | `*review` | 2 | requirements-tracer | PRD→Epic→Story→Code→Tests |
| **QA** | `*review` | 4 | qa-gate-manager | PASS/CONCERNS/FAIL/WAIVED gate |

## Time Savings Per Story

| Phase | Before | After | Savings |
|-------|--------|-------|---------|
| SM Validation | ~10 min | ~2 min | **8 min** |
| SM Architecture Check | ~15 min | ~30 sec | **14.5 min** |
| Dev Lint Fixes | ~20 min | ~5 min | **15 min** |
| Dev File List | ~5 min | ~10 sec | **4.9 min** |
| QA Requirements Trace | ~30 min | ~2 min | **28 min** |
| QA Gate Creation | ~15 min | ~1 min | **14 min** |
| **Total** | **~95 min** | **~17 min** | **~78 min (1.3 hrs)** |

## Common Issues & Quick Fixes

### Structure Validator Fails

**Issue**: "Missing section: ## Testing"
```markdown
❌ Wrong: # Testing
✅ Right: ## Testing
```

**Issue**: "YAML field missing: sizing"
```yaml
❌ Wrong: (frontmatter missing sizing)
✅ Right:
sizing:
  points: 3
  category: S
  confidence: medium
```

---

### Content Validator Score Low

| Score | Fix |
|-------|-----|
| <70 | Add measurable criteria (numbers, %, time limits) |
| 70-79 | Break oversized tasks (<4 hours each) |
| 80-89 | Add test scenarios, clarify dev notes |
| 90+ | Great! Proceed |

**Example Fixes**:
```markdown
❌ "Should be fast"
✅ "Should complete within 2 seconds"

❌ "Implement entire system (8 hours)"
✅ "Implement service layer (2 hours)" + "Implement UI (2 hours)"
```

---

### Epic Alignment Scope Creep

**Issue**: "Feature not in epic"

**Fix**: Remove OR create separate story
```markdown
❌ Adding social sharing (not in epic)
✅ Remove from story, create STORY-124 for social features
```

---

### Architecture Violation

**Issue**: "Technology not approved: MongoDB"

**Fix**: Check `docs/architecture/tech-stack.md`
```markdown
❌ Use MongoDB
✅ Use PostgreSQL (approved)
```

**Issue**: "Direct database access in controller"

**Fix**: Check `docs/architecture/patterns.md`
```markdown
❌ Controller → Database
✅ Controller → Service → Repository → Database
```

---

### Lint Errors

**Quick Fix**:
```bash
# Auto-fix 80% of issues
npm run lint:fix

# Then fix remaining manually
eslint src/file.ts --fix
```

**Common Issues**:
- Unused variables: Remove or prefix with `_`
- Missing semicolons: Add or use Prettier
- Import order: Use `eslint-plugin-import`

---

### File List Mismatch

**Quick Fix**: Use corrected_list from auditor output

**Command**:
```bash
# See what git thinks changed
git diff --name-only main..HEAD
```

---

### Test Failures

**Quick Fix**:
```bash
# Run failing test in isolation
npm test -- ProfileService.test.ts

# Check for environment issues
# - Environment variables
# - Database state
# - Hardcoded paths/timestamps
```

**Coverage Too Low**:
- Add unit tests for new functions
- Add integration tests for API endpoints
- Add E2E tests for user workflows
- Target: 80%+ coverage

---

### Traceability Gaps

**Issue**: "AC-003 not implemented"

**Fix**: Implement the missing acceptance criterion

**Issue**: "AC-005 has no tests"

**Fix**: Add tests that verify AC-005

**Issue**: "Orphaned file: utils/old-helper.ts"

**Fix**: Remove unused files OR document why they're needed

---

### Gate Status FAIL

**Criteria for FAIL**:
- Critical issues present
- Coverage <70%
- Missing requirements implementation

**Fix Priority**:
1. Critical issues FIRST (security, data loss, crashes)
2. High issues (major functionality gaps)
3. Coverage (add tests to reach 80%+)
4. Medium/Low issues (if time permits)

**Waiver Option**:
- Requires PO approval
- Must have mitigation plan
- Documented in gate file

---

## Sub-Agent Output Interpretation

### Structure Validator
```json
{"valid": true/false, "checks": {...}, "issues": [...]}
```
- `valid: false` = Must fix before proceeding
- Check `issues` array for specific problems

### Content Validator
```json
{"score": 0-100, "checks": {...}}
```
- Score <70: Significant issues
- Score 70-79: Address concerns
- Score 80-89: Minor improvements
- Score 90+: Excellent

### Epic Alignment
```json
{"aligned": true/false, "coverage": 0-100, "scope_creep": [...]}
```
- `aligned: false` = Scope creep detected
- Check `scope_creep` array

### Architecture Compliance
```json
{"compliant": true/false, "violations": [...]}
```
- `critical` severity = Must fix
- `high` severity = Should fix
- Check `docs/architecture/` for standards

### Lint Checker
```json
{"passed": true/false, "auto_fixable": N}
```
- Run `lint:fix` for auto-fixable
- Manually fix remaining

### File List Auditor
```json
{"accurate": true/false, "corrected_list": [...]}
```
- Use `corrected_list` to update story

### Test Runner
```json
{"passed": true/false, "coverage": {...}}
```
- Fix failures first
- Then improve coverage to 80%+

### Requirements Tracer
```json
{"traceability_status": "COMPLETE|GAPS|MISSING", "coverage_percentage": 0-100}
```
- COMPLETE = 100% traced
- GAPS = Some missing
- MISSING = Major gaps

### QA Gate Manager
```yaml
status: PASS|CONCERNS|FAIL|WAIVED
```
- PASS = Deploy
- CONCERNS = Deploy with docs
- FAIL = Must fix
- WAIVED = Proceed with approval

---

## Best Practices Checklist

### Story Masters (SM)
- [ ] Review validation feedback immediately
- [ ] Aim for content score 85+
- [ ] No scope creep (stick to epic)
- [ ] Use only approved technologies
- [ ] Fix issues before passing to Dev

### Developers (Dev)
- [ ] Run lint after each task
- [ ] Update File List as you code
- [ ] Run tests frequently
- [ ] Fix failures immediately
- [ ] Aim for 80%+ coverage

### QA Engineers (QA)
- [ ] Review traceability carefully
- [ ] Understand gate criteria
- [ ] Document waivers clearly
- [ ] Provide actionable feedback
- [ ] Use CONCERNS for minor issues only

---

## Emergency Contacts

**Sub-Agent Issues**:
1. Check this quick reference
2. See [Sub-Agent User Guide](sub-agent-user-guide.md)
3. Review specific sub-agent file in `.claude/agents/`
4. Consult with team

**Feedback**:
- False positives/negatives
- Confusing error messages
- Missing validations
- Report to improve sub-agents!

---

**Version**: 1.0.0
**Last Updated**: 2025-10-27
**Full Guide**: [sub-agent-user-guide.md](sub-agent-user-guide.md)
**Playbook**: [sub-agent-implementation-playbook.md](sub-agent-implementation-playbook.md)
