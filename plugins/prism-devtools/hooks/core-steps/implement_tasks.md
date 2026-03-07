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
Check for available skills using the Skill tool before implementing manually. If a skill can handle any part of this task, invoke it.

Steps:
1. Read failing test output to understand what needs implementing
2. Glob/Grep for implementation files to modify
3. Write MINIMAL code to make the next test pass
4. Run: {{test_cmd}} - check progress
5. Iterate until ALL tests pass
6. Refactor while keeping tests green

CRITICAL: The stop hook validates that ALL tests pass.
Do NOT stop until tests are GREEN.


