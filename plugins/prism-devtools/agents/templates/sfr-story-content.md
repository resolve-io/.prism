## Certificate: Story Content Validator

You MUST complete each section in order. Do NOT skip to Conclusion.

### 1. PREMISES
List each item under review with its claimed quality:
- AC-1: [text] — claims: measurable, user-outcome, no ambiguity
- AC-N: ...
- Task-1: [text] — claims: specific, sized ≤3d, includes testing
- Task-N: ...
- Dev Notes: [summary] — claims: guidance, architecture refs, dependencies
- Testing Section: [summary] — claims: scenarios, edge cases, NFRs
- Sizing: [estimate] — claims: 1-3 day total

### 2. EXECUTION TRACE
For each item, document evidence found and evidence missing:
- AC-N: pass/fail wording present? user-outcome (not technical)? ambiguous terms found?
- Task-N: actionable verb? size bounded? test requirement stated?
- Dev Notes: guidance specific? pattern referenced? challenge identified?
- Testing: scenarios named? edge case listed? NFR mentioned?
- Sizing: estimate stated? decomposition threshold triggered?

### 3. SYSTEMATIC ANALYSIS
| Item | Criterion | Evidence | Met? |
|------|-----------|----------|------|
| AC-N | measurable | [quote or MISSING] | Y/N |
| Task-N | ≤3d, testable | [quote or MISSING] | Y/N |
| Dev Notes | guidance | [quote or MISSING] | Y/N |
| Testing | scenarios | [quote or MISSING] | Y/N |
| Sizing | 1-3d | [estimate or MISSING] | Y/N |

### 4. GAPS AND COUNTEREXAMPLES
List every N row from §3. If none: "No gaps found — all criteria met with concrete evidence."

### 5. SELF-CHECK
- Which §3 row has the least concrete evidence?
- Would quality_score change >10 if that evidence is wrong?
- Did you read the story file, or assume content?
Fix any weak evidence before proceeding.

### 6. CONCLUSION
Derive quality_score (0-100) and recommendation ONLY from §3 rows. Cite specific rows.

## Output Format
Emit JSON: quality_score, checks{}, recommendations[], recommendation (APPROVE/REVISE/SPLIT_STORY).
Certificate governs your reasoning — parent agent receives only the JSON.
