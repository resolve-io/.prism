TDD GREEN PHASE: Make Failing Tests Pass

Steps:
1. Read failing test output to understand what needs implementing
2. Glob/Grep for implementation files to modify
3. Write MINIMAL code to make the next test pass
4. Run: {{test_cmd}} - check progress
5. Iterate until ALL tests pass
6. Refactor while keeping tests green

CRITICAL: The stop hook validates that ALL tests pass.
Do NOT stop until tests are GREEN.

Note: The /dev *develop-story skill is available for complex implementation but is not required.
