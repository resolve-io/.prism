# prism-harness

End-to-end test harness for `prism-devtools`. Runs the plugin against the sibling
`prism-test` project using `claude -p` headless with stream-json output, then asserts
on the results.

## Setup

```bash
cd plugins/prism-devtools/tests/harness
pip install -e .
```

This installs the `prism-harness` CLI entry point. You can also run without installing:

```bash
python3 -m prism_harness <command>
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PRISM_TEST_DIR` | Path to the `prism-test` project | Auto-detected as sibling of repo root |
| `PLUGIN_DIR` | Path to `prism-devtools` plugin root | Auto-detected as `../../` relative to harness |

## Usage

### List available tests

```bash
prism-harness list
```

### Run all tests

```bash
prism-harness run
```

### Run a filtered subset

```bash
prism-harness run session-start
prism-harness run brain
```

### Dry run (no claude invocations)

```bash
prism-harness run --dry-run
prism-harness run session-start --dry-run
```

### Override project paths

```bash
prism-harness run --prism-test-dir /path/to/prism-test --plugin-dir /path/to/prism-devtools
PRISM_TEST_DIR=/path/to/prism-test prism-harness run
```

### Show last results

```bash
prism-harness report
prism-harness report results/20260306-120000
```

### Re-analyze an existing results directory

```bash
prism-harness parse results/20260306-120000
```

Regenerates `transcript.md` from `raw.jsonl` and prints a per-test summary.

## Results Structure

Each `run` writes to a timestamped directory:

```
results/
  20260306-120000/
    test-session-start/
      raw.jsonl        # full stream-json output from claude
      summary.json     # pass/fail/assertion counts
      transcript.md    # rendered markdown transcript
    test-brain-bootstrap/
      ...
    harness-report.json  # aggregated PASS/FAIL/SKIP totals
  last -> 20260306-120000  # symlink to most recent run
```

## Tests

| Test | What it validates |
|------|------------------|
| `test-session-start` | SessionStart hook fires; MEMORY.md created; Brain referenced in system events |
| `test-brain-bootstrap` | `.prism/brain/` created; `brain.db` non-empty after session |
| `test-skill-discovery` | BYOS skills discovered; invalid skills filtered; `/calculator multiply` works |
| `test-prism-loop` | `prism-loop` skill referenced; workflow content produced; state file created |
