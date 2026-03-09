#!/usr/bin/env python3
"""
Bump prism-devtools plugin version, update CHANGELOG, create git tag, commit, and push.

Usage:
    python version_bump.py patch          # 3.5.0 → 3.5.1 (bump + commit + push)
    python version_bump.py minor          # 3.5.0 → 3.6.0 (bump + commit + push)
    python version_bump.py major          # 3.5.0 → 4.0.0 (bump + commit + push)
    python version_bump.py status         # Show current version and tag info
    python version_bump.py tag            # Create git tag for current version
    python version_bump.py sync-changelog # Add CHANGELOG stub for current version

    Options:
        --no-push    Skip the git push (commit locally only)
        --ticket XX  Use PLAT-XX in commit message (default: PLAT-0000)

Exit codes:
    0 = success
    1 = usage/validation error
    2 = file system error
"""
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


def _find_plugin_root() -> Path:
    """Walk up from script to find the prism-devtools plugin root."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        plugin_json = current / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            return current
        current = current.parent
    # Fallback: relative from known script location
    fallback = Path(__file__).resolve().parent.parent.parent
    if (fallback / ".claude-plugin" / "plugin.json").exists():
        return fallback
    print("ERROR: Could not find plugin root with .claude-plugin/plugin.json", file=sys.stderr)
    sys.exit(2)


PLUGIN_ROOT = _find_plugin_root()
PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
CHANGELOG = PLUGIN_ROOT / "CHANGELOG.md"
RELEASE_TESTS = PLUGIN_ROOT / "tools" / "prism-cli" / "tests" / "test_release_docs.py"


def read_version() -> str:
    """Read current version from plugin.json."""
    data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    return data.get("version", "0.0.0")


def write_version(new_version: str) -> None:
    """Update version in plugin.json, preserving formatting."""
    data = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    data["version"] = new_version
    PLUGIN_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def bump(current: str, part: str) -> str:
    """Compute new semver version."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", current)
    if not match:
        print(f"ERROR: Invalid semver: {current}", file=sys.stderr)
        sys.exit(1)
    major, minor, patch = int(match[1]), int(match[2]), int(match[3])
    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"ERROR: Unknown bump type: {part}. Use major/minor/patch.", file=sys.stderr)
        sys.exit(1)


def update_changelog(new_version: str) -> bool:
    """Prepend a new version section to CHANGELOG.md. Returns True if updated."""
    if not CHANGELOG.exists():
        print(f"WARNING: CHANGELOG.md not found at {CHANGELOG}", file=sys.stderr)
        return False

    text = CHANGELOG.read_text(encoding="utf-8")

    # Check if this version already has a section
    if f"## [{new_version}]" in text:
        print(f"  CHANGELOG already has [{new_version}] section, skipping.")
        return False

    today = date.today().isoformat()
    new_section = f"## [{new_version}] - {today}\n\n### Added\n\n### Fixed\n\n"

    # Insert after the header lines (before first ## [x.y.z] section)
    first_version = re.search(r"^## \[\d+\.\d+\.\d+\]", text, re.MULTILINE)
    if first_version:
        insert_pos = first_version.start()
        text = text[:insert_pos] + new_section + text[insert_pos:]
    else:
        # No existing versions, append after header
        text += "\n" + new_section

    CHANGELOG.write_text(text, encoding="utf-8")
    return True


def update_release_tests(old_version: str, new_version: str) -> bool:
    """Update version assertions in test_release_docs.py. Returns True if updated."""
    if not RELEASE_TESTS.exists():
        print(f"  WARNING: test_release_docs.py not found at {RELEASE_TESTS}", file=sys.stderr)
        return False

    text = RELEASE_TESTS.read_text(encoding="utf-8")
    original = text

    # Update AC-4: plugin.json version assertion
    # Matches patterns like: == "3.7.0"  and  expected '3.7.0'
    text = re.sub(
        r'(== ["\'])' + re.escape(old_version) + r'(["\'])',
        rf'\g<1>{new_version}\g<2>',
        text,
    )
    text = re.sub(
        r"(expected ')(" + re.escape(old_version) + r")(')",
        rf"\g<1>{new_version}\g<3>",
        text,
    )

    # Update AC-5: latest CHANGELOG version assertion
    # Matches: f"expected '3.7.0' (should be latest)"
    text = re.sub(
        r'(expected ["\'])' + re.escape(old_version) + r"([\"'] \(should be latest\))",
        rf"\g<1>{new_version}\g<2>",
        text,
    )

    # Update version references in docstrings (e.g. "Version bump from X → Y")
    text = re.sub(
        r"(Version bump from )\S+ → \S+( for)",
        rf"\g<1>{old_version} → {new_version}\g<2>",
        text,
    )

    if text == original:
        print(f"  test_release_docs.py: no version references to update")
        return False

    RELEASE_TESTS.write_text(text, encoding="utf-8")
    print(f"  Updated test_release_docs.py assertions: {old_version} → {new_version}")
    return True


def create_tag(version: str) -> bool:
    """Create an annotated git tag if it doesn't exist."""
    tag_name = f"v{version}"
    # Check if tag exists
    result = subprocess.run(
        ["git", "tag", "-l", tag_name],
        capture_output=True, text=True, cwd=PLUGIN_ROOT,
    )
    if tag_name in result.stdout.strip().split("\n"):
        print(f"  Tag {tag_name} already exists, skipping.")
        return False

    subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
        check=True, cwd=PLUGIN_ROOT,
    )
    print(f"  Created tag: {tag_name}")
    return True


def git_commit_and_push(old_version: str, new_version: str, ticket: str, push: bool) -> None:
    """Stage version files, commit, and push to origin with tags."""
    # Find repo root (git toplevel)
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=PLUGIN_ROOT,
    )
    repo_root = result.stdout.strip()

    # Stage the version-related files
    files_to_stage = [str(PLUGIN_JSON)]
    if CHANGELOG.exists():
        files_to_stage.append(str(CHANGELOG))
    if RELEASE_TESTS.exists():
        files_to_stage.append(str(RELEASE_TESTS))

    subprocess.run(
        ["git", "add"] + files_to_stage,
        check=True, cwd=repo_root,
    )
    print(f"  Staged version files")

    # Commit
    msg = f"{ticket} Bump version {old_version} → {new_version}"
    subprocess.run(
        ["git", "commit", "-m", msg],
        check=True, cwd=repo_root,
    )
    print(f"  Committed: {msg}")

    # Move tag to the commit (tag was created before commit, so re-tag)
    tag_name = f"v{new_version}"
    subprocess.run(
        ["git", "tag", "-d", tag_name],
        capture_output=True, cwd=repo_root,
    )
    subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {new_version}"],
        check=True, cwd=repo_root,
    )
    print(f"  Re-tagged {tag_name} at commit")

    # Push
    if push:
        subprocess.run(
            ["git", "push", "origin", "main", "--tags"],
            check=True, cwd=repo_root,
        )
        print(f"  Pushed to origin main with tags")
    else:
        print(f"  Skipped push (--no-push). Run: git push origin main --tags")


def git_status() -> None:
    """Show version status: plugin.json, CHANGELOG, and tags."""
    current = read_version()
    print(f"  plugin.json version: {current}")

    # Latest CHANGELOG version
    if CHANGELOG.exists():
        text = CHANGELOG.read_text(encoding="utf-8")
        match = re.search(r"## \[(\d+\.\d+\.\d+)\]", text)
        changelog_ver = match.group(1) if match else "none"
        print(f"  CHANGELOG latest:    {changelog_ver}")
        if changelog_ver != current:
            print(f"  ⚠ CHANGELOG is out of sync (expected {current})")
    else:
        print("  CHANGELOG: not found")

    # Latest git tag
    result = subprocess.run(
        ["git", "tag", "--sort=-v:refname"],
        capture_output=True, text=True, cwd=PLUGIN_ROOT,
    )
    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
    latest_tag = tags[0] if tags else "none"
    print(f"  Latest git tag:      {latest_tag}")
    if latest_tag != f"v{current}":
        print(f"  ⚠ Git tag is out of sync (expected v{current})")

    # Commits since latest tag
    if tags:
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{latest_tag}..HEAD"],
            capture_output=True, text=True, cwd=PLUGIN_ROOT,
        )
        count = result.stdout.strip()
        print(f"  Commits since tag:   {count}")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: version_bump.py <major|minor|patch|status|tag|sync-changelog> [--no-push] [--ticket PLAT-XXXX]")
        sys.exit(1)

    action = args[0].lower()
    push = "--no-push" not in args
    ticket = "PLAT-0000"
    if "--ticket" in args:
        idx = args.index("--ticket")
        if idx + 1 < len(args):
            ticket = args[idx + 1]

    if action == "status":
        git_status()
        return

    current = read_version()

    if action == "tag":
        create_tag(current)
        return

    if action == "sync-changelog":
        if update_changelog(current):
            print(f"  Added CHANGELOG section for [{current}]")
        return

    if action not in ("major", "minor", "patch"):
        print(f"ERROR: Unknown action: {action}. Use major/minor/patch/status/tag/sync-changelog.",
              file=sys.stderr)
        sys.exit(1)

    new_version = bump(current, action)
    print(f"  Bumping: {current} → {new_version}")

    write_version(new_version)
    print(f"  Updated plugin.json")

    if update_changelog(new_version):
        print(f"  Updated CHANGELOG.md with [{new_version}] section")

    update_release_tests(current, new_version)

    create_tag(new_version)
    git_commit_and_push(current, new_version, ticket, push)

    print(f"\n  ✓ Version {new_version} released")


if __name__ == "__main__":
    main()
