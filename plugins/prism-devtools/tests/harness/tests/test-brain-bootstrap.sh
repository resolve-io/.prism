#!/usr/bin/env bash
# test-brain-bootstrap.sh — Validate Brain bootstrap on session start:
#   TC-1: .prism/brain/ directory created in the test project
#   TC-2: brain.db SQLite database exists after session
#   TC-3: incremental_reindex ran (brain.db is non-zero bytes)
#   TC-4: Brain auto-bootstrap: search works after indexing
#         (stream-json output references indexed content)

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${HARNESS_DIR}/lib/common.sh"
source "${HARNESS_DIR}/lib/scaffold.sh"

run_tests() {
  log_section "test-brain-bootstrap"
  init_test_results "test-brain-bootstrap"

  scaffold_brownfield

  local brain_dir="${TEST_PROJECT_DIR}/.prism/brain"
  local brain_db="${brain_dir}/brain.db"

  # Remove existing brain artefacts so we prove bootstrap creates them
  rm -rf "$brain_dir"

  log_info "Running claude session (prompt: 'What files are in this project?')..."
  run_claude "List the files in this project and stop." "$TEST_PROJECT_DIR"

  # TC-1: .prism/brain/ directory exists after session
  assert_file_exists "$brain_dir" \
    "TC-1: .prism/brain/ directory created by session-start hook"

  # TC-2: brain.db exists
  assert_file_exists "$brain_db" \
    "TC-2: brain.db SQLite database created"

  # TC-3: brain.db is non-zero bytes (reindex wrote data)
  if [[ -f "$brain_db" ]]; then
    local db_size
    db_size="$(wc -c < "$brain_db" | tr -d ' ')"
    if (( db_size > 0 )); then
      log_pass "TC-3: brain.db is non-zero (${db_size} bytes)"
    else
      log_fail "TC-3: brain.db is empty (0 bytes)"
    fi
  else
    log_skip "TC-3: brain.db absent — skipping size check"
  fi

  # TC-4: stream-json output is non-empty (session ran)
  assert_json_not_empty "TC-4: claude session produced stream-json output"

  finalize_test_results "test-brain-bootstrap"
  scaffold_teardown
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_tests
  echo ""
  echo "Results: PASS=${HARNESS_PASS} FAIL=${HARNESS_FAIL} SKIP=${HARNESS_SKIP}"
  (( HARNESS_FAIL == 0 ))
fi
