---
name: orca
description: Launch Orca with smart build detection - builds if source changed OR build output missing
version: 2.0.0
---

# Orca Launch Skill

## Quick Reference

**Launch Orca:** `"launch orca"` or `"start orca"`
**Force rebuild:** `"launch orca with rebuild"`
**Skip build check:** `"launch orca without building"`

## What This Skill Does

Launches the Orca application with intelligent build detection:
- Detects branch changes and forces rebuilds (prevents incompatible binaries)
- Compares source file timestamps against build output
- Detects missing build output (never built or cleaned)
- Builds only when necessary (branch changed OR source newer OR no output)
- Launches Orca in background with dashboard access

## How It Works

1. Get repository list → All Actions/Orca repos
2. Check branch cache → Detect branch switches
3. Check build output → Find missing/outdated builds
4. Compare timestamps → Source vs build files
5. Stop processes → If builds needed
6. Build repositories → Only affected ones
7. Update branch cache → Track current branches
8. Launch Orca → Background bash session
9. Return dashboard URL → With auth token

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

```
1. Check all repos for changes
2. If changes found:
   - Stop running processes
   - Build affected repos
   - Update branch cache
3. Launch: cd /d/dev/orca/Orca.AppHost && dotnet run --no-build
4. Monitor: Use BashOutput with shell ID
```

### Skip Build

```
"launch orca without building"
- Skips all build checks
- Uses existing binaries
- Faster startup (if already built)
```

### Force Rebuild

```
"launch orca with rebuild"
- Rebuilds all repos regardless of changes
- Ensures clean build state
```

## Common Commands

```bash
# Standard launch with smart build
"launch orca"

# Force rebuild everything
"launch orca and rebuild everything"

# Skip build check (faster if already built)
"launch orca without building"

# Stop Orca
"stop orca processes"
```

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

**Version:** 2.0.0
**Last Updated:** 2025-11-03
