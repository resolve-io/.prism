TDD RED PHASE: Write Failing Tests

## Understanding the System (DO THIS FIRST)
1. Your prompt includes a ## System Context section with relevant
   architecture, patterns, and code. Read it carefully.
2. For deeper understanding: /brain search "topic you need"
   - Test naming: /brain search "test naming conventions"
   - Testing frameworks: /brain search "testing framework patterns"
   - Test structure: /brain search "unit test conventions for module X"
3. THEN Glob for existing test files: *.test.*, *.spec.*, *_test.*, test_*.*
4. Read existing tests to understand patterns

## Skills
IMPORTANT: Before running tests manually, check Available Skills above and invoke the matching skill — it knows your project's test runner, command flags, and output patterns so you don't have to guess.
For RED phase:
- **Invoke /test** to run and confirm tests fail cleanly. The skill knows exactly how to invoke your test runner and will parse fail/pass output for you — running tests manually risks using wrong flags or missing config.

Trace Convention (REQUIRED - workflow blocks without this):
  Map each test to its AC. If any AC lacks a mapped test, workflow blocks
  with 'SILENT DROP DETECTED'.

Test Documentation (REQUIRED):
  Each test MUST include a traceability header as the FIRST thing in the test:

  For Python:
    def test_ac1_user_can_login(self):
        """
        AC-1: User can login with valid credentials
        Requirement: Authentication flow validates credentials against store
        Expected: Returns auth token and redirects to dashboard
        """

  For JavaScript/TypeScript:
    // AC-1: User can login with valid credentials
    // Requirement: Authentication flow validates credentials against store
    // Expected: Returns auth token and redirects to dashboard
    test('AC-1: user can login with valid credentials', () => {

  For C#:
    /// <summary>
    /// AC-1: User can login with valid credentials
    /// Requirement: Authentication flow validates credentials against store
    /// Expected: Returns auth token and redirects to dashboard
    /// </summary>
    [Fact]
    public async Task AC1_UserCanLogin_ReturnsToken()

  This makes tests self-documenting artifacts that carry their own traceability.

Steps:
1. Read story file - extract all acceptance criteria
2. Glob for existing test files: *.test.*, *.spec.*, *_test.*, test_*.*
3. Read existing tests to understand patterns
4. Extend existing files if found, create new if needed
5. Write one failing test per AC with traceability header and clear assertion
6. Invoke /test skill to verify FAIL — before running tests manually, check Available Skills above; the /test skill knows your project test configuration and will confirm assertion failures (not syntax/import errors)
7. Update story with test-to-AC mappings

CRITICAL: Tests must FAIL cleanly (assertion failures, not errors).
The stop hook will run tests and validate RED state before advancing.


