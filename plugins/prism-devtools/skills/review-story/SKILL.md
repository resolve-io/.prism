---
name: review-story
description: QA review with risk assessment, code quality analysis, refactoring, and quality gate decision.
version: 1.0.0
---

# Review Story

Adaptive, risk-aware QA review that creates a gate file and updates the story's QA Results section.

## Steps

1. Verify story status is "Review" and all automated tests pass
2. Run risk assessment to determine review depth (auto-escalate for auth/payment/security changes)
3. Analyze requirements traceability, code quality, test architecture, and NFRs
4. Refactor code where safe and appropriate; document all changes
5. Create gate file (PASS/CONCERNS/FAIL) and update story QA Results section

For detailed instructions, see [instructions.md](reference/instructions.md).
