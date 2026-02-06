# Context Loading Plan

Use this template to plan file reads before starting implementation.

## Project Information

| Field | Value |
|-------|-------|
| **Repository** | `{repo_path}` |
| **Project Type** | `{project_type}` |
| **Story** | `{story_reference}` |
| **Date** | `{date}` |

---

## Phase 1: Configuration

Files to load first for standards and patterns.

| File | Purpose | Status |
|------|---------|--------|
| `core-config.yaml` | PRISM configuration, devLoadAlwaysFiles | [ ] |
| `{devLoadAlwaysFiles[0]}` | {purpose} | [ ] |
| `{devLoadAlwaysFiles[1]}` | {purpose} | [ ] |
| `{devLoadAlwaysFiles[2]}` | {purpose} | [ ] |

---

## Phase 2: Architecture

Design documentation to understand before coding.

| File | Purpose | Status |
|------|---------|--------|
| `docs/architecture/coding-standards.md` | Code style and patterns | [ ] |
| `docs/architecture/tech-stack.md` | Technologies and frameworks | [ ] |
| `docs/architecture/source-tree.md` | Directory structure | [ ] |
| `{additional_arch_file}` | {purpose} | [ ] |

---

## Phase 3: Story Context

The single source of truth for this task.

| File | Purpose | Status |
|------|---------|--------|
| `{story_file_path}` | Current story requirements | [ ] |
| `{epic_file_path}` | Parent epic context | [ ] |

---

## Phase 4: Code Files

Files to read based on story File List and discoveries.

### From Story File List

| File | Purpose | Status |
|------|---------|--------|
| `{file_list_item_1}` | {purpose} | [ ] |
| `{file_list_item_2}` | {purpose} | [ ] |
| `{file_list_item_3}` | {purpose} | [ ] |

### Discovered via Grep/Glob

| Pattern Used | Files Found | Status |
|--------------|-------------|--------|
| `{grep_pattern}` | `{found_file}` | [ ] |
| `{glob_pattern}` | `{found_files}` | [ ] |

---

## Phase 5: Tests

Existing test patterns to follow.

| File | Purpose | Status |
|------|---------|--------|
| `{test_file_1}` | Related tests | [ ] |
| `{test_file_2}` | Test patterns | [ ] |

---

## Token Budget Estimate

| Phase | Files | Estimated Tokens |
|-------|-------|------------------|
| Configuration | {n} | ~{tokens} |
| Architecture | {n} | ~{tokens} |
| Story | {n} | ~{tokens} |
| Code | {n} | ~{tokens} |
| Tests | {n} | ~{tokens} |
| **Total** | **{total}** | **~{total_tokens}** |

### Budget Decision

- [ ] Small context (~20K) - Load essentials only
- [ ] Medium context (~50K) - Standard approach
- [ ] Large context (~100K+) - Full context

---

## File-First Checklist

Before starting implementation:

- [ ] All Phase 1-3 files loaded
- [ ] Story File List reviewed
- [ ] Relevant code files identified
- [ ] Test patterns understood
- [ ] Token budget acceptable

---

## Notes

*Add any observations about the codebase or context loading decisions here.*

```
{notes}
```

---

**Template Version:** 1.0.0
**Created from:** file-first skill
