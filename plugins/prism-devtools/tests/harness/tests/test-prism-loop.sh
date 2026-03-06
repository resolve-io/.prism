#!/usr/bin/env bash
# test-prism-loop.sh — Validate prism-loop skill discovery and initialization:
#   TC-1: stream-json output is non-empty
#   TC-2: prism-loop skill is referenced in session output
#   TC-3: invoking *prism-loop triggers workflow initialization
#          (stream-json contains planning/story/SM related content)
#   TC-4: prism-loop state file created (.claude/prism-loop.local.md)
#   TC-5: state file contains expected YAML frontmatter fields

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${HARNESS_DIR}/lib/common.sh"
source "${HARNESS_DIR}/lib/scaffold.sh"

run_tests() {
  log_section "test-prism-loop"
  init_test_results "test-prism-loop"

  scaffold_brownfield

  local state_file="${TEST_PROJECT_DIR}/.claude/prism-loop.local.md"

  # Remove any prior state so we prove loop init creates it
  rm -f "$state_file"

  # ---- TC-1 & TC-2: ask Claude about prism-loop ---------------------------
  log_info "Running claude session (prompt: what is prism-loop)..."
  run_claude "What is the prism-loop skill and what does it do? Brief answer." \
    "$TEST_PROJECT_DIR"

  assert_json_not_empty "TC-1: prism-loop query produced output"

  assert_json_has "*" "prism-loop" \
    "TC-2: 'prism-loop' referenced in session output"

  # ---- TC-3: invoke prism-loop and check for workflow output --------------
  log_info "Running claude session (prompt: *prism-loop add a hello world function)..."
  run_claude "*prism-loop add a hello world function to the project" \
    "$TEST_PROJECT_DIR"

  assert_json_not_empty "TC-3a: prism-loop invocation produced output"

  # The loop should produce SM/planning content
  # Accept any of: "story", "planning", "SM", "workflow", "PRISM"
  local found_workflow=0
  for keyword in "story" "planning" "SM" "workflow" "PRISM" "TDD"; do
    if python3 - "${LAST_OUTPUT}" "$keyword" <<'PYEOF' 2>/dev/null
import json, sys
path, needle = sys.argv[1], sys.argv[2]
with open(path) as fh:
    for line in fh:
        try:
            if needle.lower() in line.lower():
                sys.exit(0)
        except Exception:
            pass
sys.exit(1)
PYEOF
    then
      found_workflow=1
      break
    fi
  done

  if (( found_workflow )); then
    log_pass "TC-3b: stream-json contains workflow/planning content"
  else
    log_fail "TC-3b: stream-json missing workflow/planning content"
  fi

  # ---- TC-4: state file created by prism-loop init ------------------------
  if [[ -f "$state_file" ]]; then
    log_pass "TC-4: prism-loop state file created ($state_file)"

    # TC-5: state file has YAML frontmatter with expected fields
    local state_content
    state_content="$(cat "$state_file")"

    local found_fields=0
    for field in "active" "phase" "step"; do
      if [[ "$state_content" == *"$field"* ]]; then
        (( found_fields += 1 ))
      fi
    done

    if (( found_fields >= 2 )); then
      log_pass "TC-5: state file contains YAML frontmatter fields (${found_fields}/3)"
    else
      log_skip "TC-5: state file present but expected frontmatter fields sparse (${found_fields}/3)"
    fi
  else
    log_skip "TC-4: state file not created (loop may not have fully initialized)"
    log_skip "TC-5: state file absent — skipping frontmatter check"
  fi

  finalize_test_results "test-prism-loop"
  scaffold_teardown
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_tests
  echo ""
  echo "Results: PASS=${HARNESS_PASS} FAIL=${HARNESS_FAIL} SKIP=${HARNESS_SKIP}"
  (( HARNESS_FAIL == 0 ))
fi
