#!/usr/bin/env bash
# test-session-start.sh — Validate the SessionStart hook fires and produces
# expected side-effects:
#   TC-1: stream-json output is non-empty (session ran successfully)
#   TC-2: stream-json contains a system event (hook injection visible)
#   TC-3: .prism/brain/memory/MEMORY.md created in the test project
#   TC-4: MEMORY.md content references Brain
#   TC-5: stream-json system message mentions "Brain"

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${HARNESS_DIR}/lib/common.sh"
source "${HARNESS_DIR}/lib/scaffold.sh"

run_tests() {
  log_section "test-session-start"
  init_test_results "test-session-start"

  scaffold_brownfield

  local mem_md="${TEST_PROJECT_DIR}/.prism/brain/memory/MEMORY.md"

  # Remove any pre-existing MEMORY.md so TC-3 proves the hook created it
  rm -f "$mem_md"

  log_info "Running claude session (prompt: 'Say hello')..."
  run_claude "Say hello and stop." "$TEST_PROJECT_DIR"

  # TC-1: stream-json output is non-empty
  assert_json_not_empty "TC-1: stream-json output is non-empty"

  # TC-2: output contains at least one 'system' type event
  assert_json_event_type "system" "TC-2: stream-json contains system event"

  # TC-3: session-start hook created MEMORY.md in test project
  assert_file_exists "$mem_md" \
    "TC-3: session-start hook created .prism/brain/memory/MEMORY.md"

  # TC-4: MEMORY.md content references Brain
  if [[ -f "$mem_md" ]]; then
    local mem_content
    mem_content="$(cat "$mem_md")"
    assert_contains "Brain" "$mem_content" \
      "TC-4: MEMORY.md mentions Brain"
  else
    log_skip "TC-4: MEMORY.md not present — skipping content check"
  fi

  # TC-5: system message in stream-json mentions Brain
  assert_json_has "*" "Brain" \
    "TC-5: stream-json system message mentions Brain"

  finalize_test_results "test-session-start"
  scaffold_teardown
}

# Run standalone if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_tests
  echo ""
  echo "Results: PASS=${HARNESS_PASS} FAIL=${HARNESS_FAIL} SKIP=${HARNESS_SKIP}"
  (( HARNESS_FAIL == 0 ))
fi
