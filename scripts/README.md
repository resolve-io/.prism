# PRISM Documentation Validation Script

## Overview

`validate-docs.py` is a comprehensive validation tool that ensures PRISM documentation follows Claude Code best practices and progressive disclosure principles.

## What It Validates

### 1. Claude Code Feature Usage
- **Agents**: Validates `.claude/agents/` structure and agent file format
- **Skills**: Checks skill organization and SKILL.md files
- **Commands**: Validates command structure
- **Settings**: Verifies `.claude/settings.json` configuration

### 2. Progressive Disclosure Compliance
- **Heading Hierarchy**: Ensures proper H1 → H2 → H3 structure
- **Information Layering**: Validates depth and organization
- **Disclosure Techniques**: Checks for TOC, details/summary usage

### 3. Cross-Reference Integrity
- **Internal Links**: Validates all markdown links resolve correctly
- **Anchors**: Checks heading anchor references
- **Path Resolution**: Handles relative and absolute paths

### 4. Skill-Builder Hierarchical Patterns (Story-002)
- **Folder Structure**: Validates SKILL.md only in root, all references in /reference/ with unlimited depth
- **Token Budgets**: Validates metadata (<150 tokens), body (<2k recommended/<5k max), reference files (soft limits)
- **Link Patterns**: Validates relative paths, descriptive text, no broken links
- **Reachability**: Ensures no orphaned files, reasonable hop counts from SKILL.md
- **Progressive Disclosure**: Validates required sections, proper hierarchy, navigation
- **Circular References**: Detects and reports cycles in link graphs

## Installation

### Requirements
- Python 3.7+
- tiktoken>=0.5.1 (for token budget validation)
- Install dependencies: `pip install -r requirements.txt`

### Setup
```bash
# Make script executable (Unix/Linux/Mac)
chmod +x scripts/validate-docs.py

# Run validation
python scripts/validate-docs.py
```

## Usage

### Basic Usage
```bash
# Validate entire project from root
python scripts/validate-docs.py --root .

# Output will show summary and generate detailed report
```

### Command-Line Options
```bash
python scripts/validate-docs.py [OPTIONS]

Options:
  --root PATH     Root directory to validate (default: current directory)
  --output PATH   Output report path (default: docs/validation/validation-report.md)
  --help          Show help message
```

### Examples
```bash
# Validate from project root
python scripts/validate-docs.py

# Validate specific directory
python scripts/validate-docs.py --root ./skills

# Custom output location
python scripts/validate-docs.py --root . --output my-report.md

# Validate and check exit code
python scripts/validate-docs.py
if [ $? -eq 0 ]; then
  echo "✓ No critical issues"
else
  echo "✗ Critical issues found"
fi
```

## Output

### Console Output
```
PRISM Documentation Validator
======================================================================
Root: .

Phase 1: Scanning documentation files...
OK: Found 141 files (128 markdown)

Phase 2: Validating Claude Code feature usage...
OK: Found 2 Claude Code feature issues

Phase 3: Validating progressive disclosure compliance...
OK: Found 116 progressive disclosure issues

Phase 4: Validating cross-references...
OK: Found 173 cross-reference issues

Phase 5: Validating skill-builder hierarchical patterns...
OK: Found 128 skill-builder pattern issues

Validation Summary
----------------------------------------------------------------------
Files checked: 128/141
Coverage: 90.8%

Issues by severity:
  Critical: 160
  Warning: 21
  Info: 97

Issues by category:
  Cross Reference: 160
  Progressive Disclosure: 116
  Claude Code Features: 2

Detailed report: docs\validation\validation-report.md

Found 278 total issues
CRITICAL: 160 issues must be fixed
```

### Detailed Report
A markdown report is generated at `docs/validation/validation-report.md` containing:
- Executive summary with metrics
- Issues grouped by category and severity
- File paths and line numbers for each issue
- Fix guidance for each issue type

## Validation Rules

### Critical Rules (Exit Code 1)
- **CR001**: Broken internal link - file doesn't exist
- **CR002**: Invalid anchor - heading not found in target file
- **CR003**: Link points outside documentation root

### Warning Rules
- **PD001**: Heading hierarchy skip (H1 → H3 without H2)
- **PD002**: Document doesn't start with H1
- **PD004**: Heading hierarchy too deep (>6 levels)
- **CC003**: Agent file missing recommended sections

### Info Rules
- **PD003**: Long document with shallow hierarchy
- **PD005**: Long document missing disclosure techniques
- **CC006**: No settings.json file
- **CC007**: No plugins/MCP configured

### Skill-Builder Pattern Rules (SB Rules)

**Critical Rules:**
- **SB001**: Reference `.md` file in skill root (should be in /reference/)
- **SB005**: Missing required metadata fields (name, description)
- **SB007**: SKILL.md body exceeds 5,000 tokens (must refactor)
- **SB010**: Link to non-existent reference file
- **SB013**: Circular reference detected in link graph

**Warning Rules:**
- **SB002**: Reference file exists but not linked (orphaned)
- **SB004**: Metadata exceeds 150 tokens
- **SB006**: SKILL.md body exceeds 2,000 tokens (recommend splitting)
- **SB009**: Reference file exceeds 10,000 tokens
- **SB011**: Link uses absolute path instead of relative
- **SB016**: Missing recommended section (When to Use, What This Does, Quick Start)
- **SB021**: Orphaned reference file (not reachable from SKILL.md)

**Info Rules:**
- **SB003**: Deep nesting detected (>3 levels) - consider flattening
- **SB008**: Reference file exceeds 3,000 tokens (consider splitting)
- **SB012**: Non-descriptive link text
- **SB014**: Deep link crosses multiple levels without intermediate stops
- **SB015**: Missing bidirectional navigation
- **SB017**: No table of contents for body >1,000 tokens
- **SB018**: Reference file lacks clear topic focus
- **SB019**: Missing navigation breadcrumbs for nested files
- **SB020**: Long section (>500 tokens) without details/summary or file split
- **SB022**: File requires >5 link hops from SKILL.md

## Exit Codes

- **0**: Validation passed (no critical issues)
- **1**: Validation failed (critical issues found)

Use exit codes in scripts/CI:
```bash
python scripts/validate-docs.py
EXIT_CODE=$?
if [ $EXIT_CODE -eq 1 ]; then
  echo "Validation failed - fix critical issues before proceeding"
  exit 1
fi
```

## Architecture

### Modular Design (PRISM Principles)
The validator follows PRISM principles with clear separation of concerns:

```python
DocumentationScanner
├── Scans files recursively
├── Parses markdown (headings, links)
└── Builds file graph

ClaudeCodeFeatureValidator
├── Validates agent structure
├── Validates skills organization
├── Validates commands and settings
└── Returns Claude Code-specific issues

ProgressiveDisclosureValidator
├── Validates heading hierarchy
├── Validates information layering
├── Checks disclosure techniques
└── Returns disclosure issues

SkillBuilderPatternValidator (Story-002)
├── Validates folder structure (SKILL.md only in root)
├── Validates token budgets (metadata/body/references)
├── Validates link patterns (relative paths, descriptive text)
├── Performs reachability analysis (BFS from SKILL.md)
├── Detects circular references (DFS cycle detection)
└── Returns skill-builder pattern issues

CrossReferenceValidator
├── Resolves link paths
├── Validates file existence
├── Validates anchors
└── Returns broken link issues

ValidationReport
├── Aggregates all issues
├── Calculates metrics
└── Generates markdown report
```

### Data Models
```python
FileNode: Represents a documentation file
  - path, relative_path
  - headings (hierarchical)
  - internal_links, external_links
  - metadata, progressive disclosure features

ValidationIssue:
  - file, line
  - category, severity
  - rule_id, message
  - fix_guidance

ValidationReport:
  - timestamp, coverage
  - issues (by severity/category)
  - statistics
```

## Customization

### Adding New Rules
1. Choose validator class (ClaudeCodeFeatureValidator, ProgressiveDisclosureValidator, CrossReferenceValidator)
2. Add validation method
3. Create issues with appropriate severity
4. Add rule documentation

Example:
```python
def _validate_custom_rule(self, file_node: FileNode):
    if some_condition:
        self.issues.append(ValidationIssue(
            file=file_node.relative_path,
            line=None,
            category=Category.STRUCTURE,
            severity=Severity.WARNING,
            rule_id="CUSTOM001",
            message="Custom rule violation",
            fix_guidance="How to fix this issue"
        ))
```

### Adjusting Severity
Edit severity in validator methods:
- `Severity.CRITICAL` - Must fix (exits with code 1)
- `Severity.WARNING` - Should fix
- `Severity.INFO` - Consider fixing

### Configuring Thresholds
Adjust validation thresholds in validator classes:
```python
# Progressive disclosure validator
if line_count > 200 and file_node.max_heading_depth <= 2:
    # Adjust 200 threshold as needed
```

## Performance

### Benchmarks
- **100 files**: ~2-3 seconds
- **500 files**: ~10-15 seconds
- **Memory**: <50MB for typical projects

### Optimization
- Files parsed once and cached
- Regex patterns compiled
- Lazy evaluation where possible

## Troubleshooting

### Issue: "Could not read file"
**Cause**: File encoding issues
**Fix**: Ensure files are UTF-8 encoded

### Issue: "Path resolution errors"
**Cause**: Mixed path separators (\ vs /)
**Fix**: Validator auto-normalizes paths

### Issue: "Too many INFO issues"
**Cause**: Many suggestions for improvement
**Fix**: Focus on CRITICAL and WARNING first, INFO is optional

### Issue: "Template placeholders flagged as broken"
**Cause**: Validator should skip `{var}`, `{{var}}`, `${var}`
**Fix**: Already handled - if still occurring, check regex pattern

## Integration

### Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running documentation validation..."
python scripts/validate-docs.py --root .

if [ $? -eq 1 ]; then
  echo "❌ Documentation validation failed"
  echo "Fix critical issues or use git commit --no-verify to skip"
  exit 1
fi

echo "✓ Documentation validation passed"
```

### GitHub Actions (Future)
```yaml
name: Validate Documentation
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Run validation
        run: python scripts/validate-docs.py
      - name: Upload report
        if: failure()
        uses: actions/upload-artifact@v2
        with:
          name: validation-report
          path: docs/validation/validation-report.md
```

## Development

### Running Tests
```bash
# Test on sample directory
python scripts/validate-docs.py --root ./docs/archive/test-artifacts
```

### Adding Validators
1. Create new validator class inheriting pattern
2. Implement `validate()` method
3. Add to main() execution
4. Update documentation

### Code Style
- Follows PRISM principles (Predictability, Resilience, Intentionality, Sustainability, Maintainability)
- Type hints for all public methods
- Docstrings for all classes and methods
- Modular design with single responsibility

## Support

### Getting Help
- Check validation report for fix guidance
- See `documentation-quality-checklist.md` for best practices
- Review validation rules in this README

### Reporting Issues
If validator gives false positives:
1. Check if it's expected (template placeholders, etc.)
2. Review path resolution logic
3. Report with example file and expected behavior

## Version History

### v1.1.0 (2025-10-29) - Story-002
- Added Skill-Builder Pattern Validator with 22 validation rules (SB001-SB022)
- Token budget validation using tiktoken library (cl100k_base encoding)
- Hierarchical folder structure validation with unlimited depth support
- Reachability analysis (BFS) to detect orphaned reference files
- Circular reference detection (DFS) to identify link cycles
- Progressive disclosure compliance checks for skills
- Enhanced reporting with skill-specific metrics

### v1.0.0 (2025-10-29) - Story-001
- Initial release
- Claude Code feature validation
- Progressive disclosure validation
- Cross-reference validation
- Markdown report generation
- 182 issues fixed during development

---

**Maintained by**: PRISM Development Team
**Last Updated**: 2025-10-29
