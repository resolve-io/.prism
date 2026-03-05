TDD GREEN STATE VERIFICATION: Confirm Implementation Complete

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture and implementation patterns. Read it carefully.
2. For deeper context: /brain search "topic you need"
   - Test coverage patterns: /brain search "integration test conventions"
   - Build requirements: /brain search "CI pipeline requirements"
3. THEN proceed with verification steps

Steps:
1. Run all tests (unit, integration, e2e)
2. Verify all tests PASS
3. Run linting: {{lint_cmd}}
4. Run type checks (if applicable)
5. Verify build succeeds
6. Confirm all ACs have passing test coverage

The stop hook validates tests + lint before advancing to completion gate.


