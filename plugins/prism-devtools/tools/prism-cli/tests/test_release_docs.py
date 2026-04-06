"""
AC-traced tests for PLAT-0000-release-documentation story.

Validates v2.5.0 release documentation BEFORE implementation (TDD RED).
All tests must FAIL with assertion errors until DEV writes the CHANGELOG entry
and bumps the version.

AC-1: CHANGELOG has [2.5.0] section dated 2026-03-02
AC-2: Five Added features documented in [2.5.0]
AC-3: Four Fixed items documented in [2.5.0]
AC-4: pyproject.toml has a version
AC-5: [2.5.0] appears before [2.4.0] in CHANGELOG
AC-6: ### Infrastructure subsection exists with pyproject.toml, .gitattributes, tests
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
PRISM_ROOT = REPO_ROOT / "plugins" / "prism-devtools"
CHANGELOG = PRISM_ROOT / "CHANGELOG.md"
PYPROJECT_TOML = REPO_ROOT / "pyproject.toml"


def _changelog_text() -> str:
    return CHANGELOG.read_text(encoding="utf-8")


def _version_section(version: str) -> str:
    """Extract the text between ## [version] and the next ## heading."""
    text = _changelog_text()
    pattern = rf"## \[{re.escape(version)}\].*?(?=\n## \[|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# AC-1: CHANGELOG has [2.5.0] section
# ---------------------------------------------------------------------------
class TestAC1_ChangelogHasV250Section:
    def test_ac1_changelog_file_exists(self):
        """
        AC-1: CHANGELOG.md file exists at expected path
        Requirement: Release documentation lives in CHANGELOG.md
        Expected: File exists at plugins/prism-devtools/CHANGELOG.md
        """
        assert CHANGELOG.exists(), f"CHANGELOG not found at {CHANGELOG}"

    def test_ac1_changelog_has_250_heading(self):
        """
        AC-1: CHANGELOG contains ## [2.5.0] section heading
        Requirement: New release entry must follow Keep a Changelog format
        Expected: '## [2.5.0]' present in CHANGELOG.md
        """
        text = _changelog_text()
        assert "## [2.5.0]" in text, "CHANGELOG missing ## [2.5.0] section"

    def test_ac1_250_section_has_date(self):
        """
        AC-1: [2.5.0] heading includes release date 2026-03-02
        Requirement: Keep a Changelog requires ## [version] - YYYY-MM-DD format
        Expected: '## [2.5.0] - 2026-03-02' found in CHANGELOG
        """
        text = _changelog_text()
        match = re.search(r"## \[2\.5\.0\] - (\d{4}-\d{2}-\d{2})", text)
        assert match, "CHANGELOG [2.5.0] heading missing date (format: YYYY-MM-DD)"
        assert match.group(1) == "2026-03-02", (
            f"Expected date 2026-03-02, got {match.group(1)}"
        )


# ---------------------------------------------------------------------------
# AC-2: Five Added features documented
# ---------------------------------------------------------------------------
class TestAC2_AddedFeaturesDocumented:
    def _section(self) -> str:
        return _version_section("2.5.0")

    def test_ac2_added_subsection_exists(self):
        """
        AC-2: [2.5.0] section contains ### Added subsection
        Requirement: New features must be categorised under ### Added
        Expected: '### Added' present in [2.5.0] section
        """
        section = self._section()
        assert "### Added" in section, "[2.5.0] missing ### Added subsection"

    def test_ac2_dashboard_tui_documented(self):
        """
        AC-2: PRISM Dashboard TUI documented in Added section
        Requirement: Textual live dashboard is a major new feature on this branch
        Expected: 'PRISM Dashboard TUI' or 'Dashboard TUI' in [2.5.0] Added
        """
        section = self._section()
        assert "PRISM Dashboard TUI" in section or "Dashboard TUI" in section, (
            "PRISM Dashboard TUI not documented in [2.5.0] Added"
        )

    def test_ac2_snapshot_mode_documented(self):
        """
        AC-2: CLI Snapshot mode documented in Added section
        Requirement: --snapshot ASCII output flag is a major new feature
        Expected: 'snapshot' (case-insensitive) in [2.5.0] Added
        """
        section = self._section()
        assert "snapshot" in section.lower(), (
            "CLI Snapshot mode not documented in [2.5.0] Added"
        )

    def test_ac2_prism_dashboard_command_documented(self):
        """
        AC-2: /prism-dashboard command documented in Added section
        Requirement: New slash command to launch TUI must be in release notes
        Expected: 'prism-dashboard' in [2.5.0] Added
        """
        section = self._section()
        assert "prism-dashboard" in section, (
            "/prism-dashboard command not documented in [2.5.0] Added"
        )

    def test_ac2_validate_cli_command_documented(self):
        """
        AC-2: /validate-cli command documented in Added section
        Requirement: New slash command for headless TUI validation must be in release notes
        Expected: 'validate-cli' in [2.5.0] Added
        """
        section = self._section()
        assert "validate-cli" in section, (
            "/validate-cli command not documented in [2.5.0] Added"
        )

    def test_ac2_activity_hook_documented(self):
        """
        AC-2: prism_activity_hook.py documented in Added section
        Requirement: New activity tracking hook is a new feature on this branch
        Expected: 'activity_hook' or 'activity hook' in [2.5.0] Added
        """
        section = self._section()
        assert "activity_hook" in section or "activity hook" in section.lower(), (
            "prism_activity_hook.py not documented in [2.5.0] Added"
        )


# ---------------------------------------------------------------------------
# AC-3: Four Fixed items documented
# ---------------------------------------------------------------------------
class TestAC3_FixedItemsDocumented:
    def _section(self) -> str:
        return _version_section("2.5.0")

    def test_ac3_fixed_subsection_exists(self):
        """
        AC-3: [2.5.0] section contains ### Fixed subsection
        Requirement: Bug fixes must be categorised under ### Fixed
        Expected: '### Fixed' present in [2.5.0] section
        """
        section = self._section()
        assert "### Fixed" in section, "[2.5.0] missing ### Fixed subsection"

    def test_ac3_plugin_root_fix_documented(self):
        """
        AC-3: Plugin root resolution fix documented in Fixed section
        Requirement: _find_plugin_root() sentinel-walk fix is a notable bug fix
        Expected: 'plugin root' or '_find_plugin_root' in [2.5.0] Fixed
        """
        section = self._section()
        assert "plugin root" in section.lower() or "_find_plugin_root" in section, (
            "Plugin root resolution fix not documented in [2.5.0] Fixed"
        )

    def test_ac3_precommit_gate_documented(self):
        """
        AC-3: Pre-commit gate installation documented in Fixed section
        Requirement: .git/hooks/pre-commit wiring was a missing infrastructure fix
        Expected: 'pre-commit' or 'precommit' in [2.5.0] Fixed
        """
        section = self._section()
        assert "pre-commit" in section.lower() or "precommit" in section.lower(), (
            "Pre-commit gate installation not documented in [2.5.0] Fixed"
        )

    def test_ac3_validate_all_fix_documented(self):
        """
        AC-3: validate-all repo-root path fix documented in Fixed section
        Requirement: 234 false-positive docs errors were a known bug, now fixed
        Expected: 'validate-all' or 'validate_all' in [2.5.0] Fixed
        """
        section = self._section()
        assert "validate-all" in section or "validate_all" in section, (
            "validate-all path fix not documented in [2.5.0] Fixed"
        )

    def test_ac3_stop_hook_session_fix_documented(self):
        """
        AC-3: Stop hook session detection lenience documented in Fixed section
        Requirement: Orphaned workflows got permanently stuck — now fixed
        Expected: 'stop hook' or 'session detection' in [2.5.0] Fixed
        """
        section = self._section()
        assert "stop hook" in section.lower() or "session detection" in section.lower(), (
            "Stop hook session detection fix not documented in [2.5.0] Fixed"
        )


# ---------------------------------------------------------------------------
# AC-4: pyproject.toml version exists
# ---------------------------------------------------------------------------
class TestAC4_PyprojectVersion:
    def test_ac4_pyproject_toml_exists(self):
        """
        AC-4: pyproject.toml exists at expected path
        Requirement: Version is signalled via pyproject.toml
        Expected: File exists at repo root
        """
        assert PYPROJECT_TOML.exists(), f"pyproject.toml not found at {PYPROJECT_TOML}"

    def test_ac4_pyproject_has_version(self):
        """
        AC-4: pyproject.toml has a version field
        Requirement: Version is tracked in pyproject.toml
        """
        content = PYPROJECT_TOML.read_text(encoding="utf-8")
        assert re.search(r'version\s*=\s*"[\d.]+"', content), (
            "pyproject.toml missing version field"
        )


# ---------------------------------------------------------------------------
# AC-5: [2.5.0] appears before [2.4.0] in CHANGELOG
# ---------------------------------------------------------------------------
class TestAC5_VersionOrdering:
    def test_ac5_250_appears_before_240(self):
        """
        AC-5: [2.5.0] section appears before [2.4.0] in file order
        Requirement: Newest release must be at the top of the CHANGELOG
        Expected: text.find('## [2.5.0]') < text.find('## [2.4.0]')
        """
        text = _changelog_text()
        pos_250 = text.find("## [2.5.0]")
        pos_240 = text.find("## [2.4.0]")
        assert pos_250 != -1, "## [2.5.0] not found in CHANGELOG"
        assert pos_240 != -1, "## [2.4.0] not found in CHANGELOG"
        assert pos_250 < pos_240, (
            "[2.5.0] section does not appear before [2.4.0] in CHANGELOG"
        )

    def test_ac5_250_is_latest_version(self):
        """
        AC-5: [3.11.1] is the first (topmost) version entry in CHANGELOG
        Requirement: Latest release must be at the very top of the version list
        Expected: First '## [X.Y.Z]' match in CHANGELOG is [3.11.1]
        """
        text = _changelog_text()
        first_version = re.search(r"## \[(\d+\.\d+\.\d+)\]", text)
        assert first_version, "No version headings found in CHANGELOG"
        assert first_version.group(1) == "3.11.1", (
            f"First version in CHANGELOG is '{first_version.group(1)}', "
            f"expected '3.11.1' (should be latest)"
        )


# ---------------------------------------------------------------------------
# AC-6: Infrastructure subsection documents tooling changes
# ---------------------------------------------------------------------------
class TestAC6_InfrastructureSubsection:
    def _section(self) -> str:
        return _version_section("2.5.0")

    def test_ac6_infrastructure_subsection_exists(self):
        """
        AC-6: [2.5.0] section contains ### Infrastructure subsection
        Requirement: Tooling and DX changes are documented separately from features
        Expected: '### Infrastructure' present in [2.5.0] section
        """
        section = self._section()
        assert "### Infrastructure" in section, (
            "[2.5.0] missing ### Infrastructure subsection"
        )

    def test_ac6_pyproject_toml_documented(self):
        """
        AC-6: pyproject.toml documented in Infrastructure subsection
        Requirement: New pytest config and pylint overrides are a tooling change
        Expected: 'pyproject.toml' in [2.5.0] Infrastructure
        """
        section = self._section()
        assert "pyproject.toml" in section, (
            "pyproject.toml not documented in [2.5.0] Infrastructure"
        )

    def test_ac6_gitattributes_documented(self):
        """
        AC-6: .gitattributes documented in Infrastructure subsection
        Requirement: LF enforcement for shell scripts prevents CRLF issues
        Expected: '.gitattributes' or 'gitattributes' in [2.5.0] Infrastructure
        """
        section = self._section()
        assert ".gitattributes" in section or "gitattributes" in section, (
            ".gitattributes not documented in [2.5.0] Infrastructure"
        )

    def test_ac6_test_suite_documented(self):
        """
        AC-6: Test suite size documented in Infrastructure subsection
        Requirement: 95 passing tests are a notable DX quality indicator
        Expected: 'test' with '95' or 'passing' or 'suite' in [2.5.0] Infrastructure
        """
        section = self._section()
        assert "test" in section.lower() and (
            "95" in section or "passing" in section.lower() or "suite" in section.lower()
        ), "Test suite coverage not documented in [2.5.0] Infrastructure"
