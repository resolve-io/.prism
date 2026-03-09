## Certificate: Requirements Tracer

You MUST complete each section in order. Do NOT skip to Conclusion.

### 1. PREMISES
List each story acceptance criterion:
- AC-1: [description] — maps to epic requirement: [epic-AC text or UNKNOWN]
- AC-N: ...

### 2. EXECUTION TRACE
For EACH AC, trace the full chain and record evidence at each link:
- AC-N:
  - PRD→Epic: [epic file:line] or MISSING
  - Story AC→Epic AC: aligned? [quote comparison]
  - Epic→Code: [impl file:line] or MISSING — searched: [patterns used]
  - Code→Test: [test file:line] or MISSING — searched: [patterns used]
  - Evidence missing: [what you searched for but did not find]

### 3. SYSTEMATIC ANALYSIS
| AC | Epic Mapped | Code Found | Test Found | Status |
|----|-------------|------------|------------|--------|
| AC-N | Y/N [ref] | Y/N [file] | Y/N [file] | TRACED/PARTIAL/MISSING |

Coverage: N TRACED / M total = X%

### 4. GAPS AND COUNTEREXAMPLES
For each PARTIAL or MISSING row: state the concrete missing link with search evidence.
For any orphaned code (file with no corresponding AC): name the file and explain.

### 5. SELF-CHECK
- Which TRACED row has the weakest code→test link?
- Did you Grep for test files or assume they don't exist?
- Is any MISSING possibly in a file you haven't read yet?
Strengthen uncertain links before proceeding.

### 6. CONCLUSION
State traceability_status (COMPLETE/GAPS/MISSING), coverage %, and recommendation ONLY from §3.
Reference specific rows for each gap cited.

## Output Format
Emit JSON: traceability_status, requirements_traced, requirements_total, coverage_percentage, trace_matrix[], gaps[], orphaned_code[], test_quality{}, recommendation.
Certificate governs your reasoning — parent agent receives only the JSON.
