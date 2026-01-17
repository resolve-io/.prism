# Documentation Quality Checklist

## Overview
This checklist ensures PRISM documentation follows Claude Code best practices and progressive disclosure principles.

## Usage
Run before committing documentation changes:
```bash
python scripts/validate-docs.py --root .
```

Review the generated report at `docs/validation/validation-report.md`.

---

## Claude Code Features

### Agents (.claude/agents/)
- [ ] Agent files exist in `.claude/agents/`
- [ ] Each agent has Purpose, Tools, and Prompt sections
- [ ] Agent prompts are clear and actionable
- [ ] Agents use appropriate tool restrictions

### Skills (skills/)
- [ ] Each skill has a `SKILL.md` file
- [ ] Skills follow progressive disclosure (Level 0 → 1 → 2 → 3+)
- [ ] Reference files in `reference/` subdirectory
- [ ] Links use correct relative paths (`../shared/reference/`)

### Commands (commands/)
- [ ] Command files organized by agent role
- [ ] Commands have clear descriptions
- [ ] Command prompts are concise and actionable

### Settings (.claude/settings.json)
- [ ] Settings file exists and is valid JSON
- [ ] Plugins configured appropriately
- [ ] MCP servers configured if needed

---

## Progressive Disclosure

### Heading Hierarchy
- [ ] Documents start with H1
- [ ] No skipped heading levels (H1 → H2 → H3, not H1 → H3)
- [ ] Maximum depth ≤ 6 levels
- [ ] Hierarchy reflects information importance

### Information Layering
- [ ] Essential information at top (Level 0/1)
- [ ] Details progressively disclosed (Level 2/3+)
- [ ] Long documents (>150 lines) use disclosure techniques
- [ ] Complex topics split into reference files

### Disclosure Techniques
For documents >150 lines, use at least one:
- [ ] Table of Contents with anchors
- [ ] `<details>`/`<summary>` sections for optional content
- [ ] Split into multiple files with clear navigation
- [ ] Breadcrumb navigation (← Previous | Next →)

---

## Cross-Reference Integrity

### Internal Links
- [ ] All markdown links resolve to existing files
- [ ] All anchor links have valid targets in destination files
- [ ] Relative paths are correct (`./`, `../`)
- [ ] No broken links to moved/renamed files

### External Links
- [ ] External URLs are valid and accessible
- [ ] No hardcoded localhost URLs in documentation
- [ ] API documentation links point to correct versions

### Bidirectional Navigation
- [ ] Related documents link to each other
- [ ] Parent/child relationships clear
- [ ] Breadcrumbs show current location

---

## Structure Consistency

### File Organization
- [ ] Files in correct directories (skills/, docs/, checklists/, etc.)
- [ ] Naming conventions followed (kebab-case, descriptive)
- [ ] Index files accurate (README.md, index.md)
- [ ] Archive files in `docs/archive/`

### SKILL.md Consistency
- [ ] All skills have same basic structure
- [ ] Dependencies section present
- [ ] Examples section present
- [ ] Reference links use correct paths

### Template Compliance
- [ ] Story files follow story-tmpl.yaml
- [ ] Epic files follow epic-tmpl.yaml
- [ ] Agent files follow agent structure

---

## Metadata Completeness

### Document Metadata
- [ ] Last Updated dates present
- [ ] Version information when applicable
- [ ] Author/owner identified
- [ ] Status indicators clear (Draft, Ready, Archived)

### Navigation Metadata
- [ ] Previous/Next links correct
- [ ] Table of contents matches actual structure
- [ ] Breadcrumbs show document hierarchy
- [ ] Cross-references maintained

---

## Validation Rules Reference

### Critical (Must Fix)
- **CR001**: Broken internal links
- **CR002**: Invalid anchor references
- **CR003**: Links outside documentation root

### Warning (Should Fix)
- **PD001**: Heading hierarchy skip
- **PD002**: Document doesn't start with H1
- **PD004**: Heading hierarchy too deep (>6 levels)
- **CC003**: Agent missing recommended sections

### Info (Consider)
- **PD003**: Long document with shallow hierarchy
- **PD005**: Long document missing disclosure techniques
- **CC006**: No settings.json file
- **CC007**: No plugins/MCP configured

### Skill-Builder Pattern Rules (SB - Story-002)

**Critical (Must Fix):**
- **SB001**: Reference `.md` file in skill root (move to /reference/)
- **SB005**: Missing required metadata fields (name, description)
- **SB007**: SKILL.md body exceeds 5,000 tokens (must refactor)
- **SB010**: Link to non-existent reference file
- **SB013**: Circular reference detected in link graph

**Warning (Should Fix):**
- **SB004**: Metadata exceeds 150 tokens
- **SB006**: SKILL.md body exceeds 2,000 tokens (recommend splitting)
- **SB009**: Reference file exceeds 10,000 tokens
- **SB011**: Link uses absolute path (use relative instead)
- **SB016**: Missing recommended section (When to Use, What This Does, Quick Start)
- **SB021**: Orphaned reference file (not reachable from SKILL.md)

**Info (Consider):**
- **SB003**: Deep nesting detected (>3 levels)
- **SB008**: Reference file exceeds 3,000 tokens
- **SB012**: Non-descriptive link text
- **SB017**: No table of contents for body >1,000 tokens
- **SB022**: File requires >5 link hops from SKILL.md

---

## Severity Guidelines

### When to Fix Immediately (Critical)
- Broken links that prevent navigation
- Invalid anchors that cause 404s
- Links pointing outside documentation root

### When to Fix Soon (Warning)
- Heading hierarchy issues affecting readability
- Missing recommended sections in agents
- Structure inconsistencies across similar files

### When to Consider (Info)
- Optimization opportunities (TOC, details/summary)
- Missing optional enhancements
- Suggestions for better organization

---

## Running Validation

### Command Line
```bash
# Validate entire project
python scripts/validate-docs.py --root .

# Validate specific directory
python scripts/validate-docs.py --root ./skills

# Custom output location
python scripts/validate-docs.py --root . --output custom-report.md
```

### Interpreting Results
1. **Coverage**: Percentage of files validated (target: >90%)
2. **Critical Issues**: Must be fixed before merging
3. **Warnings**: Should be addressed for quality
4. **Info**: Optional improvements

### CI/CD Integration (Future)
```bash
# Exit code 0 = no critical issues, 1 = critical issues found
python scripts/validate-docs.py --root .
if [ $? -eq 1 ]; then
  echo "Critical validation issues found. See report."
  exit 1
fi
```

---

## Common Issues & Fixes

### Issue: Broken Link
**Problem**: `Broken link: './reference/foo.md' does not exist`
**Fix**: Create the missing file or update the link path

### Issue: Invalid Anchor
**Problem**: `Invalid anchor: '#section-name' not found`
**Fix**: Check heading text, anchors are lowercase with hyphens (e.g., "Section Name" → "#section-name")

### Issue: Heading Hierarchy Skip
**Problem**: `Heading hierarchy skip: jumped from H1 to H3`
**Fix**: Use H2 between H1 and H3, or restructure document

### Issue: Shallow Hierarchy
**Problem**: `Long document (300 lines) with shallow hierarchy (max depth: 2)`
**Fix**: Add subsections (H3, H4) or split into multiple files

---

## Best Practices

### Writing New Documentation
1. Start with H1 title
2. Add table of contents for long documents
3. Use progressive disclosure for complex topics
4. Test all links before committing
5. Run validation script: `python scripts/validate-docs.py`

### Updating Existing Documentation
1. Run validation to check current state
2. Fix any broken links you introduce
3. Maintain consistent heading hierarchy
4. Update "Last Updated" date
5. Re-run validation before committing

### Creating New Skills
1. Use SKILL.md template
2. Place reference docs in `reference/` subdirectory
3. Use relative paths: `../shared/reference/`
4. Follow progressive disclosure pattern
5. Validate with: `python scripts/validate-docs.py --root ./skills`

### Skill-Builder Hierarchical Patterns (Story-002)
1. **Folder Structure**: Only SKILL.md in root, all references in `/reference/`
2. **Token Budgets**:
   - Metadata: <150 tokens
   - SKILL.md body: <2k tokens recommended, <5k max
   - Reference files: <3k tokens recommended, <10k warning
3. **Link Patterns**: Use relative paths (`./reference/file.md`)
4. **Reachability**: Ensure all reference files are linked from SKILL.md
5. **Required Sections**: When to Use, What This Does, Quick Start
6. **Navigation**: Add table of contents for bodies >1k tokens
7. **Avoid Orphans**: Link to all reference files, avoid circular references

---

**Last Updated**: 2025-10-29
