# PRISM Meta-Conductor benchmark

Scores the server-side promotion policy for AutoAgent-style prompt candidates.

This is intentionally not an LLM benchmark. PRISM can generate conservative
rule-based candidates from PSP outcome traces, and a calling agent may also
draft prompt variants. In both cases, PRISM owns storage and promotion. This
gate verifies that PRISM creates the deterministic no-LLM candidate and
promotes only candidates that beat baseline on holdout metrics while preserving
context-pack quality and operational safety signals.

Run:

```bash
python benchmarks/metaconductor/run.py
```

Results are written to `benchmarks/results/metaconductor/`.

## Relation to TerminalBench and SpreadsheetBench

This fast gate proves PRISM's promotion policy and deterministic no-LLM
candidate generation. It does not claim TerminalBench or SpreadsheetBench
leaderboard quality.

- TerminalBench belongs in an optional overnight end-to-end tier because it
  measures whether an agent can complete real terminal tasks in containers.
- SpreadsheetBench belongs in a domain-specific tier if PRISM is being tested
  as a spreadsheet/business-workflow agent aid.

Meta-Conductor candidates should use this benchmark as the local safety gate,
then use external task-completion suites such as TerminalBench or
SpreadsheetBench as holdout evidence before broad promotion.
