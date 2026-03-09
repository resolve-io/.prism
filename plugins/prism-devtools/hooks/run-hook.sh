#!/bin/sh
# Cross-platform Python resolver for PRISM hooks.
# Finds python3 or python, then executes the given hook script.
PY=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)
exec "$PY" "$@"
