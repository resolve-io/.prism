#!/usr/bin/env python3
"""
PRISM Documentation Validation Script

Validates PRISM system for optimal Claude Code feature usage and progressive disclosure:
1. Claude Code Features: Skills, agents, commands, hooks, MCP integration
2. Progressive Disclosure: Hierarchical documentation (Level 0→1→2→3+)
3. Cross-Reference Integrity: All markdown links resolve correctly

Following PRISM principles:
- Predictability: Structured validation with consistent rules
- Resilience: Robust error handling and validation
- Intentionality: Clear, purposeful validation logic
- Sustainability: Maintainable and extensible architecture
- Maintainability: Modular design with clear separation of concerns
"""

import os
import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import argparse
from collections import deque

# Token counting for skill-builder pattern validation (Story-002)
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    print("Warning: tiktoken not installed. Token budget validation will be skipped.", file=sys.stderr)
    print("Install with: pip install -r requirements.txt", file=sys.stderr)


class Severity(Enum):
    """Issue severity levels"""
    CRITICAL = "Critical"
    WARNING = "Warning"
    INFO = "Info"


class Category(Enum):
    """Validation category types"""
    CROSS_REFERENCE = "cross_reference"
    PROGRESSIVE_DISCLOSURE = "progressive_disclosure"
    STRUCTURE = "structure"
    METADATA = "metadata"
    CLAUDE_CODE_FEATURES = "claude_code_features"


@dataclass
class Heading:
    """Represents a markdown heading"""
    level: int
    text: str
    anchor: str
    line_number: int
    children: List['Heading'] = field(default_factory=list)


@dataclass
class Link:
    """Represents a markdown link"""
    text: str
    target: str
    anchor: Optional[str]
    line_number: int
    is_external: bool


@dataclass
class FileNode:
    """Represents a documentation file in the graph"""
    path: Path
    relative_path: str
    file_type: str  # 'markdown' or 'yaml'
    headings: List[Heading] = field(default_factory=list)
    internal_links: List[Link] = field(default_factory=list)
    external_links: List[Link] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    content_lines: List[str] = field(default_factory=list)
    max_heading_depth: int = 0
    has_toc: bool = False
    has_details_summary: bool = False


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    file: str
    line: Optional[int]
    category: Category
    severity: Severity
    rule_id: str
    message: str
    fix_guidance: str


@dataclass
class ValidationReport:
    """Complete validation report"""
    timestamp: datetime
    total_files: int
    files_checked: int
    issues: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, any] = field(default_factory=dict)

    @property
    def coverage_percentage(self) -> float:
        """Calculate validation coverage"""
        if self.total_files == 0:
            return 0.0
        return (self.files_checked / self.total_files) * 100

    @property
    def issues_by_severity(self) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {s.value: 0 for s in Severity}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts

    @property
    def issues_by_category(self) -> Dict[str, int]:
        """Count issues by category"""
        counts = {c.value: 0 for c in Category}
        for issue in self.issues:
            counts[issue.category.value] += 1
        return counts


class DocumentationScanner:
    """
    Scans and parses PRISM documentation files

    PRISM Principle: Intentionality - Clear, single-purpose scanner
    """

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.files: Dict[str, FileNode] = {}

    def scan(self) -> Dict[str, FileNode]:
        """Recursively scan directory for markdown and YAML files"""
        for file_path in self.root_path.rglob('*'):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix not in ['.md', '.yaml', '.yml']:
                continue

            relative_path = str(file_path.relative_to(self.root_path)).replace('\\', '/')

            # Determine file type
            file_type = 'markdown' if suffix == '.md' else 'yaml'

            # Create FileNode
            file_node = FileNode(
                path=file_path,
                relative_path=relative_path,
                file_type=file_type
            )

            # Parse file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_node.content_lines = f.readlines()

                if file_type == 'markdown':
                    self._parse_markdown(file_node)
                elif file_type == 'yaml':
                    self._parse_yaml(file_node)

            except Exception as e:
                print(f"Warning: Could not read {relative_path}: {e}", file=sys.stderr)
                continue

            self.files[relative_path] = file_node

        return self.files

    def _parse_markdown(self, file_node: FileNode):
        """Parse markdown file to extract headings, links, and features"""
        heading_stack: List[Heading] = []
        max_depth = 0

        content = ''.join(file_node.content_lines)

        # Check for progressive disclosure features
        file_node.has_details_summary = '<details>' in content.lower() and '<summary>' in content.lower()
        file_node.has_toc = bool(re.search(r'##\s+Table of Contents', content, re.IGNORECASE))

        for line_num, line in enumerate(file_node.content_lines, start=1):
            # Extract headings
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                anchor = self._generate_anchor(text)

                max_depth = max(max_depth, level)

                heading = Heading(
                    level=level,
                    text=text,
                    anchor=anchor,
                    line_number=line_num
                )

                # Build hierarchy
                while heading_stack and heading_stack[-1].level >= level:
                    heading_stack.pop()

                if heading_stack:
                    heading_stack[-1].children.append(heading)
                else:
                    file_node.headings.append(heading)

                heading_stack.append(heading)

            # Extract links: [text](target) or [text](target#anchor)
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            for match in re.finditer(link_pattern, line):
                text = match.group(1)
                target = match.group(2)

                # Check if external link
                is_external = target.startswith(('http://', 'https://', 'mailto:'))

                # Parse anchor if present
                anchor = None
                if '#' in target and not is_external:
                    target, anchor = target.split('#', 1)

                link = Link(
                    text=text,
                    target=target,
                    anchor=anchor,
                    line_number=line_num,
                    is_external=is_external
                )

                if is_external:
                    file_node.external_links.append(link)
                else:
                    file_node.internal_links.append(link)

        file_node.max_heading_depth = max_depth

    def _parse_yaml(self, file_node: FileNode):
        """Parse YAML file for basic structure"""
        # Basic YAML parsing - could be enhanced with yaml library
        pass

    @staticmethod
    def _generate_anchor(heading_text: str) -> str:
        """Generate GitHub-style anchor from heading text"""
        anchor = heading_text.lower()
        anchor = re.sub(r'[^\w\s-]', '', anchor)
        anchor = re.sub(r'[\s_]+', '-', anchor)
        anchor = anchor.strip('-')
        return anchor


class TokenCountingUtilities:
    """
    Token counting utilities for skill-builder pattern validation

    PRISM Principle: Resilience - Robust token counting with graceful fallback
    Story-002: Hierarchical Progressive Disclosure Pattern Validation
    """

    @staticmethod
    def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
        """
        Count tokens using OpenAI's tiktoken library (Claude-compatible)

        Args:
            text: Text to count tokens in
            encoding_name: Encoding to use (default: cl100k_base for Claude/GPT-4)

        Returns:
            Token count, or 0 if tiktoken not available
        """
        if not TIKTOKEN_AVAILABLE:
            return 0

        try:
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
        except Exception as e:
            print(f"Warning: Token counting failed: {e}", file=sys.stderr)
            return 0

    @staticmethod
    def extract_yaml_frontmatter(content_lines: List[str]) -> str:
        """
        Extract YAML frontmatter from markdown file (between --- markers)

        Args:
            content_lines: Lines of markdown content

        Returns:
            YAML frontmatter content as string
        """
        if not content_lines or not content_lines[0].strip().startswith('---'):
            return ""

        yaml_lines = []
        in_yaml = False

        for line in content_lines:
            if line.strip() == '---':
                if not in_yaml:
                    in_yaml = True
                    continue
                else:
                    # Found closing marker
                    break
            elif in_yaml:
                yaml_lines.append(line)

        return ''.join(yaml_lines)

    @staticmethod
    def extract_markdown_body(content_lines: List[str]) -> str:
        """
        Extract markdown body from file (excluding YAML frontmatter)

        Args:
            content_lines: Lines of markdown content

        Returns:
            Markdown body content as string
        """
        if not content_lines:
            return ""

        # Skip YAML frontmatter if present
        start_index = 0
        if content_lines[0].strip().startswith('---'):
            # Find closing ---
            for i, line in enumerate(content_lines[1:], start=1):
                if line.strip() == '---':
                    start_index = i + 1
                    break

        return ''.join(content_lines[start_index:])


class ClaudeCodeFeatureValidator:
    """
    Validates proper usage of Claude Code features

    PRISM Principle: Intentionality - Validate PRISM's effective use of Claude Code
    """

    def __init__(self, files: Dict[str, FileNode], root_path: Path):
        self.files = files
        self.root_path = root_path
        self.issues: List[ValidationIssue] = []

    def validate(self) -> List[ValidationIssue]:
        """Validate Claude Code feature usage"""
        self._validate_agent_structure()
        self._validate_command_structure()
        self._validate_skills_structure()
        self._validate_settings_file()
        return self.issues

    def _validate_agent_structure(self):
        """Validate .claude/agents/ structure"""
        agents_dir = self.root_path / '.claude' / 'agents'

        if not agents_dir.exists():
            self.issues.append(ValidationIssue(
                file=".claude/agents",
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.CRITICAL,
                rule_id="CC001",
                message="Missing .claude/agents directory - Claude Code agents not configured",
                fix_guidance="Create .claude/agents/ directory and define sub-agents"
            ))
            return

        # Find all agent files
        agent_files = list(agents_dir.glob('*.md'))

        if not agent_files:
            self.issues.append(ValidationIssue(
                file=".claude/agents",
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.WARNING,
                rule_id="CC002",
                message="No agent files found in .claude/agents/",
                fix_guidance="Define sub-agents for specialized tasks"
            ))
        else:
            # Validate each agent file has proper structure
            for agent_file in agent_files:
                rel_path = str(agent_file.relative_to(self.root_path))
                if rel_path in self.files:
                    self._validate_agent_file(self.files[rel_path])

    def _validate_agent_file(self, file_node: FileNode):
        """Validate individual agent file structure"""
        content = ''.join(file_node.content_lines)

        # Check for required agent components
        required_sections = ['Purpose', 'Tools', 'Prompt']
        missing_sections = []

        for section in required_sections:
            if section.lower() not in content.lower():
                missing_sections.append(section)

        if missing_sections:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.WARNING,
                rule_id="CC003",
                message=f"Agent file missing recommended sections: {', '.join(missing_sections)}",
                fix_guidance="Add missing sections to improve agent clarity"
            ))

    def _validate_command_structure(self):
        """Validate commands/ directory structure"""
        commands_dir = self.root_path / 'commands'

        if not commands_dir.exists():
            self.issues.append(ValidationIssue(
                file="commands",
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.INFO,
                rule_id="CC004",
                message="No commands/ directory found - consider organizing agent commands",
                fix_guidance="Create commands/ directory to organize agent slash commands"
            ))

    def _validate_skills_structure(self):
        """Validate skills/ directory structure for progressive disclosure"""
        skills_dir = self.root_path / 'skills'

        if not skills_dir.exists():
            return  # Skills are optional

        # Check each skill directory
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.exists():
                self.issues.append(ValidationIssue(
                    file=str(skill_dir.relative_to(self.root_path)),
                    line=None,
                    category=Category.CLAUDE_CODE_FEATURES,
                    severity=Severity.WARNING,
                    rule_id="CC005",
                    message=f"Skill directory missing SKILL.md file",
                    fix_guidance="Create SKILL.md to document skill usage and structure"
                ))

    def _validate_settings_file(self):
        """Validate .claude/settings.json exists and is properly structured"""
        settings_file = self.root_path / '.claude' / 'settings.json'

        if not settings_file.exists():
            self.issues.append(ValidationIssue(
                file=".claude/settings.json",
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.INFO,
                rule_id="CC006",
                message="No .claude/settings.json found",
                fix_guidance="Create settings.json to configure Claude Code behavior"
            ))
            return

        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)

            # Check for recommended settings
            if 'plugins' not in settings and 'mcpServers' not in settings:
                self.issues.append(ValidationIssue(
                    file=".claude/settings.json",
                    line=None,
                    category=Category.CLAUDE_CODE_FEATURES,
                    severity=Severity.INFO,
                    rule_id="CC007",
                    message="No plugins or MCP servers configured in settings",
                    fix_guidance="Consider adding plugins/MCP servers to extend capabilities"
                ))
        except Exception as e:
            self.issues.append(ValidationIssue(
                file=".claude/settings.json",
                line=None,
                category=Category.CLAUDE_CODE_FEATURES,
                severity=Severity.WARNING,
                rule_id="CC008",
                message=f"Could not parse settings.json: {e}",
                fix_guidance="Ensure settings.json is valid JSON"
            ))


class ProgressiveDisclosureValidator:
    """
    Validates hierarchical progressive disclosure principles

    PRISM Principle: Intentionality - Ensure documentation follows disclosure patterns
    """

    def __init__(self, files: Dict[str, FileNode], root_path: Path):
        self.files = files
        self.root_path = root_path
        self.issues: List[ValidationIssue] = []

    def validate(self) -> List[ValidationIssue]:
        """Validate progressive disclosure compliance"""
        for rel_path, file_node in self.files.items():
            if file_node.file_type != 'markdown':
                continue

            self._validate_heading_hierarchy(file_node)
            self._validate_information_layering(file_node)
            self._validate_disclosure_techniques(file_node)

        return self.issues

    def _validate_heading_hierarchy(self, file_node: FileNode):
        """Validate heading levels follow proper hierarchy (no skipping levels)"""
        if not file_node.headings:
            return

        def check_hierarchy(headings: List[Heading], parent_level: int = 0):
            for heading in headings:
                expected_level = parent_level + 1
                if heading.level > expected_level + 1:  # Skipped a level
                    self.issues.append(ValidationIssue(
                        file=file_node.relative_path,
                        line=heading.line_number,
                        category=Category.PROGRESSIVE_DISCLOSURE,
                        severity=Severity.WARNING,
                        rule_id="PD001",
                        message=f"Heading hierarchy skip: jumped from H{parent_level} to H{heading.level}",
                        fix_guidance=f"Use H{expected_level} instead, or restructure document hierarchy"
                    ))

                check_hierarchy(heading.children, heading.level)

        # Check top-level headings start at H1
        first_heading = file_node.headings[0]
        if first_heading.level != 1:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=first_heading.line_number,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.WARNING,
                rule_id="PD002",
                message=f"Document starts with H{first_heading.level} instead of H1",
                fix_guidance="Start document with a single H1 heading"
            ))

        check_hierarchy(file_node.headings)

    def _validate_information_layering(self, file_node: FileNode):
        """Validate information is properly layered (Level 0 → 1 → 2 → 3+)"""
        # Check if document is long enough to benefit from layering
        line_count = len(file_node.content_lines)

        if line_count > 200 and file_node.max_heading_depth <= 2:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=None,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.INFO,
                rule_id="PD003",
                message=f"Long document ({line_count} lines) with shallow hierarchy (max depth: {file_node.max_heading_depth})",
                fix_guidance="Consider breaking into subsections or using deeper heading levels"
            ))

        # Check for overly deep nesting (> 6 levels is too much)
        if file_node.max_heading_depth > 6:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=None,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.WARNING,
                rule_id="PD004",
                message=f"Heading hierarchy too deep (H{file_node.max_heading_depth})",
                fix_guidance="Consider splitting into separate reference files"
            ))

    def _validate_disclosure_techniques(self, file_node: FileNode):
        """Validate use of progressive disclosure UI patterns"""
        # For longer documents, recommend disclosure techniques
        line_count = len(file_node.content_lines)

        if line_count > 150:
            needs_toc = not file_node.has_toc
            needs_details = not file_node.has_details_summary

            if needs_toc and needs_details:
                self.issues.append(ValidationIssue(
                    file=file_node.relative_path,
                    line=None,
                    category=Category.PROGRESSIVE_DISCLOSURE,
                    severity=Severity.INFO,
                    rule_id="PD005",
                    message=f"Long document ({line_count} lines) missing disclosure techniques",
                    fix_guidance="Consider adding: Table of Contents, <details>/<summary> sections, or split into multiple files"
                ))


class CrossReferenceValidator:
    """
    Validates cross-references and links

    PRISM Principle: Resilience - Robust link validation with error handling
    """

    def __init__(self, files: Dict[str, FileNode], root_path: Path):
        self.files = files
        self.root_path = root_path
        self.issues: List[ValidationIssue] = []

    def validate(self) -> List[ValidationIssue]:
        """Validate all cross-references"""
        for rel_path, file_node in self.files.items():
            if file_node.file_type != 'markdown':
                continue

            for link in file_node.internal_links:
                self._validate_link(file_node, link)

        return self.issues

    def _validate_link(self, file_node: FileNode, link: Link):
        """Validate a single internal link"""
        # Skip empty links
        if not link.target or link.target == '#':
            return

        # Skip template placeholders ({{var}}, {var}, ${var})
        if re.search(r'(\{\{.*?\}\}|\{[^}]*\}|\$\{[^}]*\})', link.target):
            return

        # Resolve target path relative to current file
        current_dir = Path(file_node.relative_path).parent

        try:
            # Handle absolute paths from root
            if link.target.startswith('/'):
                target_path = link.target[1:]
            elif link.target.startswith('./') or link.target.startswith('../'):
                # Resolve relative path
                resolved = (current_dir / link.target).resolve()
                try:
                    target_path = str(resolved.relative_to(self.root_path.resolve()))
                except ValueError:
                    # Path is outside root - treat as broken
                    self.issues.append(ValidationIssue(
                        file=file_node.relative_path,
                        line=link.line_number,
                        category=Category.CROSS_REFERENCE,
                        severity=Severity.CRITICAL,
                        rule_id="CR003",
                        message=f"Link points outside root: '{link.target}'",
                        fix_guidance="Ensure link targets a file within the documentation root"
                    ))
                    return
            else:
                target_path = str(current_dir / link.target)

            # Normalize path
            target_path = target_path.replace('\\', '/')
        except Exception as e:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=link.line_number,
                category=Category.CROSS_REFERENCE,
                severity=Severity.WARNING,
                rule_id="CR004",
                message=f"Could not resolve link '{link.target}': {e}",
                fix_guidance="Check link syntax and path validity"
            ))
            return

        # Check if target file exists
        if target_path not in self.files:
            self.issues.append(ValidationIssue(
                file=file_node.relative_path,
                line=link.line_number,
                category=Category.CROSS_REFERENCE,
                severity=Severity.CRITICAL,
                rule_id="CR001",
                message=f"Broken link: '{link.target}' does not exist",
                fix_guidance=f"Verify the target file exists or update the link path"
            ))
            return

        # If anchor specified, validate it exists in target file
        if link.anchor:
            target_file = self.files[target_path]
            valid_anchors = self._collect_anchors(target_file)

            if link.anchor not in valid_anchors:
                self.issues.append(ValidationIssue(
                    file=file_node.relative_path,
                    line=link.line_number,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.CRITICAL,
                    rule_id="CR002",
                    message=f"Invalid anchor: '#{link.anchor}' not found in '{link.target}'",
                    fix_guidance=f"Valid anchors in target: {', '.join(sorted(valid_anchors)[:5])}"
                ))

    def _collect_anchors(self, file_node: FileNode) -> Set[str]:
        """Collect all valid anchors in a file"""
        anchors = set()

        def collect_from_headings(headings: List[Heading]):
            for heading in headings:
                anchors.add(heading.anchor)
                collect_from_headings(heading.children)

        collect_from_headings(file_node.headings)
        return anchors


class SkillBuilderPatternValidator:
    """
    Validates hierarchical progressive disclosure patterns for skills

    Story-002: Hierarchical Progressive Disclosure Pattern Validation
    PRISM Principle: Predictability - Structured validation with 22 clear rules (SB001-SB022)

    Validates:
    - Folder structure (SKILL.md only in root, all references in /reference/ with unlimited depth)
    - Token budgets (metadata <150, body <2k recommended/<5k max, references soft limits)
    - Link patterns (relative paths, descriptive text, no broken links)
    - Reachability (no orphans, reasonable hop counts)
    - Progressive disclosure compliance (required sections, proper hierarchy)
    - Circular references (detect and report cycles)
    """

    def __init__(self, files: Dict[str, FileNode], root_path: Path):
        self.files = files
        self.root_path = root_path
        self.issues: List[ValidationIssue] = []
        self.skills_dir = root_path / 'skills'

    def validate(self) -> List[ValidationIssue]:
        """Run all skill-builder pattern validations"""
        if not TIKTOKEN_AVAILABLE:
            print("Warning: tiktoken not available - skipping token budget validation", file=sys.stderr)

        if not self.skills_dir.exists():
            return self.issues

        # Find all skill directories
        skill_dirs = [d for d in self.skills_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

        for skill_dir in skill_dirs:
            self._validate_skill(skill_dir)

        return self.issues

    def _validate_skill(self, skill_dir: Path):
        """Validate a single skill directory"""
        skill_name = skill_dir.name
        skill_relative = f"skills/{skill_name}"

        # AC1: Validate folder structure
        self._validate_folder_structure(skill_dir, skill_relative)

        # AC2: Validate token budgets
        self._validate_token_budgets(skill_dir, skill_relative)

        # AC3: Validate link patterns
        self._validate_link_patterns(skill_dir, skill_relative)

        # AC4: Validate progressive disclosure patterns
        self._validate_progressive_disclosure(skill_dir, skill_relative)

        # AC5: Validate reachability (no orphans)
        self._validate_reachability(skill_dir, skill_relative)

        # Additional: Detect circular references
        self._detect_circular_references(skill_dir, skill_relative)

    def _validate_folder_structure(self, skill_dir: Path, skill_relative: str):
        """
        AC1: Hierarchical Folder Structure Validation
        Rules: SB001, SB002, SB003
        """
        # SB001: Check for .md files in skill root (other than SKILL.md)
        md_files_in_root = [f for f in skill_dir.glob('*.md') if f.name != 'SKILL.md']

        for md_file in md_files_in_root:
            self.issues.append(ValidationIssue(
                file=f"{skill_relative}/{md_file.name}",
                line=None,
                category=Category.STRUCTURE,
                severity=Severity.CRITICAL,
                rule_id="SB001",
                message=f"Reference file '{md_file.name}' in skill root instead of /reference/",
                fix_guidance=f"Move to {skill_relative}/reference/{md_file.name}"
            ))

        # Check for deep nesting (SB003 - INFO level)
        reference_dir = skill_dir / 'reference'
        if reference_dir.exists():
            for md_file in reference_dir.rglob('*.md'):
                depth = len(md_file.relative_to(reference_dir).parts)
                if depth > 3:  # More than 3 levels deep
                    self.issues.append(ValidationIssue(
                        file=str(md_file.relative_to(self.root_path)).replace('\\', '/'),
                        line=None,
                        category=Category.STRUCTURE,
                        severity=Severity.INFO,
                        rule_id="SB003",
                        message=f"Deep nesting detected ({depth} levels) - consider flattening",
                        fix_guidance="Consider reorganizing to reduce nesting depth for easier navigation"
                    ))

    def _validate_token_budgets(self, skill_dir: Path, skill_relative: str):
        """
        AC2: Token Budget Validation Per Level
        Rules: SB004, SB005, SB006, SB007, SB008, SB009
        """
        if not TIKTOKEN_AVAILABLE:
            return

        skill_md_path = f"{skill_relative}/SKILL.md"
        file_node = self.files.get(skill_md_path)

        if not file_node:
            return

        # Extract and validate YAML metadata (Level 1)
        yaml_content = TokenCountingUtilities.extract_yaml_frontmatter(file_node.content_lines)
        yaml_tokens = TokenCountingUtilities.count_tokens(yaml_content)

        if yaml_tokens > 150:
            self.issues.append(ValidationIssue(
                file=skill_md_path,
                line=None,
                category=Category.METADATA,
                severity=Severity.WARNING,
                rule_id="SB004",
                message=f"Metadata exceeds 150 tokens ({yaml_tokens} actual)",
                fix_guidance="Simplify metadata or move detailed info to body/reference files"
            ))

        # Check for required metadata fields (SB005)
        yaml_lower = yaml_content.lower()
        required_fields = ['name', 'description']
        missing_fields = [f for f in required_fields if f not in yaml_lower]

        if missing_fields:
            self.issues.append(ValidationIssue(
                file=skill_md_path,
                line=None,
                category=Category.METADATA,
                severity=Severity.CRITICAL,
                rule_id="SB005",
                message=f"Missing required metadata fields: {', '.join(missing_fields)}",
                fix_guidance="Add required fields to YAML frontmatter"
            ))

        # Extract and validate markdown body (Level 2)
        body_content = TokenCountingUtilities.extract_markdown_body(file_node.content_lines)
        body_tokens = TokenCountingUtilities.count_tokens(body_content)

        if body_tokens > 5000:
            self.issues.append(ValidationIssue(
                file=skill_md_path,
                line=None,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.CRITICAL,
                rule_id="SB007",
                message=f"Body exceeds 5,000 tokens ({body_tokens} actual) - must refactor",
                fix_guidance="Split content into reference files. Body should be table of contents only"
            ))
        elif body_tokens > 2000:
            self.issues.append(ValidationIssue(
                file=skill_md_path,
                line=None,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.WARNING,
                rule_id="SB006",
                message=f"Body exceeds 2,000 tokens ({body_tokens} actual) - recommend splitting",
                fix_guidance="Consider moving detailed content to reference files"
            ))

        # Validate reference files (Level 3+)
        reference_dir = skill_dir / 'reference'
        if reference_dir.exists():
            for md_file in reference_dir.rglob('*.md'):
                ref_relative = str(md_file.relative_to(self.root_path)).replace('\\', '/')
                ref_node = self.files.get(ref_relative)

                if ref_node:
                    ref_content = ''.join(ref_node.content_lines)
                    ref_tokens = TokenCountingUtilities.count_tokens(ref_content)

                    if ref_tokens > 10000:
                        self.issues.append(ValidationIssue(
                            file=ref_relative,
                            line=None,
                            category=Category.PROGRESSIVE_DISCLOSURE,
                            severity=Severity.WARNING,
                            rule_id="SB009",
                            message=f"Reference file exceeds 10,000 tokens ({ref_tokens} actual)",
                            fix_guidance="Strongly recommend splitting into multiple focused files"
                        ))
                    elif ref_tokens > 3000:
                        self.issues.append(ValidationIssue(
                            file=ref_relative,
                            line=None,
                            category=Category.PROGRESSIVE_DISCLOSURE,
                            severity=Severity.INFO,
                            rule_id="SB008",
                            message=f"Reference file exceeds 3,000 tokens ({ref_tokens} actual)",
                            fix_guidance="Consider splitting for better progressive disclosure"
                        ))

    def _validate_link_patterns(self, skill_dir: Path, skill_relative: str):
        """
        AC3: Progressive Disclosure Link Pattern Validation
        Rules: SB010, SB011, SB012, SB013, SB014, SB015
        """
        skill_md_path = f"{skill_relative}/SKILL.md"
        file_node = self.files.get(skill_md_path)

        if not file_node:
            return

        # Validate links from SKILL.md
        for link in file_node.internal_links:
            # SB010: Check if linked reference file exists
            target_path = self._resolve_link_path(skill_md_path, link.target)

            if target_path not in self.files:
                self.issues.append(ValidationIssue(
                    file=skill_md_path,
                    line=link.line_number,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.CRITICAL,
                    rule_id="SB010",
                    message=f"Link to non-existent reference file: '{link.target}'",
                    fix_guidance="Create the referenced file or update the link"
                ))
                continue

            # SB011: Check for absolute paths
            if link.target.startswith('/'):
                self.issues.append(ValidationIssue(
                    file=skill_md_path,
                    line=link.line_number,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.WARNING,
                    rule_id="SB011",
                    message=f"Link uses absolute path: '{link.target}'",
                    fix_guidance="Use relative path: './reference/...' instead"
                ))

            # SB012: Check for non-descriptive link text
            non_descriptive = ['here', 'this', 'link', 'click', 'click here']
            if link.text.lower().strip() in non_descriptive:
                self.issues.append(ValidationIssue(
                    file=skill_md_path,
                    line=link.line_number,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.INFO,
                    rule_id="SB012",
                    message=f"Non-descriptive link text: '{link.text}'",
                    fix_guidance="Use descriptive text that explains what the link points to"
                ))

    def _validate_progressive_disclosure(self, skill_dir: Path, skill_relative: str):
        """
        AC4: Progressive Disclosure Pattern Compliance
        Rules: SB016, SB017, SB018, SB019, SB020
        """
        skill_md_path = f"{skill_relative}/SKILL.md"
        file_node = self.files.get(skill_md_path)

        if not file_node:
            return

        content = ''.join(file_node.content_lines).lower()

        # SB016: Check for recommended sections
        recommended_sections = {
            'when to use': 'whenToUse or trigger conditions',
            'what': 'high-level overview',
            'quick start': 'immediate action path'
        }

        for section_name, description in recommended_sections.items():
            if section_name not in content:
                self.issues.append(ValidationIssue(
                    file=skill_md_path,
                    line=None,
                    category=Category.PROGRESSIVE_DISCLOSURE,
                    severity=Severity.WARNING,
                    rule_id="SB016",
                    message=f"Missing recommended section: '{section_name}' ({description})",
                    fix_guidance=f"Add a section about {description}"
                ))

        # SB017: Check for table of contents on large files
        body_content = TokenCountingUtilities.extract_markdown_body(file_node.content_lines)
        body_tokens = TokenCountingUtilities.count_tokens(body_content)

        if body_tokens > 1000 and not file_node.has_toc:
            self.issues.append(ValidationIssue(
                file=skill_md_path,
                line=None,
                category=Category.PROGRESSIVE_DISCLOSURE,
                severity=Severity.INFO,
                rule_id="SB017",
                message="No table of contents for body >1,000 tokens",
                fix_guidance="Add a table of contents section for easier navigation"
            ))

    def _validate_reachability(self, skill_dir: Path, skill_relative: str):
        """
        AC5: Reachability Analysis (No Orphans)
        Rules: SB021, SB022
        """
        skill_md_path = f"{skill_relative}/SKILL.md"

        # Build graph of reachable files from SKILL.md
        reachable = self._analyze_reachability(skill_md_path)

        # Find all reference files in this skill
        reference_dir = skill_dir / 'reference'
        if not reference_dir.exists():
            return

        for md_file in reference_dir.rglob('*.md'):
            ref_relative = str(md_file.relative_to(self.root_path)).replace('\\', '/')

            if ref_relative not in reachable:
                # SB021: Orphaned file
                self.issues.append(ValidationIssue(
                    file=ref_relative,
                    line=None,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.WARNING,
                    rule_id="SB021",
                    message="Orphaned reference file (not reachable from SKILL.md)",
                    fix_guidance="Add a link to this file from SKILL.md or another reachable file"
                ))
            elif reachable[ref_relative] > 5:
                # SB022: Too many hops
                self.issues.append(ValidationIssue(
                    file=ref_relative,
                    line=None,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.INFO,
                    rule_id="SB022",
                    message=f"File requires {reachable[ref_relative]} hops from SKILL.md",
                    fix_guidance="Consider restructuring for shorter link chains"
                ))

    def _analyze_reachability(self, root_file: str) -> Dict[str, int]:
        """
        Perform BFS to find all reachable files and their hop counts

        Returns:
            Dict mapping file path to hop count from root (0 = root file)
        """
        reachable = {root_file: 0}
        queue = deque([(root_file, 0)])

        while queue:
            current_path, hop_count = queue.popleft()
            current_file = self.files.get(current_path)

            if not current_file:
                continue

            # Process all internal links from current file
            for link in current_file.internal_links:
                target_path = self._resolve_link_path(current_path, link.target)

                if target_path and target_path not in reachable and target_path in self.files:
                    reachable[target_path] = hop_count + 1
                    queue.append((target_path, hop_count + 1))

        return reachable

    def _detect_circular_references(self, skill_dir: Path, skill_relative: str):
        """
        Detect circular reference chains using DFS
        Rule: SB013
        """
        visited = set()

        # Start DFS from SKILL.md
        skill_md_path = f"{skill_relative}/SKILL.md"
        if skill_md_path in self.files:
            cycles = self._dfs_detect_cycles(skill_md_path, visited, [])

            for cycle in cycles:
                cycle_str = ' → '.join(cycle)
                self.issues.append(ValidationIssue(
                    file=cycle[0],
                    line=None,
                    category=Category.CROSS_REFERENCE,
                    severity=Severity.CRITICAL,
                    rule_id="SB013",
                    message=f"Circular reference detected: {cycle_str}",
                    fix_guidance="Remove one of the links to break the cycle"
                ))

    def _dfs_detect_cycles(self, path: str, visited: Set[str], path_stack: List[str]) -> List[List[str]]:
        """DFS helper to detect circular references"""
        if path in path_stack:
            # Found cycle
            cycle_start = path_stack.index(path)
            return [path_stack[cycle_start:] + [path]]

        if path in visited:
            return []

        visited.add(path)
        path_stack.append(path)

        cycles = []
        file_node = self.files.get(path)
        if file_node:
            for link in file_node.internal_links:
                target_path = self._resolve_link_path(path, link.target)
                if target_path and target_path in self.files:
                    cycles.extend(self._dfs_detect_cycles(target_path, visited, path_stack[:]))

        return cycles

    def _resolve_link_path(self, current_file: str, link_target: str) -> Optional[str]:
        """Resolve relative link path to absolute path"""
        if not link_target or link_target.startswith(('http://', 'https://', 'mailto:')):
            return None

        # Remove anchor if present
        if '#' in link_target:
            link_target = link_target.split('#')[0]

        if not link_target:
            return None

        current_dir = str(Path(current_file).parent)

        if link_target.startswith('./'):
            # Relative to current directory
            resolved = str(Path(current_dir) / link_target[2:])
        elif link_target.startswith('../'):
            # Relative to parent directory
            resolved = str(Path(current_dir) / link_target)
        elif link_target.startswith('/'):
            # Absolute from root
            resolved = link_target[1:]
        else:
            # Relative to current directory
            resolved = str(Path(current_dir) / link_target)

        # Normalize path
        resolved = str(Path(resolved)).replace('\\', '/')

        return resolved


def generate_markdown_report(report: ValidationReport, output_path: Path):
    """Generate detailed markdown validation report"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# PRISM Documentation Validation Report\n\n")
        f.write(f"**Generated**: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")

        # Summary
        f.write(f"## Executive Summary\n\n")
        f.write(f"- **Files Checked**: {report.files_checked}/{report.total_files}\n")
        f.write(f"- **Coverage**: {report.coverage_percentage:.1f}%\n")
        f.write(f"- **Total Issues**: {len(report.issues)}\n\n")

        # Issues by severity
        f.write(f"### Issues by Severity\n\n")
        for severity, count in report.issues_by_severity.items():
            f.write(f"- **{severity}**: {count}\n")
        f.write(f"\n")

        # Issues by category
        f.write(f"### Issues by Category\n\n")
        for category, count in report.issues_by_category.items():
            if count > 0:
                f.write(f"- **{category.replace('_', ' ').title()}**: {count}\n")
        f.write(f"\n---\n\n")

        # Detailed issues grouped by category
        for category in Category:
            category_issues = [i for i in report.issues if i.category == category]
            if not category_issues:
                continue

            f.write(f"## {category.value.replace('_', ' ').title()} Issues\n\n")

            # Group by severity
            for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
                severity_issues = [i for i in category_issues if i.severity == severity]
                if not severity_issues:
                    continue

                f.write(f"### {severity.value}\n\n")

                for issue in severity_issues[:20]:  # Limit to first 20 per category/severity
                    f.write(f"**{issue.rule_id}**: `{issue.file}`")
                    if issue.line:
                        f.write(f":{issue.line}")
                    f.write(f"\n")
                    f.write(f"- **Issue**: {issue.message}\n")
                    f.write(f"- **Fix**: {issue.fix_guidance}\n\n")

                if len(severity_issues) > 20:
                    f.write(f"*... and {len(severity_issues) - 20} more {severity.value} issues*\n\n")

            f.write(f"\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate PRISM documentation for Claude Code best practices and progressive disclosure'
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=Path('.'),
        help='Root directory to validate (default: current directory)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('docs/validation/validation-report.md'),
        help='Output report path'
    )

    args = parser.parse_args()

    print("PRISM Documentation Validator")
    print("=" * 70)
    print(f"Root: {args.root}")
    print()

    # Phase 1: Scan files
    print("Phase 1: Scanning documentation files...")
    scanner = DocumentationScanner(args.root)
    files = scanner.scan()
    print(f"OK: Found {len(files)} files ({sum(1 for f in files.values() if f.file_type == 'markdown')} markdown)")
    print()

    all_issues = []

    # Phase 2: Validate Claude Code features
    print("Phase 2: Validating Claude Code feature usage...")
    claude_validator = ClaudeCodeFeatureValidator(files, args.root)
    claude_issues = claude_validator.validate()
    all_issues.extend(claude_issues)
    print(f"OK: Found {len(claude_issues)} Claude Code feature issues")
    print()

    # Phase 3: Validate progressive disclosure
    print("Phase 3: Validating progressive disclosure compliance...")
    disclosure_validator = ProgressiveDisclosureValidator(files, args.root)
    disclosure_issues = disclosure_validator.validate()
    all_issues.extend(disclosure_issues)
    print(f"OK: Found {len(disclosure_issues)} progressive disclosure issues")
    print()

    # Phase 4: Validate cross-references
    print("Phase 4: Validating cross-references...")
    cross_ref_validator = CrossReferenceValidator(files, args.root)
    cross_ref_issues = cross_ref_validator.validate()
    all_issues.extend(cross_ref_issues)
    print(f"OK: Found {len(cross_ref_issues)} cross-reference issues")
    print()

    # Phase 5: Validate skill-builder patterns (Story-002)
    print("Phase 5: Validating skill-builder hierarchical patterns...")
    skillbuilder_validator = SkillBuilderPatternValidator(files, args.root)
    skillbuilder_issues = skillbuilder_validator.validate()
    all_issues.extend(skillbuilder_issues)
    print(f"OK: Found {len(skillbuilder_issues)} skill-builder pattern issues")
    print()

    # Generate report
    report = ValidationReport(
        timestamp=datetime.now(),
        total_files=len(files),
        files_checked=len([f for f in files.values() if f.file_type == 'markdown']),
        issues=all_issues
    )

    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_markdown_report(report, args.output)

    # Display summary
    print("Validation Summary")
    print("-" * 70)
    print(f"Files checked: {report.files_checked}/{report.total_files}")
    print(f"Coverage: {report.coverage_percentage:.1f}%")
    print(f"\nIssues by severity:")
    for severity, count in report.issues_by_severity.items():
        print(f"  {severity}: {count}")
    print(f"\nIssues by category:")
    for category, count in report.issues_by_category.items():
        if count > 0:
            print(f"  {category.replace('_', ' ').title()}: {count}")
    print(f"\nDetailed report: {args.output}")
    print()

    if report.issues:
        print(f"Found {len(report.issues)} total issues")
        critical_count = sum(1 for i in report.issues if i.severity == Severity.CRITICAL)
        if critical_count > 0:
            print(f"CRITICAL: {critical_count} issues must be fixed")
    else:
        print("OK: No issues found!")

    return 0 if not any(i.severity == Severity.CRITICAL for i in all_issues) else 1


if __name__ == '__main__':
    sys.exit(main())
