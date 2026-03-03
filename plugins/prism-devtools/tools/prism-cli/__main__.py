"""Entry point for the PRISM CLI Dashboard.

Usage:
    python plugins/prism-devtools/tools/prism-cli
    python plugins/prism-devtools/tools/prism-cli --path /your/project
"""

from __future__ import annotations

import argparse
import os
import sys

# The directory name "prism-cli" contains a hyphen, which is not a valid
# Python package identifier. Add this directory to sys.path so all modules
# can import each other with absolute (non-relative) imports.
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
if _PKG_DIR not in sys.path:
    sys.path.insert(0, _PKG_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PRISM Workflow Dashboard — live TUI monitor",
    )
    parser.add_argument(
        "--path",
        default=os.getcwd(),
        help="Working directory to monitor (default: cwd)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Poll interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Print ASCII snapshot and exit (no TUI)",
    )
    args = parser.parse_args()

    if args.snapshot:
        from pathlib import Path
        from snapshot import render_snapshot
        print(render_snapshot(Path(args.path)))
        return

    # Import here so argparse --help works without textual installed
    from app import PrismDashboard

    PrismDashboard(path=args.path, interval=args.interval).run()


if __name__ == "__main__":
    main()
