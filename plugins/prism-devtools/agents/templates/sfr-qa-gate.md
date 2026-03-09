## Certificate: QA Gate Manager

You MUST complete each section in order. Do NOT skip to Conclusion.

### 1. PREMISES
List each quality dimension with its claimed state from the findings provided:
- Traceability: [COMPLETE/GAPS/MISSING] — from requirements-tracer output
- Coverage: lines=X%, branches=Y%, functions=Z%
- Critical issues: N — [brief list of each]
- High issues: N — [brief list of each]
- Medium issues: N | Low issues: N

### 2. EXECUTION TRACE
For each critical and high issue, document supporting evidence:
- Issue-N: [description]
  - Evidence: [file:line, test output, or specific finding quote]
  - Why critical/high (not medium): [specific harm or threshold exceeded]
For coverage metrics: source of these numbers? [tool output, report, or estimated]

### 3. SYSTEMATIC ANALYSIS
| Dimension | Threshold | Actual | Evidence | Met? |
|-----------|-----------|--------|----------|------|
| Lines coverage | ≥80% | X% | [source] | Y/N |
| Branch coverage | ≥80% | X% | [source] | Y/N |
| Critical issues | 0 | N | [list] | Y/N |
| High unmitigated | 0 | N | [list] | Y/N |
| Traceability | COMPLETE | [status] | [tracer ref] | Y/N |

### 4. GAPS AND COUNTEREXAMPLES
List any severity classification unsupported by concrete evidence.
List any metric that came from estimation rather than measurement.

### 5. SELF-CHECK
- Which severity claim is least supported by evidence?
- Would gate status change (PASS↔CONCERNS↔FAIL) if that claim is revised?
- Did you apply the decision rules from your agent definition, or shortcut to a verdict?
Revisit any uncertain classification before proceeding.

### 6. CONCLUSION
Derive PASS/CONCERNS/FAIL ONLY from §3 table. Cite which rows drive the decision.
If WAIVED: confirm business justification is present in findings.

## Output Format
Emit JSON: gate_created, status, critical_issues, high_issues, medium_issues, low_issues, coverage_lines, coverage_branches, coverage_functions, traceability_complete, summary, recommendation, next_action.
Certificate governs your reasoning — parent agent receives only the JSON.
