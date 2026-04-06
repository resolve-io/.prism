#!/usr/bin/env python3
"""PreToolUse hook — convention enforcement on writes.

Fires before Write/Edit tool calls. Advisory only (never blocks).
- Reads conventions directly from the JSONL file on the shared volume
- Warns if known anti-patterns may be present in proposed content

Reads the conventions.jsonl file that the MCP service writes to via
the Docker volume mount.  No HTTP call needed — same backing file,
zero network latency.
"""

import io
import json
import os
import re
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# File extension → domain mapping
_EXT_DOMAIN = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".cs": "dotnet",
    ".go": "go",
    ".rs": "rust",
    ".md": "docs",
    ".yaml": "config",
    ".yml": "config",
    ".json": "config",
    ".toml": "config",
}


def _get_domain(file_path: str) -> str:
    """Map file extension to domain for convention lookup."""
    ext = Path(file_path).suffix.lower()
    return _EXT_DOMAIN.get(ext, "general")


def _find_conventions_jsonl() -> Path | None:
    """Locate conventions.jsonl via the Docker volume mount.

    Walks up from this hook's directory to find the .prism project root,
    then resolves the data path.  Supports both the standard layout
    and a PRISM_DATA_DIR env override.
    """
    # Allow explicit override (e.g. in CI or non-standard layouts)
    override = os.environ.get("PRISM_DATA_DIR")
    project = os.environ.get("PRISM_PROJECT", "prism")
    if override:
        p = Path(override) / "projects" / project / "mulch" / "expertise" / "conventions.jsonl"
        return p if p.exists() else None

    # Walk up from hook location to find services/prism-service/data
    hook_dir = Path(__file__).resolve().parent
    root = hook_dir
    for _ in range(6):  # max 6 levels up
        candidate = root / "services" / "prism-service" / "data" / "projects" / project / "mulch" / "expertise" / "conventions.jsonl"
        if candidate.exists():
            return candidate
        root = root.parent
    return None


def _recall_conventions(domain: str) -> list[dict]:
    """Read conventions directly from the JSONL file on the shared volume.

    The MCP service writes to this file via memory_store; the Docker
    volume mount makes it accessible on the host.  Reading it directly
    avoids the 600ms HTTP round-trip per write.
    """
    try:
        jsonl_path = _find_conventions_jsonl()
        if not jsonl_path:
            return []

        entries = []
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if entry.get("status") == "active" and not entry.get("invalid_at"):
                entries.append(entry)
        return entries
    except Exception:
        pass
    return []


def _check_conventions(content: str, conventions: list[dict]) -> list[str]:
    """Check content against recalled conventions. Returns warnings."""
    warnings = []
    content_lower = content.lower()

    for conv in conventions:
        if not isinstance(conv, dict):
            continue

        name = conv.get("name", "")
        desc = conv.get("description", "")

        # Look for "do not" / "never" / "avoid" patterns in convention description
        # and try to extract what to check for
        if not desc:
            continue

        # Extract anti-patterns: capture multi-word phrases after never/avoid/don't
        # e.g., "Never use inline PowerShell" -> ["inline powershell"]
        # e.g., "Never use -ErrorAction SilentlyContinue" -> ["erroraction silentlycontinue"]
        anti_patterns = []
        for match in re.finditer(
            r'(?:never|do not|don\'t|avoid|prohibited)\s+(?:use\s+)?(.+?)(?:\.|,|;|\s+for\b|\s+with\b|\s+in\b|\s+when\b|$)',
            desc,
            re.IGNORECASE,
        ):
            phrase = match.group(1).strip().lower()
            # Clean up: remove quotes, backticks, leading dashes
            phrase = re.sub(r'[`"\'\-]', ' ', phrase).strip()
            words = [w for w in phrase.split() if len(w) > 2]
            if words:
                anti_patterns.extend(words[:3])  # Take up to 3 keywords

        # Deduplicate and skip generic words
        skip_words = {"use", "the", "any", "all", "for", "and", "not", "with"}
        anti_patterns = list(dict.fromkeys(
            p for p in anti_patterns if p not in skip_words
        ))

        for pattern in anti_patterns:
            if re.search(rf'(?i)\b{re.escape(pattern)}\b', content_lower):
                warnings.append(
                    f"Convention '{name}': {desc[:120]}"
                )
                break  # One warning per convention

    return warnings


def main():
    file_path = os.environ.get("TOOL_PARAMS_file_path", "")
    if not file_path:
        sys.exit(0)

    # For Edit, the content is in old_string/new_string; for Write, it's in content
    content = os.environ.get("TOOL_PARAMS_content", "")
    new_string = os.environ.get("TOOL_PARAMS_new_string", "")
    check_content = content or new_string

    if not check_content:
        sys.exit(0)

    domain = _get_domain(file_path)
    conventions = _recall_conventions(domain)

    if not conventions:
        sys.exit(0)

    warnings = _check_conventions(check_content, conventions)

    if warnings:
        print(f"Convention check for {os.path.basename(file_path)}:", file=sys.stderr)
        for w in warnings[:3]:  # Cap at 3 warnings
            print(f"  - {w}", file=sys.stderr)

    # Always allow the write (advisory only)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Never block on hook failure
        sys.exit(0)
