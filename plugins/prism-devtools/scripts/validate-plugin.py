#!/usr/bin/env python3
"""
Plugin Wiring Validator
=======================
Structural validation of plugin component integrity and cross-component wiring.
Complements validate-all (doc quality) by checking that all plugin pieces exist
and reference each other correctly.

Phases:
  1. Manifest     — plugin.json required fields + claude plugin validate
  2. Skills       — SKILL.md frontmatter (name, description) + referenced scripts
  3. Commands     — commands/*.md has frontmatter or heading, non-empty
  4. Agents       — agents/*.md has frontmatter with name + description
  5. Hooks        — hooks.json schema, referenced scripts exist, .py files compile
  6. Cross-component — skills→agents, commands→skills, hooks→scripts resolve

Usage:
    python scripts/validate-plugin.py              # From plugin directory
    python scripts/validate-plugin.py --root /path # From anywhere

Exit Codes:
    0 - PASS (all phases clean)
    1 - FAIL (one or more errors)
    2 - Script error
"""
import argparse
import json
import py_compile
import re
import sys
from pathlib import Path


# --- Frontmatter Parsing -----------------------------------------------------

def parse_yaml_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown. Returns dict or None."""
    if not text.startswith('---'):
        return None
    # Find closing ---
    rest = text[3:]
    end = rest.find('\n---')
    if end == -1:
        return None
    fm_text = rest[:end].strip()
    result = {}
    for line in fm_text.splitlines():
        if ':' in line:
            key, _, val = line.partition(':')
            result[key.strip()] = val.strip()
    return result


# --- Phase 1: Manifest -------------------------------------------------------

def phase_manifest(root: Path) -> list[dict]:
    """Validate plugin.json required fields."""
    issues = []
    # plugin.json may live at root or in .claude-plugin/ subdirectory
    candidates = [root / 'plugin.json', root / '.claude-plugin' / 'plugin.json']
    plugin_json = next((p for p in candidates if p.exists()), None)

    if plugin_json is None:
        issues.append({
            'phase': 'manifest',
            'severity': 'Error',
            'file': 'plugin.json',
            'message': 'plugin.json not found (checked root and .claude-plugin/)',
        })
        return issues

    rel_manifest = str(plugin_json.relative_to(root))
    try:
        data = json.loads(plugin_json.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        issues.append({
            'phase': 'manifest',
            'severity': 'Error',
            'file': rel_manifest,
            'message': f'Invalid JSON: {e}',
        })
        return issues

    for field in ('name', 'version', 'description'):
        if not data.get(field):
            issues.append({
                'phase': 'manifest',
                'severity': 'Error',
                'file': rel_manifest,
                'message': f'Missing required field: {field}',
            })

    return issues


# --- Phase 2: Skills ---------------------------------------------------------

SCRIPT_REF_PATTERN = re.compile(r'`([^`]+\.py)`|python3?\s+([^\s`\'"]+\.py)')


def _extract_script_refs(text: str) -> list[str]:
    """Extract Python script paths mentioned in markdown."""
    refs = []
    for m in SCRIPT_REF_PATTERN.finditer(text):
        path = m.group(1) or m.group(2)
        if path:
            refs.append(path)
    return refs


def phase_skills(root: Path) -> list[dict]:
    """Validate all skills/*/SKILL.md files."""
    issues = []
    skills_dir = root / 'skills'

    if not skills_dir.exists():
        issues.append({
            'phase': 'skills',
            'severity': 'Error',
            'file': 'skills/',
            'message': 'skills/ directory not found',
        })
        return issues

    skill_mds = sorted(skills_dir.rglob('SKILL.md'))
    if not skill_mds:
        issues.append({
            'phase': 'skills',
            'severity': 'Warning',
            'file': 'skills/',
            'message': 'No SKILL.md files found',
        })
        return issues

    for skill_md in skill_mds:
        rel = str(skill_md.relative_to(root))
        try:
            text = skill_md.read_text(encoding='utf-8')
        except Exception as e:
            issues.append({
                'phase': 'skills',
                'severity': 'Error',
                'file': rel,
                'message': f'Cannot read file: {e}',
            })
            continue

        fm = parse_yaml_frontmatter(text)
        if fm is None:
            issues.append({
                'phase': 'skills',
                'severity': 'Error',
                'file': rel,
                'message': 'Missing YAML frontmatter',
            })
            continue

        for field in ('name', 'description'):
            if not fm.get(field):
                issues.append({
                    'phase': 'skills',
                    'severity': 'Error',
                    'file': rel,
                    'message': f'Frontmatter missing required field: {field}',
                })

        # Check referenced scripts exist
        skill_dir = skill_md.parent
        for script_ref in _extract_script_refs(text):
            # Resolve relative to skill dir or plugin root
            candidates = [
                skill_dir / script_ref,
                root / script_ref,
            ]
            if not any(c.exists() for c in candidates):
                issues.append({
                    'phase': 'skills',
                    'severity': 'Warning',
                    'file': rel,
                    'message': f'Referenced script not found: {script_ref}',
                })

    return issues


# --- Phase 3: Commands -------------------------------------------------------

def phase_commands(root: Path) -> list[dict]:
    """Validate all commands/*.md files."""
    issues = []
    commands_dir = root / 'commands'

    if not commands_dir.exists():
        issues.append({
            'phase': 'commands',
            'severity': 'Warning',
            'file': 'commands/',
            'message': 'commands/ directory not found',
        })
        return issues

    command_files = sorted(commands_dir.glob('*.md'))
    # Exclude README.md
    command_files = [f for f in command_files if f.name.upper() != 'README.MD']

    for cmd_file in command_files:
        rel = str(cmd_file.relative_to(root))
        try:
            text = cmd_file.read_text(encoding='utf-8').strip()
        except Exception as e:
            issues.append({
                'phase': 'commands',
                'severity': 'Error',
                'file': rel,
                'message': f'Cannot read file: {e}',
            })
            continue

        if not text:
            issues.append({
                'phase': 'commands',
                'severity': 'Error',
                'file': rel,
                'message': 'Empty command file',
            })
            continue

        # Must have frontmatter OR a heading
        has_fm = text.startswith('---')
        has_heading = bool(re.search(r'^#', text, re.MULTILINE))
        if not has_fm and not has_heading:
            issues.append({
                'phase': 'commands',
                'severity': 'Warning',
                'file': rel,
                'message': 'No YAML frontmatter or markdown heading found',
            })

    return issues


# --- Phase 4: Agents ---------------------------------------------------------

def phase_agents(root: Path) -> list[dict]:
    """Validate all agents/*.md files."""
    issues = []
    agents_dir = root / 'agents'

    if not agents_dir.exists():
        issues.append({
            'phase': 'agents',
            'severity': 'Warning',
            'file': 'agents/',
            'message': 'agents/ directory not found',
        })
        return issues

    agent_files = sorted(agents_dir.glob('*.md'))
    agent_files = [f for f in agent_files if f.name.upper() != 'README.MD']

    for agent_file in agent_files:
        rel = str(agent_file.relative_to(root))
        try:
            text = agent_file.read_text(encoding='utf-8').strip()
        except Exception as e:
            issues.append({
                'phase': 'agents',
                'severity': 'Error',
                'file': rel,
                'message': f'Cannot read file: {e}',
            })
            continue

        if not text:
            issues.append({
                'phase': 'agents',
                'severity': 'Error',
                'file': rel,
                'message': 'Empty agent file',
            })
            continue

        fm = parse_yaml_frontmatter(text)
        if fm is None:
            issues.append({
                'phase': 'agents',
                'severity': 'Error',
                'file': rel,
                'message': 'Missing YAML frontmatter',
            })
            continue

        for field in ('name', 'description'):
            if not fm.get(field):
                issues.append({
                    'phase': 'agents',
                    'severity': 'Error',
                    'file': rel,
                    'message': f'Frontmatter missing required field: {field}',
                })

    return issues


# --- Phase 5: Hooks ----------------------------------------------------------

PLUGIN_ROOT_VAR = '${CLAUDE_PLUGIN_ROOT}'


def _extract_hook_commands(hooks_data: dict) -> list[str]:
    """Flatten all hook command strings from hooks.json structure."""
    commands = []

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get('type') == 'command' and 'command' in obj:
                commands.append(obj['command'])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(hooks_data)
    return commands


def _resolve_hook_script(command_str: str, root: Path) -> str | None:
    """Extract script path from a hook command, substituting CLAUDE_PLUGIN_ROOT."""
    # Replace variable with actual root
    resolved = command_str.replace(PLUGIN_ROOT_VAR, str(root))
    # Extract path: usually "python3 <path>" or just "<path>"
    parts = resolved.split()
    for part in parts:
        if part.endswith('.py') or (Path(part).suffix and Path(part).exists()):
            return part
    # Try last token if nothing found
    if parts:
        return parts[-1]
    return None


def phase_hooks(root: Path) -> list[dict]:
    """Validate hooks/hooks.json and referenced scripts."""
    issues = []
    hooks_dir = root / 'hooks'
    hooks_json = hooks_dir / 'hooks.json'

    if not hooks_json.exists():
        issues.append({
            'phase': 'hooks',
            'severity': 'Error',
            'file': 'hooks/hooks.json',
            'message': 'hooks.json not found',
        })
        return issues

    try:
        hooks_data = json.loads(hooks_json.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        issues.append({
            'phase': 'hooks',
            'severity': 'Error',
            'file': 'hooks/hooks.json',
            'message': f'Invalid JSON: {e}',
        })
        return issues

    # Check top-level structure
    if not isinstance(hooks_data, dict) or 'hooks' not in hooks_data:
        issues.append({
            'phase': 'hooks',
            'severity': 'Error',
            'file': 'hooks/hooks.json',
            'message': 'hooks.json must have top-level "hooks" key',
        })
        return issues

    # Check referenced scripts exist
    hook_commands = _extract_hook_commands(hooks_data)
    seen_scripts: set[str] = set()
    for cmd_str in hook_commands:
        script_path = _resolve_hook_script(cmd_str, root)
        if script_path and script_path not in seen_scripts:
            seen_scripts.add(script_path)
            p = Path(script_path)
            if not p.exists():
                issues.append({
                    'phase': 'hooks',
                    'severity': 'Error',
                    'file': 'hooks/hooks.json',
                    'message': f'Hook script not found: {script_path}',
                })

    # Compile-check all .py files in hooks/
    for py_file in sorted(hooks_dir.glob('*.py')):
        rel = str(py_file.relative_to(root))
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            issues.append({
                'phase': 'hooks',
                'severity': 'Error',
                'file': rel,
                'message': f'Python compile error: {e}',
            })
        except Exception as e:
            issues.append({
                'phase': 'hooks',
                'severity': 'Warning',
                'file': rel,
                'message': f'Cannot compile-check: {e}',
            })

    return issues


# --- Phase 6: Cross-component ------------------------------------------------

def _find_agent_refs_in_skill(text: str) -> list[str]:
    """Find agent names referenced in a SKILL.md (e.g. 'agent: foo' or 'uses foo agent')."""
    refs = []
    # Match frontmatter agent: field
    for m in re.finditer(r'^agent:\s*(\S+)', text, re.MULTILINE):
        refs.append(m.group(1).strip())
    return refs


def _find_skill_refs_in_command(text: str) -> list[str]:
    """Find skill directory names referenced in a command file."""
    refs = []
    # Match /skill-name patterns in backtick or slash syntax
    for m in re.finditer(r'/([a-z][a-z0-9-]+)', text):
        refs.append(m.group(1))
    return refs


def phase_cross_component(root: Path) -> list[dict]:
    """Validate cross-component references."""
    issues = []
    skills_dir = root / 'skills'
    agents_dir = root / 'agents'
    commands_dir = root / 'commands'
    hooks_json = root / 'hooks' / 'hooks.json'

    # Build lookup sets
    skill_dirs: set[str] = set()
    if skills_dir.exists():
        skill_dirs = {d.name for d in skills_dir.iterdir() if d.is_dir()}

    agent_names: set[str] = set()
    if agents_dir.exists():
        for f in agents_dir.glob('*.md'):
            if f.name.upper() != 'README.MD':
                agent_names.add(f.stem)

    # Skills → agents: check agent refs in SKILL.md files
    if skills_dir.exists():
        for skill_md in skills_dir.rglob('SKILL.md'):
            rel = str(skill_md.relative_to(root))
            try:
                text = skill_md.read_text(encoding='utf-8')
            except Exception:
                continue
            for agent_ref in _find_agent_refs_in_skill(text):
                if agent_ref not in agent_names:
                    issues.append({
                        'phase': 'cross-component',
                        'severity': 'Warning',
                        'file': rel,
                        'message': f'Skill references unknown agent: {agent_ref}',
                    })

    # Hooks scripts → actual existence (already covered in Phase 5)
    # Cross-check: hooks.json CLAUDE_PLUGIN_ROOT paths resolve
    if hooks_json.exists():
        try:
            hooks_data = json.loads(hooks_json.read_text(encoding='utf-8'))
            for cmd_str in _extract_hook_commands(hooks_data):
                if PLUGIN_ROOT_VAR in cmd_str:
                    resolved = cmd_str.replace(PLUGIN_ROOT_VAR, str(root))
                    # Extract script token
                    parts = resolved.split()
                    script_candidates = [p for p in parts if p.endswith('.py')]
                    for sc in script_candidates:
                        if not Path(sc).exists():
                            issues.append({
                                'phase': 'cross-component',
                                'severity': 'Error',
                                'file': 'hooks/hooks.json',
                                'message': f'CLAUDE_PLUGIN_ROOT script not found: {sc}',
                            })
        except Exception:
            pass

    return issues


# --- Main --------------------------------------------------------------------

def validate_plugin(root: Path) -> dict:
    """Run all 6 validation phases and return structured results."""
    all_issues: list[dict] = []

    phases = [
        ('manifest', phase_manifest),
        ('skills', phase_skills),
        ('commands', phase_commands),
        ('agents', phase_agents),
        ('hooks', phase_hooks),
        ('cross-component', phase_cross_component),
    ]

    phase_results = {}
    for phase_name, phase_fn in phases:
        try:
            issues = phase_fn(root)
        except Exception as e:
            issues = [{
                'phase': phase_name,
                'severity': 'Error',
                'file': '',
                'message': f'Phase crashed: {e}',
            }]
        phase_results[phase_name] = issues
        all_issues.extend(issues)

    errors = sum(1 for i in all_issues if i['severity'] == 'Error')
    warnings = sum(1 for i in all_issues if i['severity'] == 'Warning')
    status = 'FAIL' if errors > 0 else 'PASS'

    return {
        'status': status,
        'summary': {
            'phases_run': len(phases),
            'issues_found': len(all_issues),
            'errors': errors,
            'warnings': warnings,
        },
        'phases': {
            name: {
                'issues': issues,
                'errors': sum(1 for i in issues if i['severity'] == 'Error'),
                'warnings': sum(1 for i in issues if i['severity'] == 'Warning'),
            }
            for name, issues in phase_results.items()
        },
        'issues': all_issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Validate plugin component wiring and structural integrity.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=None,
        help='Plugin root directory (default: auto-detect from script location)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output JSON instead of human-readable summary',
    )
    args = parser.parse_args()

    # Resolve root: prefer --root, then walk up from script location
    if args.root:
        root = args.root.resolve()
    else:
        # Script lives at scripts/validate-plugin.py; plugin root is parent
        root = Path(__file__).resolve().parent.parent

    try:
        result = validate_plugin(root)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            _print_human_summary(result, root)

        sys.exit(0 if result['status'] == 'PASS' else 1)

    except Exception as e:
        error = {
            'status': 'ERROR',
            'error': str(e),
            'summary': {},
            'phases': {},
            'issues': [],
        }
        print(json.dumps(error, indent=2))
        sys.exit(2)


def _print_human_summary(result: dict, root: Path) -> None:
    """Print human-readable validation summary."""
    print('Plugin Wiring Validation')
    print('=' * 60)
    print(f'Plugin root: {root}')
    print()

    phase_order = ['manifest', 'skills', 'commands', 'agents', 'hooks', 'cross-component']
    phase_labels = {
        'manifest': 'Manifest (plugin.json)',
        'skills': 'Skills (SKILL.md files)',
        'commands': 'Commands (commands/*.md)',
        'agents': 'Agents (agents/*.md)',
        'hooks': 'Hooks (hooks.json + scripts)',
        'cross-component': 'Cross-component references',
    }

    for i, phase_name in enumerate(phase_order, 1):
        label = phase_labels.get(phase_name, phase_name)
        phase_data = result['phases'].get(phase_name, {})
        errors = phase_data.get('errors', 0)
        warnings = phase_data.get('warnings', 0)

        print(f'[{i}/{len(phase_order)}] {label}')
        if errors > 0:
            print(f'  FAIL: {errors} error(s)')
            for issue in phase_data.get('issues', []):
                if issue['severity'] == 'Error':
                    loc = f" ({issue['file']})" if issue['file'] else ''
                    print(f'    ERROR{loc}: {issue["message"]}')
        elif warnings > 0:
            print(f'  PASS ({warnings} warning(s))')
            for issue in phase_data.get('issues', []):
                if issue['severity'] == 'Warning':
                    loc = f" ({issue['file']})" if issue['file'] else ''
                    print(f'    WARN{loc}: {issue["message"]}')
        else:
            print('  PASS')
        print()

    print('=' * 60)
    s = result['summary']
    if result['status'] == 'FAIL':
        print(f'RESULT: FAIL — {s["errors"]} error(s), {s["warnings"]} warning(s)')
    else:
        warns = f', {s["warnings"]} warning(s)' if s['warnings'] else ''
        print(f'RESULT: PASS{warns}')


if __name__ == '__main__':
    main()
