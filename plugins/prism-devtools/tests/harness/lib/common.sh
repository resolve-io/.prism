#!/usr/bin/env bash
# lib/common.sh — Shared utilities for the prism-devtools test harness.
#
# Usage: source this file from test scripts or run-harness.sh.
# Exports: HARNESS_PASS, HARNESS_FAIL, HARNESS_SKIP, LAST_OUTPUT
#          log_pass log_fail log_info log_section log_warn
#          run_claude assert_eq assert_contains assert_file_exists
#          assert_json_has assert_json_event_type

# ---------------------------------------------------------------------------
# Color codes (suppressed when not a tty)
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
  _C_RESET='\033[0m'
  _C_GREEN='\033[0;32m'
  _C_RED='\033[0;31m'
  _C_YELLOW='\033[0;33m'
  _C_CYAN='\033[0;36m'
  _C_BOLD='\033[1m'
else
  _C_RESET='' _C_GREEN='' _C_RED='' _C_YELLOW='' _C_CYAN='' _C_BOLD=''
fi

# ---------------------------------------------------------------------------
# Counters (file-scoped; run-harness.sh aggregates across test files)
# ---------------------------------------------------------------------------
HARNESS_PASS=0
HARNESS_FAIL=0
HARNESS_SKIP=0

# Last stream-json output file path (set by run_claude)
LAST_OUTPUT=""

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log_info()    { echo -e "${_C_CYAN}  INFO${_C_RESET}  $*"; }
log_warn()    { echo -e "${_C_YELLOW}  WARN${_C_RESET}  $*"; }
log_section() { echo -e "${_C_BOLD}${_C_CYAN}── $* ──${_C_RESET}"; }
harness_log() { echo -e "$*"; }

log_pass() {
  echo -e "  ${_C_GREEN}PASS${_C_RESET}  $*"
  (( HARNESS_PASS += 1 ))
}

log_fail() {
  echo -e "  ${_C_RED}FAIL${_C_RESET}  $*"
  (( HARNESS_FAIL += 1 ))
}

log_skip() {
  echo -e "  ${_C_YELLOW}SKIP${_C_RESET}  $*"
  (( HARNESS_SKIP += 1 ))
}

# ---------------------------------------------------------------------------
# run_claude — invoke claude -p headless and capture stream-json to a tmp file
#
# Usage: run_claude <prompt> [work_dir]
# Sets:  LAST_OUTPUT — path to captured stream-json output
# Returns: claude exit code
# ---------------------------------------------------------------------------
run_claude() {
  local prompt="$1"
  local work_dir="${2:-${TEST_PROJECT_DIR:-${PRISM_TEST_DIR:?PRISM_TEST_DIR not set}}}"

  if [[ -z "${PLUGIN_DIR:-}" ]]; then
    echo "ERROR: PLUGIN_DIR not set" >&2
    return 1
  fi

  local tmpout
  tmpout="$(mktemp /tmp/claude-harness-XXXXXX.jsonl)"
  LAST_OUTPUT="$tmpout"

  local exit_code=0
  (
    cd "$work_dir"
    env -u CLAUDECODE claude -p "$prompt" \
      --plugin-dir "$PLUGIN_DIR" \
      --output-format stream-json \
      --dangerously-skip-permissions \
      --no-session-persistence \
      --model sonnet \
      --max-budget-usd 0.50 \
      --max-turns 3 \
      2>/dev/null
  ) > "$tmpout" || exit_code=$?

  return $exit_code
}

# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

# assert_eq <expected> <actual> <description>
assert_eq() {
  local expected="$1" actual="$2" desc="$3"
  if [[ "$actual" == "$expected" ]]; then
    log_pass "$desc"
  else
    log_fail "$desc (expected='$expected' got='$actual')"
  fi
}

# assert_contains <needle> <haystack> <description>
assert_contains() {
  local needle="$1" haystack="$2" desc="$3"
  if [[ "$haystack" == *"$needle"* ]]; then
    log_pass "$desc"
  else
    log_fail "$desc (expected '$needle' in '$haystack')"
  fi
}

# assert_file_exists <path> <description>
assert_file_exists() {
  local path="$1" desc="${2:-file exists: $1}"
  if [[ -e "$path" ]]; then
    log_pass "$desc"
  else
    log_fail "$desc (path not found: $path)"
  fi
}

# assert_file_absent <path> <description>
assert_file_absent() {
  local path="$1" desc="${2:-file absent: $1}"
  if [[ ! -e "$path" ]]; then
    log_pass "$desc"
  else
    log_fail "$desc (path should not exist: $path)"
  fi
}

# assert_json_has <field_path> <substring> <description>
# Searches all JSON lines in LAST_OUTPUT for a field matching the substring.
# field_path uses dot notation, e.g. "message.content" or "type"
assert_json_has() {
  local field="$1" needle="$2" desc="$3"
  local output="${4:-${LAST_OUTPUT}}"

  if [[ -z "$output" || ! -f "$output" ]]; then
    log_fail "$desc (no output file)"
    return
  fi

  if python3 - "$output" "$field" "$needle" <<'PYEOF'
import json, sys

output_path = sys.argv[1]
field_path  = sys.argv[2]
needle      = sys.argv[3]

def deep_get(obj, path):
    for key in path.split('.'):
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return obj

def search(obj):
    """Recursively search for needle in any string value."""
    if isinstance(obj, str):
        return needle in obj
    if isinstance(obj, dict):
        return any(search(v) for v in obj.values())
    if isinstance(obj, list):
        return any(search(item) for item in obj)
    return False

found = False
with open(output_path) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if field_path == '*':
                if search(obj):
                    found = True
                    break
            else:
                val = deep_get(obj, field_path)
                if val is not None and needle in str(val):
                    found = True
                    break
        except json.JSONDecodeError:
            pass

sys.exit(0 if found else 1)
PYEOF
  then
    log_pass "$desc"
  else
    log_fail "$desc (field='$field' needle='$needle' not found in $output)"
  fi
}

# assert_json_event_type <event_type> <description>
# Asserts at least one JSON line has {"type": "<event_type>"}
assert_json_event_type() {
  local event_type="$1" desc="$2"
  assert_json_has "type" "$event_type" "$desc"
}

# assert_json_not_empty <description>
# Asserts LAST_OUTPUT has at least one parseable JSON line
assert_json_not_empty() {
  local desc="${1:-stream-json output is non-empty}"
  local output="${LAST_OUTPUT}"

  if [[ -z "$output" || ! -f "$output" ]]; then
    log_fail "$desc (no output file)"
    return
  fi

  local count
  count=$(python3 -c "
import json, sys
count = 0
for line in open(sys.argv[1]):
    line = line.strip()
    if not line: continue
    try:
        json.loads(line)
        count += 1
    except: pass
print(count)
" "$output" 2>/dev/null || echo 0)

  if (( count > 0 )); then
    log_pass "$desc ($count events)"
  else
    log_fail "$desc (0 parseable JSON events)"
  fi
}

# ---------------------------------------------------------------------------
# Results output helpers (optional; used when RESULTS_DIR is set by harness)
# ---------------------------------------------------------------------------
RESULTS_DIR="${RESULTS_DIR:-}"

# init_test_results <test_name>
# Creates output directory for a test if RESULTS_DIR is set.
init_test_results() {
  local test_name="$1"
  if [[ -n "${RESULTS_DIR:-}" ]]; then
    mkdir -p "${RESULTS_DIR}/${test_name}"
  fi
}

# finalize_test_results <test_name>
# Copies LAST_OUTPUT to results dir and writes summary.json + transcript.md.
finalize_test_results() {
  local test_name="$1"
  if [[ -z "${RESULTS_DIR:-}" ]]; then
    return
  fi

  local out_dir="${RESULTS_DIR}/${test_name}"
  mkdir -p "$out_dir"

  # Copy raw stream-json output
  if [[ -n "${LAST_OUTPUT:-}" && -f "$LAST_OUTPUT" ]]; then
    cp "$LAST_OUTPUT" "${out_dir}/raw.jsonl"
  fi

  # Write summary.json
  python3 - "$out_dir" "$test_name" "${HARNESS_PASS}" "${HARNESS_FAIL}" <<'PYEOF'
import json, sys, os
out_dir, test_name, passed, total_fail = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
assertions = passed + total_fail
summary = {
    "test_name": test_name,
    "passed": passed,
    "failed": total_fail,
    "assertions": assertions,
}
with open(os.path.join(out_dir, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)
PYEOF

  # Write transcript.md extracting text and tool calls from raw.jsonl
  if [[ -f "${out_dir}/raw.jsonl" ]]; then
    python3 - "${out_dir}/raw.jsonl" "${out_dir}/transcript.md" <<'PYEOF'
import json, sys
in_path, out_path = sys.argv[1], sys.argv[2]
lines_out = ["# Session Transcript\n"]

with open(in_path) as fh:
    for raw in fh:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        typ = obj.get("type", "")
        if typ == "assistant":
            for block in (obj.get("message", {}).get("content") or []):
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        lines_out.append(f"\n**Assistant:** {block['text']}\n")
                    elif block.get("type") == "tool_use":
                        lines_out.append(f"\n**Tool:** `{block.get('name')}` input={json.dumps(block.get('input',''))[:200]}\n")
        elif typ == "system":
            content = obj.get("message", {}).get("content", "")
            if content:
                lines_out.append(f"\n**System:** {str(content)[:200]}\n")

with open(out_path, "w") as f:
    f.writelines(lines_out)
PYEOF
  fi
}
