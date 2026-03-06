#!/usr/bin/env bash
# lib/scaffold.sh — Test project state management for the prism-devtools harness.
#
# Manages two scaffold modes:
#   greenfield — a fresh working directory (dotnet new blazor or minimal git repo)
#   brownfield — the cultivated prism-test project reset to baseline state
#
# Exports:
#   TEST_PROJECT_DIR — active working directory for the current test
#   scaffold_reset        — reset prism-test to baseline (remove generated files)
#   scaffold_greenfield   — create a fresh temporary project directory
#   scaffold_brownfield   — use prism-test as-is (cultivated fixtures intact)
#   scaffold_teardown     — clean up temp dirs created by scaffold_greenfield

# Guard: PRISM_TEST_DIR must be set by run-harness.sh
: "${PRISM_TEST_DIR:?PRISM_TEST_DIR must be set before sourcing scaffold.sh}"

# Active project dir used by run_claude() and assertion helpers.
# Defaults to PRISM_TEST_DIR; overridden by scaffold_greenfield.
TEST_PROJECT_DIR="$PRISM_TEST_DIR"

# Track temp dirs created by scaffold_greenfield for cleanup
_SCAFFOLD_TEMP_DIRS=()

# ---------------------------------------------------------------------------
# scaffold_reset — reset prism-test to harness baseline
#
# Removes generated project files while preserving .claude/ fixtures and .git/.
# Safe to call between every test. Mirrors the canonical reset from CLAUDE.md:
#   git clean -fd --exclude=.claude
# ---------------------------------------------------------------------------
scaffold_reset() {
  TEST_PROJECT_DIR="$PRISM_TEST_DIR"

  if [[ ! -d "$PRISM_TEST_DIR/.git" ]]; then
    log_warn "scaffold_reset: $PRISM_TEST_DIR is not a git repo — skipping clean"
    return 0
  fi

  (
    cd "$PRISM_TEST_DIR"
    git clean -fd --exclude=.claude -q 2>/dev/null || true
  )
  rm -rf "$PRISM_TEST_DIR/.prism"

  log_info "Scaffold reset: prism-test baseline restored"
}

# ---------------------------------------------------------------------------
# scaffold_greenfield — create a fresh isolated project directory
#
# Attempts to create a minimal project via:
#   1. dotnet new blazor (if dotnet CLI available)
#   2. Fallback: a plain git repo with a minimal pyproject.toml
#
# Sets TEST_PROJECT_DIR to the new temp directory.
# ---------------------------------------------------------------------------
scaffold_greenfield() {
  local tmpdir
  tmpdir="$(mktemp -d /tmp/prism-harness-greenfield-XXXXXX)"
  _SCAFFOLD_TEMP_DIRS+=("$tmpdir")
  TEST_PROJECT_DIR="$tmpdir"

  # Initialize as a git repo so session-start hook can anchor to a root
  git -C "$tmpdir" init -q
  git -C "$tmpdir" commit --allow-empty -q -m "initial" \
    --author="test <test@harness>" 2>/dev/null || true

  if command -v dotnet &>/dev/null; then
    log_info "Greenfield: dotnet blazor in $tmpdir"
    dotnet new blazor -o "$tmpdir" --force -q 2>/dev/null \
      || log_warn "dotnet new blazor failed; using minimal fallback"
  else
    log_info "Greenfield: minimal project in $tmpdir (dotnet not available)"
    echo '[tool.pytest.ini_options]' > "$tmpdir/pyproject.toml"
    echo 'testpaths = ["tests"]' >> "$tmpdir/pyproject.toml"
  fi

  log_info "Scaffold greenfield: TEST_PROJECT_DIR=$TEST_PROJECT_DIR"
}

# ---------------------------------------------------------------------------
# scaffold_brownfield — use the cultivated prism-test project as-is
#
# Resets to baseline first, then optionally checks out a named branch/tag.
# Usage: scaffold_brownfield [git_ref]
# ---------------------------------------------------------------------------
scaffold_brownfield() {
  local git_ref="${1:-}"

  scaffold_reset

  if [[ -n "$git_ref" && -d "$PRISM_TEST_DIR/.git" ]]; then
    log_info "Brownfield: checking out $git_ref in $PRISM_TEST_DIR"
    (cd "$PRISM_TEST_DIR" && git checkout -q "$git_ref" 2>/dev/null) \
      || log_warn "git checkout $git_ref failed — proceeding with current state"
  fi

  TEST_PROJECT_DIR="$PRISM_TEST_DIR"
  log_info "Scaffold brownfield: TEST_PROJECT_DIR=$TEST_PROJECT_DIR"
}

# ---------------------------------------------------------------------------
# scaffold_teardown — remove temp directories created by scaffold_greenfield
# ---------------------------------------------------------------------------
scaffold_teardown() {
  for d in "${_SCAFFOLD_TEMP_DIRS[@]:-}"; do
    if [[ -n "$d" && -d "$d" && "$d" == /tmp/prism-harness-* ]]; then
      rm -rf "$d"
      log_info "Scaffold teardown: removed $d"
    fi
  done
  _SCAFFOLD_TEMP_DIRS=()
}
