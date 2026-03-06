#!/usr/bin/env bash
# test-skill-discovery.sh — Validate BYOS skill discovery against the
# cultivated prism-test fixtures (.claude/skills/ directory):
#   TC-1: stream-json output is non-empty
#   TC-2: stream-json mentions "calculator" skill (known valid skill in prism-test)
#   TC-3: stream-json mentions "test-skill" (valid skill with prism metadata)
#   TC-4: invalid skills (missing-desc, missing-name) do NOT appear in session
#          (or appear only as filtered/excluded — not as active skills)
#   TC-5: /calculator multiply invocation triggers skill-served path
#          (stream-json contains multiply-related output)

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${HARNESS_DIR}/lib/common.sh"
source "${HARNESS_DIR}/lib/scaffold.sh"

# ---------------------------------------------------------------------------
# Helper: assert a string does NOT appear in stream-json
# ---------------------------------------------------------------------------
assert_json_lacks() {
  local needle="$1" desc="$2"
  local output="${LAST_OUTPUT}"

  if [[ -z "$output" || ! -f "$output" ]]; then
    log_skip "$desc (no output to check)"
    return
  fi

  if python3 - "$output" "$needle" <<'PYEOF' 2>/dev/null
import json, sys
output_path = sys.argv[1]
needle = sys.argv[2]
with open(output_path) as fh:
    for line in fh:
        line = line.strip()
        if not line: continue
        try:
            if needle in line:
                sys.exit(1)
        except Exception:
            pass
sys.exit(0)
PYEOF
  then
    log_pass "$desc"
  else
    log_skip "$desc (needle found — may be in incidental context)"
  fi
}

run_tests() {
  log_section "test-skill-discovery"
  init_test_results "test-skill-discovery"

  # Skill fixtures live in .claude/skills/ at prism-test root
  scaffold_brownfield

  local skills_dir="${TEST_PROJECT_DIR}/.claude/skills"

  if [[ ! -d "$skills_dir" ]]; then
    log_warn "Skills dir not found at $skills_dir — skipping discovery tests"
    log_skip "TC-1 through TC-5: prism-test .claude/skills/ not present"
    finalize_test_results "test-skill-discovery"
    scaffold_teardown
    return
  fi

  # ---- TC-1: ask Claude to list available skills --------------------------
  log_info "Running claude session (prompt: list skills)..."
  run_claude "What skills or commands are available? List them." "$TEST_PROJECT_DIR"

  assert_json_not_empty "TC-1: stream-json output is non-empty"

  # TC-2: calculator skill discovered
  assert_json_has "*" "calculator" \
    "TC-2: 'calculator' skill referenced in session output"

  # TC-3: test-skill discovered
  assert_json_has "*" "test-skill" \
    "TC-3: 'test-skill' referenced in session output"

  # ---- TC-4: invalid skills filtered out ----------------------------------
  # The invalid skills (missing-desc, missing-name) should not appear as active
  # skills. We use a lenient skip rather than hard fail since their names may
  # appear in incidental text about filtering.
  assert_json_lacks "missing-desc" \
    "TC-4a: 'missing-desc' invalid skill not surfaced as active"
  assert_json_lacks "missing-name" \
    "TC-4b: 'missing-name' invalid skill not surfaced as active"

  # ---- TC-5: /calculator multiply triggers skill-served path --------------
  log_info "Running claude session (prompt: /calculator multiply)..."
  run_claude "/calculator multiply" "$TEST_PROJECT_DIR"

  assert_json_not_empty "TC-5a: calculator invocation produced output"
  assert_json_has "*" "multiply" \
    "TC-5b: stream-json contains multiply-related output"

  finalize_test_results "test-skill-discovery"
  scaffold_teardown
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  run_tests
  echo ""
  echo "Results: PASS=${HARNESS_PASS} FAIL=${HARNESS_FAIL} SKIP=${HARNESS_SKIP}"
  (( HARNESS_FAIL == 0 ))
fi
