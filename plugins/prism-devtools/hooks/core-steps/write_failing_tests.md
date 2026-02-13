TDD RED PHASE: Write Failing Tests

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
6. Run: {{test_cmd}} - verify FAIL with assertion errors (not syntax/import)
7. Update story with test-to-AC mappings

CRITICAL: Tests must FAIL cleanly (assertion failures, not errors).
The stop hook will run tests and validate RED state before advancing.

Note: The /qa *write-failing-tests skill is available for complex test orchestration but is not required.
