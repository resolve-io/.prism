TDD GREEN PHASE: Make Failing Tests Pass

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture, code patterns, and past solutions. Read it carefully.
2. Read the failing test output to understand what needs implementing
3. For deeper understanding: /brain search "topic you need"
   - Code patterns: /brain search "code patterns for repositories"
   - Module structure: /brain search "module structure conventions"
   - Error handling: /brain search "error handling patterns"
4. THEN Glob/Grep for implementation files to modify

## Skills
IMPORTANT: Before running tests or committing manually, check Available Skills above and invoke the matching skill — skills know your project's test runner configuration and commit conventions so you iterate faster without hunting down commands.
For GREEN phase:
- **Invoke /test** after each implementation step — the skill runs your full test suite with the right flags and parses results; running tests manually risks missing config or misreading output.
- **Invoke /checkin** to commit working changes — the skill enforces this project's commit message format and staging conventions automatically.

Steps:
1. Read failing test output to understand what needs implementing
2. Glob/Grep for implementation files to modify
3. Write MINIMAL code to make the next test pass
4. Invoke /test skill — before running tests manually, check Available Skills above; the /test skill knows your project's test runner and will surface failures with context
5. Iterate until ALL tests pass
6. Refactor while keeping tests green

CRITICAL: The stop hook validates that ALL tests pass.
Do NOT stop until tests are GREEN.


