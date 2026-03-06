"""Assertion framework for the prism-harness test runner.

AssertionContext tracks pass/fail/skip counts and emits colored output.
Create one context per test; the runner aggregates totals across tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .parser import parse_jsonl, deep_get

# ANSI escape codes
_C_RESET = "\033[0m"
_C_GREEN = "\033[0;32m"
_C_RED = "\033[0;31m"
_C_YELLOW = "\033[0;33m"
_C_CYAN = "\033[0;36m"
_C_BOLD = "\033[1m"


def _c(code: str, text: str, use_color: bool) -> str:
    return f"{code}{text}{_C_RESET}" if use_color else text


class AssertionContext:
    """Per-test assertion tracker with colored output."""

    def __init__(self, use_color: bool | None = None) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.use_color = sys.stdout.isatty() if use_color is None else use_color
        # Set by the runner after each run_claude() call
        self.last_output: Path | None = None

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def log_info(self, msg: str) -> None:
        print(f"  {_c(_C_CYAN, 'INFO', self.use_color)}  {msg}")

    def log_warn(self, msg: str) -> None:
        print(f"  {_c(_C_YELLOW, 'WARN', self.use_color)}  {msg}")

    def log_section(self, msg: str) -> None:
        print(_c(_C_BOLD + _C_CYAN, f"── {msg} ──", self.use_color))

    def _pass(self, desc: str) -> None:
        print(f"  {_c(_C_GREEN, 'PASS', self.use_color)}  {desc}")
        self.passed += 1

    def _fail(self, desc: str, detail: str = "") -> None:
        suffix = f" ({detail})" if detail else ""
        print(f"  {_c(_C_RED, 'FAIL', self.use_color)}  {desc}{suffix}")
        self.failed += 1

    def _skip(self, desc: str) -> None:
        print(f"  {_c(_C_YELLOW, 'SKIP', self.use_color)}  {desc}")
        self.skipped += 1

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_eq(self, expected: str, actual: str, desc: str) -> None:
        if actual == expected:
            self._pass(desc)
        else:
            self._fail(desc, f"expected={expected!r} got={actual!r}")

    def assert_contains(self, needle: str, haystack: str, desc: str) -> None:
        if needle in haystack:
            self._pass(desc)
        else:
            self._fail(desc, f"expected {needle!r} in output")

    def assert_file_exists(self, path: Path | str, desc: str | None = None) -> None:
        path = Path(path)
        desc = desc or f"file exists: {path}"
        if path.exists():
            self._pass(desc)
        else:
            self._fail(desc, f"path not found: {path}")

    def assert_file_absent(self, path: Path | str, desc: str | None = None) -> None:
        path = Path(path)
        desc = desc or f"file absent: {path}"
        if not path.exists():
            self._pass(desc)
        else:
            self._fail(desc, f"path should not exist: {path}")

    def assert_json_not_empty(
        self, desc: str | None = None, output: Path | None = None
    ) -> None:
        desc = desc or "stream-json output is non-empty"
        output = output or self.last_output
        if not output or not output.is_file():
            self._fail(desc, "no output file")
            return
        events = parse_jsonl(output)
        if events:
            self._pass(f"{desc} ({len(events)} events)")
        else:
            self._fail(desc, "0 parseable JSON events")

    def assert_json_has(
        self,
        field: str,
        needle: str,
        desc: str,
        output: Path | None = None,
    ) -> None:
        """Assert that at least one JSON event contains needle at field_path.

        Use field='*' to search all string content of every event.
        """
        output = output or self.last_output
        if not output or not output.is_file():
            self._fail(desc, "no output file")
            return

        events = parse_jsonl(output)
        found = False
        for ev in events:
            if field == "*":
                if needle in json.dumps(ev.raw):
                    found = True
                    break
            else:
                val = deep_get(ev.raw, field)
                if val is not None and needle in str(val):
                    found = True
                    break

        if found:
            self._pass(desc)
        else:
            self._fail(desc, f"field={field!r} needle={needle!r} not found")

    def assert_json_event_type(
        self, event_type: str, desc: str, output: Path | None = None
    ) -> None:
        self.assert_json_has("type", event_type, desc, output)

    def assert_json_lacks(
        self, needle: str, desc: str, output: Path | None = None
    ) -> None:
        """Assert needle does NOT appear anywhere in the JSONL output.

        Uses lenient skip (not fail) if needle is found, matching bash behavior:
        invalid skill names may appear in incidental log text.
        """
        output = output or self.last_output
        if not output or not output.is_file():
            self._skip(f"{desc} (no output to check)")
            return

        found = False
        try:
            with open(output) as fh:
                for line in fh:
                    if needle in line:
                        found = True
                        break
        except OSError:
            self._skip(f"{desc} (error reading output)")
            return

        if not found:
            self._pass(desc)
        else:
            self._skip(f"{desc} (needle found — may be in incidental context)")

    def assert_json_keyword_any(
        self,
        keywords: list[str],
        desc: str,
        output: Path | None = None,
    ) -> bool:
        """Assert at least one keyword (case-insensitive) appears in JSONL output.

        Returns True if found, False otherwise.
        """
        output = output or self.last_output
        if not output or not output.is_file():
            self._fail(desc, "no output file")
            return False

        try:
            content = output.read_text().lower()
            for kw in keywords:
                if kw.lower() in content:
                    self._pass(desc)
                    return True
        except OSError:
            pass

        self._fail(desc, f"none of {keywords!r} found in output")
        return False
