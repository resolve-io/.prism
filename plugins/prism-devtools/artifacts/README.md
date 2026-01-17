# PRISM Artifacts

This directory contains **operational artifacts** generated during PRISM development and usage.

---

## Directory Structure

```
artifacts/
├── stories/              # Working stories (in-progress and completed)
├── qa/
│   └── gates/           # Quality gate decisions (YAML files)
└── validation/          # Validation reports from testing
```

---

## What Belongs Here

**Stories** (`stories/`)
- Active development stories
- Completed stories with implementation records
- Story artifacts with file lists, dev notes, QA records

**QA Gates** (`qa/gates/`)
- Quality gate YAML files (PASS/CONCERNS/FAIL/WAIVED)
- Traceability reports
- Test coverage analysis
- Issue tracking

**Validation Reports** (`validation/`)
- System validation reports
- Integration test results
- Compliance validation outputs

---

## What Does NOT Belong Here

❌ **Documentation** → Use `docs/` for all documentation
❌ **Templates** → Use `templates/` for reusable templates
❌ **Checklists** → Use `checklists/` for quality checklists
❌ **Tasks** → Use `tasks/` for reusable task definitions
❌ **Workflows** → Use `workflows/` for workflow definitions

---

## Related Directories

- **[docs/](../docs/index.md)** - System documentation (NOT operational artifacts)
- **[templates/](../templates/README.md)** - Document templates
- **[skills/](../skills/README.md)** - Reusable skill definitions
- **[workflows/](../workflows/README.md)** - Workflow orchestration

---

## Archive Policy

Completed stories and old validation reports should be archived periodically:
- Stories: After sprint completion or quarterly
- QA Gates: Keep current sprint + last sprint, archive older
- Validation: Archive after 90 days unless reference needed

Archive documentation will be added in a future update.

---

**Last Updated**: 2025-11-10
