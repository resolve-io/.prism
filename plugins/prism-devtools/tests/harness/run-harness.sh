#!/usr/bin/env bash
# run-harness.sh — Main orchestrator for the prism-devtools end-to-end test harness.
#
# Runs sequential tests against the sibling prism-test project using claude -p
# (headless) with the plugin loaded via --plugin-dir.
#
# Usage:
#   ./run-harness.sh                  # run all tests
#   ./run-harness.sh session-start    # run tests matching filter
#   VERBOSE=1 ./run-harness.sh        # verbose output
#   PRISM_TEST_DIR=/path ./run-harness.sh  # override test project path
#
# Environment variables:
#   PRISM_TEST_DIR   Path to the prism-test project (auto-detected if unset)
#   PLUGIN_DIR       Path to prism-devtools plugin (auto-detected if unset)
#   VERBOSE          Set to 1 for verbose output
#   FILTER           Test name substring filter (or pass as $1)

set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILTER="${1:-${FILTER:-}}"

# ---------------------------------------------------------------------------
# Resolve PLUGIN_DIR — the prism-devtools plugin root
# ---------------------------------------------------------------------------
if [[ -z "${PLUGIN_DIR:-}" ]]; then
  PLUGIN_DIR="$(cd "${HARNESS_DIR}/../.." && pwd)"
fi

# ---------------------------------------------------------------------------
# Resolve PRISM_TEST_DIR — the sibling prism-test project
# ---------------------------------------------------------------------------
if [[ -z "${PRISM_TEST_DIR:-}" ]]; then
  # Canonical layout: prism/ and prism-test/ are siblings under the same parent
  REPO_ROOT="$(cd "${HARNESS_DIR}/../../../.." && pwd)"
  PARENT="$(dirname "$REPO_ROOT")"
  CANDIDATE="${PARENT}/prism-test"

  if [[ -d "$CANDIDATE" ]]; then
    PRISM_TEST_DIR="$CANDIDATE"
  else
    echo "ERROR: Cannot find prism-test directory."
    echo "  Expected: $CANDIDATE"
    echo "  Set PRISM_TEST_DIR env var to override."
    exit 1
  fi
fi

export HARNESS_DIR PLUGIN_DIR PRISM_TEST_DIR

# ---------------------------------------------------------------------------
# Source shared libraries
# ---------------------------------------------------------------------------
source "${HARNESS_DIR}/lib/common.sh"
source "${HARNESS_DIR}/lib/scaffold.sh"

# ---------------------------------------------------------------------------
# Results directory
# ---------------------------------------------------------------------------
RESULTS_DIR="${HARNESS_DIR}/results"
export RESULTS_DIR
rm -rf "$RESULTS_DIR"
mkdir -p "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
_preflight_ok=1

if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' CLI not found. Install Claude Code and ensure it is on PATH."
  _preflight_ok=0
fi

if ! command -v python3 &>/dev/null; then
  echo "ERROR: 'python3' not found. Required for JSON parsing assertions."
  _preflight_ok=0
fi

if [[ ! -d "$PLUGIN_DIR/hooks" ]]; then
  echo "ERROR: PLUGIN_DIR does not look like prism-devtools: $PLUGIN_DIR"
  _preflight_ok=0
fi

if [[ ! -d "$PRISM_TEST_DIR" ]]; then
  echo "ERROR: PRISM_TEST_DIR not found: $PRISM_TEST_DIR"
  _preflight_ok=0
fi

if (( _preflight_ok == 0 )); then
  exit 1
fi

# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------
TEST_FILES=(
  "${HARNESS_DIR}/tests/test-session-start.sh"
  "${HARNESS_DIR}/tests/test-brain-bootstrap.sh"
  "${HARNESS_DIR}/tests/test-skill-discovery.sh"
  "${HARNESS_DIR}/tests/test-prism-loop.sh"
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo -e "${_C_BOLD}prism-devtools end-to-end test harness${_C_RESET}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Plugin:       $PLUGIN_DIR"
echo "  Test project: $PRISM_TEST_DIR"
[[ -n "$FILTER" ]] && echo "  Filter:       $FILTER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ---------------------------------------------------------------------------
# Run each test file in a sub-process so failures don't abort the suite.
# Capture per-file counters via a temp file.
# ---------------------------------------------------------------------------
TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0
FAILED_TESTS=()

for test_file in "${TEST_FILES[@]}"; do
  test_name="$(basename "$test_file" .sh)"

  # Apply filter
  if [[ -n "$FILTER" && "$test_name" != *"$FILTER"* ]]; then
    continue
  fi

  if [[ ! -f "$test_file" ]]; then
    echo "  WARN  test file not found: $test_file"
    continue
  fi

  # Run the test file in a subshell; it sources common.sh and calls run_tests()
  # We capture output and emit counters to a temp file.
  tmpresult="$(mktemp /tmp/harness-result-XXXXXX)"

  (
    source "${HARNESS_DIR}/lib/common.sh"
    source "${HARNESS_DIR}/lib/scaffold.sh"
    source "$test_file"
    run_tests
    echo "COUNTERS ${HARNESS_PASS} ${HARNESS_FAIL} ${HARNESS_SKIP}"
  ) 2>&1 | tee "${tmpresult}.out"

  # Extract counters from last COUNTERS line
  counters_line="$(grep '^COUNTERS ' "${tmpresult}.out" | tail -1 || true)"
  rm -f "${tmpresult}.out" "$tmpresult"

  if [[ -n "$counters_line" ]]; then
    read -r _ fp ff fs <<< "$counters_line"
    TOTAL_PASS=$(( TOTAL_PASS + fp ))
    TOTAL_FAIL=$(( TOTAL_FAIL + ff ))
    TOTAL_SKIP=$(( TOTAL_SKIP + fs ))
    (( ff > 0 )) && FAILED_TESTS+=("$test_name")
  else
    echo -e "  ${_C_RED}ERROR${_C_RESET}  $test_name: test file did not emit counters"
    FAILED_TESTS+=("$test_name")
    (( TOTAL_FAIL += 1 ))
  fi

  echo ""
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ${_C_GREEN}PASS${_C_RESET} ${TOTAL_PASS}   ${_C_RED}FAIL${_C_RESET} ${TOTAL_FAIL}   ${_C_YELLOW}SKIP${_C_RESET} ${TOTAL_SKIP}"

if (( ${#FAILED_TESTS[@]} > 0 )); then
  echo ""
  echo -e "  ${_C_RED}Failed tests:${_C_RESET}"
  for t in "${FAILED_TESTS[@]}"; do
    echo -e "    ${_C_RED}✗${_C_RESET} $t"
  done
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Write harness-report.json
python3 - "$RESULTS_DIR" "$TOTAL_PASS" "$TOTAL_FAIL" "$TOTAL_SKIP" <<'PYEOF'
import json, sys, os
out_dir, total_pass, total_fail, total_skip = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
os.makedirs(out_dir, exist_ok=True)
report = {"total_pass": total_pass, "total_fail": total_fail, "total_skip": total_skip}
with open(os.path.join(out_dir, "harness-report.json"), "w") as f:
    json.dump(report, f, indent=2)
PYEOF

(( TOTAL_FAIL == 0 ))
