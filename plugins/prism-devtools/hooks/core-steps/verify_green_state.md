TDD GREEN STATE VERIFICATION: Confirm Implementation Complete

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture and implementation patterns. Read it carefully.
2. For deeper context: /brain search "topic you need"
   - Test conventions: /brain search "test coverage conventions"
   - Testing frameworks: /brain search "integration test framework patterns"
3. THEN proceed with verification steps

## Skills
IMPORTANT: Before running quality checks manually, check Available Skills above and invoke the matching skill — skills already know your project's test runner, lint config, and type-check setup, so invoking them is faster and more reliable than running checks manually.
For verification:
- **Invoke /test** to verify all tests pass — the skill knows your full test suite and surfaces failures with context; don't run tests manually when the skill handles configuration for you.
- **Invoke /lint** (if available) — the skill knows your lint config and which files to check; running lint manually risks missing config flags specific to this project.

Steps:
1. Run all tests (unit, integration, e2e)
2. Verify all tests PASS
3. Invoke /lint skill (if available) — before running lint manually, check Available Skills above; the skill knows your project's lint config and won't miss project-specific flags
4. Run type checks (if applicable)
5. Verify build succeeds
6. Confirm all ACs have passing test coverage

The stop hook validates tests + lint before advancing to completion gate.


