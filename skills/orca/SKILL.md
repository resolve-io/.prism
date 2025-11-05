---
name: orca
description: Launch Orca with smart build detection - builds if source changed OR build output missing
version: 2.1.0
---

# Orca Launch Skill

## Quick Reference

**Launch Orca:** `"launch orca"` or `"start orca"`
**Force rebuild:** `"launch orca with rebuild"`
**Skip build check:** `"launch orca without building"`

## CRITICAL: How to Execute This Skill

**DO NOT write your own PowerShell scripts.** All logic is already implemented in `Launch-Orca.ps1`.

### Step 1: Call Launch-Orca.ps1

**Standard launch (with smart build detection):**
```bash
powershell.exe -ExecutionPolicy Bypass -File "D:\dev\.prism\skills\orca\scripts\Launch-Orca.ps1"
```

**Skip build check (when user says "without building"):**
```bash
powershell.exe -ExecutionPolicy Bypass -File "D:\dev\.prism\skills\orca\scripts\Launch-Orca.ps1" -SkipBuild
```

**Force rebuild (when user says "rebuild" or "with rebuild"):**
```bash
powershell.exe -ExecutionPolicy Bypass -File "D:\dev\.prism\skills\orca\scripts\Launch-Orca.ps1" -ForceBuild
```

### Step 2: Parse the Output

`Launch-Orca.ps1` returns a PSCustomObject with:
- `Success` (bool): Whether ready to launch
- `LaunchCommand` (string): The exact command to run (e.g., "cd /d/dev/orca/Orca.AppHost && dotnet run --no-build")
- `BuiltRepos` (array): List of repos that were built
- `Message` (string): Status message

### Step 3: Launch Orca in Background

Use the Bash tool with the returned `LaunchCommand`:
```bash
Bash(command: <LaunchCommand>, run_in_background: true, timeout: 120000)
```

### Step 4: Get Dashboard URL

Wait 10-15 seconds, then use `BashOutput` to get the dashboard URL with auth token.

## What This Skill Does

Launches the Orca application with intelligent build detection:
- Detects branch changes and forces rebuilds (prevents incompatible binaries)
- Compares source file timestamps against build output
- Detects missing build output (never built or cleaned)
- Builds only when necessary (branch changed OR source newer OR no output)
- Launches Orca in background with dashboard access

## How It Works (Internally)

The `Launch-Orca.ps1` script handles:
1. Get repository list → All Actions/Orca repos
2. Check branch cache → Detect branch switches
3. Check build output → Find missing/outdated builds (using BinPath for each repo)
4. Compare timestamps → Source vs build files
5. Stop processes → If builds needed
6. Build repositories → Only affected ones
7. Update branch cache → Track current branches
8. Return launch command → For you to execute with Bash tool

## Build Detection Logic

**Build required when ANY of:**
- Branch changed (e.g., `main` → `feature/test`)
- Build output missing (bin folder empty)
- Source files newer than build output

**Build NOT required when ALL of:**
- Branch unchanged
- Build output exists with DLLs
- All source files older than build

## Repository Configuration

**Embedded Configuration** (no external dependencies):
- **Dotnet**: orca, actions.api, actions.engine, actions.manager
- **MSBuild**: express-comm, express-web-api, express-executor, etc.

All repo paths discovered dynamically from dev root.

## Cache Location

**Branch cache:** `$env:USERPROFILE\.claude-orca\branch-cache`

**Format:**
```
orca:main
actions.api:feature/content-bridge
actions.manager:develop
```

**Purpose:** Detect branch switches that require rebuilds

## Launch Workflow

### Normal Launch (with build check)

See **"CRITICAL: How to Execute This Skill"** section above for the exact commands.

Summary:
1. Call `Launch-Orca.ps1` (no parameters)
2. Script checks all repos for changes and builds if needed
3. Script returns launch command
4. Execute launch command with Bash tool in background
5. Monitor with BashOutput to get dashboard URL

### Skip Build

When user says **"without building"**:
```bash
powershell.exe -ExecutionPolicy Bypass -File "D:\dev\.prism\skills\orca\scripts\Launch-Orca.ps1" -SkipBuild
```

### Force Rebuild

When user says **"rebuild"** or **"with rebuild"**:
```bash
powershell.exe -ExecutionPolicy Bypass -File "D:\dev\.prism\skills\orca\scripts\Launch-Orca.ps1" -ForceBuild
```

## User Commands

Users may say:
- `"launch orca"` → Standard launch with smart build detection
- `"launch orca and rebuild everything"` → Force rebuild (-ForceBuild)
- `"launch orca without building"` → Skip build check (-SkipBuild)
- `"stop orca processes"` → Stop running Orca (use Stop-ActionsProcesses script)

## Dashboard Access

After launch (~10-15 seconds for startup):
- Check bash output for URL
- Format: `https://localhost:17206/login?t=<token>`
- Port may vary (check output)
- Token changes each launch

## Process Management

**Launch:** Background bash session (use `run_in_background: true`)
**Monitor:** BashOutput tool with shell ID
**Stop:** KillShell tool OR Stop-ActionsProcesses script

## Dev Root Discovery

**Automatic detection:**
1. Check `DEV_ROOT` environment variable
2. Search for `resolve.dev.resources` repo
3. Check common locations (D:\dev, C:\dev, etc.)
4. Fall back to D:\dev

**Portable across:**
- `D:\dev` (default)
- `C:\source\resolve`
- `$env:USERPROFILE\dev`
- Any location with resolve.dev.resources

## Error Handling

**"Build failed"**
- Check error output from build tool
- May be compilation errors in code
- See: [Troubleshooting Guide](./reference/troubleshooting.md)

**"Processes could not be stopped"**
- Manually kill via Task Manager
- OR use PowerShell: `Stop-Process -Name "Orca.AppHost" -Force`

**"Dev root not found"**
- Set `DEV_ROOT` environment variable
- OR ensure resolve.dev.resources exists

## Performance

**Typical Times:**
- Build check only: 2-5 seconds
- Build 1-2 repos: 30-60 seconds
- Build all repos: 2-4 minutes
- Launch after build: 10-15 seconds

**Optimization:**
- Build check uses cached branches (fast)
- Only builds changed repos (not everything)
- Parallel builds not yet implemented

## Related Skills

- [Backup Orca Database](../backup-orca-db/SKILL.md) - Backup before major changes
- [Restore Orca Database](../restore-orca-db/SKILL.md) - Restore if problems occur

## Reference Documentation

- [Build Detection Details](./reference/build-detection.md) - How smart build works
- [Branch Tracking](./reference/branch-tracking.md) - Branch cache explained
- [Repository Mappings](./reference/repo-mappings.md) - All repo configurations
- [Launch Workflow](./reference/launch-workflow.md) - Step-by-step process
- [Troubleshooting](./reference/troubleshooting.md) - Common issues

## Scripts

- `Get-DevRoot.ps1` - Dev root discovery
- `Get-ActionsRepos.ps1` - Repository list
- `Get-BranchCache.ps1` - Read branch cache
- `Update-BranchCache.ps1` - Write branch cache
- `Check-BuildRequired.ps1` - Build detection logic
- `Stop-ActionsProcesses.ps1` - Process management
- `Build-Solution.ps1` - Build wrapper
- `Launch-Orca.ps1` - Main orchestration

---

**Version:** 2.1.0
**Last Updated:** 2025-11-04

## Changelog

### v2.1.0 (2025-11-04)
- **BREAKING**: Added "CRITICAL: How to Execute This Skill" section
- Explicitly instructs to call `Launch-Orca.ps1` directly, not write custom scripts
- Added step-by-step execution guide with exact PowerShell commands
- Documented the PSCustomObject return structure
- Clarified that all build detection logic is already in the scripts
- Fixed confusion about when to use bash vs PowerShell vs writing scripts

### v2.0.0 (2025-11-03)
- Initial version with embedded scripts
- Smart build detection with branch tracking
- Support for dotnet and MSBuild projects
