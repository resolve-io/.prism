TDD GREEN STATE VERIFICATION: Confirm Implementation Complete

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture and implementation patterns. Read it carefully.
2. For deeper context: /brain search "topic you need"
   - Test conventions: /brain search "test coverage conventions"
   - Testing frameworks: /brain search "integration test framework patterns"
3. THEN proceed with verification steps

## Skills
IMPORTANT: See Available Skills listed above. For verification:
- Run /test to verify all tests pass before marking complete

Steps:
1. Run all tests (unit, integration, e2e)
2. Verify all tests PASS
3. Invoke /lint skill (if available) or run linting checks
4. Run type checks (if applicable)
5. Verify build succeeds
6. Confirm all ACs have passing test coverage

The stop hook validates tests + lint before advancing to completion gate.


