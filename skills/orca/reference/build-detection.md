# Build Detection - Smart Build System

This document explains how the orca skill determines when builds are necessary.

## Overview

The build detection system uses three checks to determine if a repository needs rebuilding:

1. **Branch Change Detection** - Has the branch switched since last build?
2. **Build Output Existence** - Do compiled binaries exist?
3. **Timestamp Comparison** - Are source files newer than binaries?

A build is required if **ANY** of these conditions is true.

## Check 1: Branch Change Detection

### Why Branch Detection?

When you switch branches, existing build output may still be present on disk and appear up-to-date by timestamp, but it's compiled from the **previous branch's code**. This causes incompatible binaries that lead to runtime errors.

**Example Problem:**
```
1. On branch "main" - Build succeeds
2. Switch to "feature/new-api" - Code has breaking changes
3. Build check sees binaries from "main" - Appears up-to-date
4. Launch fails - Running "main" binaries with "feature/new-api" code
```

### How It Works

**Step 1: Get Current Branch**
```powershell
cd $repoPath
$currentBranch = git rev-parse --abbrev-ref HEAD
```

**Step 2: Read Branch Cache**
```
$branchCache = @{
    "orca" = "main"
    "actions.api" = "feature/test"
}
```

**Step 3: Compare**
```powershell
if ($currentBranch -ne $branchCache[$repoName]) {
    return "Branch changed - build required"
}
```

### Branch Cache Location

**Path:** `$env:USERPROFILE\.claude-orca\branch-cache`

**Format:**
```
orca:main
actions.api:feature/content-bridge
actions.manager:develop
express-web-api:master
```

Each line: `<repo-name>:<branch-name>`

### Cache Updates

**When Updated:** After successful builds

**How:**
```powershell
$currentBranches = @{
    "orca" = "main"
    "actions.api" = "feature/test"
}
& Update-BranchCache.ps1 -BranchInfo $currentBranches
```

## Check 2: Build Output Existence

### Why Check Existence?

Before checking timestamps, verify binaries actually exist:
- Never built before
- `bin` folders deleted (cleanup)
- Build failed previously

### Repository Types

**Dotnet Projects (.NET Core/9):**
- Build to: `{ProjectDir}/bin/Debug/net9.0/`
- Example: `orca/Orca.AppHost/bin/Debug/net9.0/*.dll`

**MSBuild Projects (.NET Framework):**
- Build to: `{ProjectDir}/bin/`
- Example: `express-web-api/AyehuWebApi/EyeShare.Api/bin/*.dll`

### Detection Logic

```powershell
$binPath = Join-Path $repoPath $RepoInfo.BinPath

# Check if directory exists
if (!(Test-Path $binPath)) {
    return "No build output directory - build required"
}

# Check if any DLLs exist
$dlls = Get-ChildItem -Path $binPath -Filter "*.dll" -Recurse
if ($dlls.Count -eq 0) {
    return "No DLLs found - build required"
}
```

### Common Scenarios

**First Build:**
```
bin/ directory doesn't exist
→ Build required
```

**After Clean:**
```
bin/ exists but empty
→ Build required
```

**Partial Build:**
```
bin/ exists with some DLLs
→ Check timestamps (next step)
```

## Check 3: Timestamp Comparison

### Why Timestamps?

Even if binaries exist, they may be outdated. Source files modified after the last build require rebuilding.

### How It Works

**Step 1: Find Newest Binary**
```powershell
$newestDll = Get-ChildItem -Path $binPath -Filter "*.dll" -Recurse |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

$buildTime = $newestDll.LastWriteTime
```

**Step 2: Find Source Files Newer Than Binary**
```powershell
$sourceFiles = Get-ChildItem -Path $repoPath -Include @(
    "*.cs", "*.vb", "*.csproj", "*.vbproj", "*.sln"
) -Recurse |
Where-Object {
    $_.FullName -notlike "*\bin\*" -and
    $_.FullName -notlike "*\obj\*" -and
    $_.LastWriteTime -gt $buildTime
}
```

**Step 3: Decision**
```powershell
if ($sourceFiles) {
    return "Source files newer than build - build required"
} else {
    return "Build is up to date"
}
```

### Source File Types

**Included in Check:**
- `*.cs` - C# source files
- `*.vb` - Visual Basic source files
- `*.csproj` - C# project files
- `*.vbproj` - VB project files
- `*.sln` - Solution files

**Excluded from Check:**
- `*.md` - Markdown documentation
- `*.txt` - Text files
- `*.json` - Configuration (unless project files)
- `*.xml` - XML docs
- Files in `bin/` or `obj/` directories

### Why Exclude bin/obj?

- `bin/` contains build output (not source)
- `obj/` contains intermediate files (not source)
- Including them would create false positives

## Decision Flow

```
Start
  ↓
Branch changed?
  ├─ Yes → Build Required (Reason: BranchChanged)
  └─ No → Continue
        ↓
Build output exists?
  ├─ No → Build Required (Reason: NoBuildOutput)
  └─ Yes → Continue
        ↓
Source newer than build?
  ├─ Yes → Build Required (Reason: SourceNewer)
  └─ No → Build NOT Required (Reason: UpToDate)
```

## Repository-Specific Examples

### Orca (Dotnet)

**Bin Path:** `Orca.AppHost/bin/Debug/net9.0/`

**Check:**
1. Current branch: `main`
2. Cached branch: `main` ✓ Same
3. Find DLLs: `Orca.AppHost.dll` found ✓
4. DLL time: `2025-11-03 10:00:00`
5. Source check: All `.cs` files older ✓
6. Result: **Build NOT Required**

### actions.api (Dotnet)

**Bin Path:** `src/bin/Debug/net9.0/`

**Check:**
1. Current branch: `feature/new-api`
2. Cached branch: `main` ✗ Changed
3. Result: **Build Required (BranchChanged)**

### express-web-api (MSBuild)

**Bin Path:** `AyehuWebApi/EyeShare.Api/bin/`

**Check:**
1. Current branch: `master`
2. Cached branch: `master` ✓ Same
3. Find DLLs: `EyeShare.Api.dll` found ✓
4. DLL time: `2025-11-02 15:00:00`
5. Source check: `SomeController.cs` modified `2025-11-03 09:00:00` ✗ Newer
6. Result: **Build Required (SourceNewer)**

## Performance Optimization

### Fast Checks First

1. **Branch check** (fastest - simple string compare)
2. **Existence check** (fast - directory/file checks)
3. **Timestamp check** (slower - walks directory tree)

If early checks fail, later checks are skipped.

### Timestamp Caching

Branch cache prevents unnecessary timestamp checks:
- Branch unchanged → Trust timestamps
- Branch changed → Skip timestamps, rebuild anyway

### Limited Source Scan

Only scans for first 5 newer files:
```powershell
Select-Object -First 5
```

Don't need to find **all** newer files, just **any** newer file.

## Troubleshooting

### "Build required every time"

**Symptom:** Always rebuilds even when no changes

**Causes:**
1. Branch cache not updating
2. Clock skew (file times in future)
3. Build process touching source files

**Solutions:**
- Check branch cache file exists
- Verify file timestamps (`Get-Item file.cs | Select LastWriteTime`)
- Check build doesn't modify source

### "Build not triggered when needed"

**Symptom:** Running with outdated binaries

**Causes:**
1. Source file not detected (wrong extension)
2. Timestamp precision issues
3. Branch cache stale

**Solutions:**
- Verify file extension in source list
- Force rebuild: `"launch orca with rebuild"`
- Delete branch cache and retry

### "False positives from documentation changes"

**Symptom:** Rebuilds when only `.md` files changed

**Cause:** Incorrect source file detection

**Solution:** Verify exclusion list includes `.md`

## Script Reference

**Main Script:** `Check-BuildRequired.ps1`

**Parameters:**
- `RepoInfo` - Repository configuration
- `BranchCache` - Cached branch names

**Returns:**
```powershell
[PSCustomObject]@{
    BuildRequired = $true/$false
    Reason = "BranchChanged"|"NoBuildOutput"|"SourceNewer"|"UpToDate"
    CurrentBranch = "main"
    CachedBranch = "main"
}
```

## Related Documentation

- [Branch Tracking](./branch-tracking.md) - Branch cache details
- [Repository Mappings](./repo-mappings.md) - All repo configurations
- [Launch Workflow](./launch-workflow.md) - Complete process

---

**Last Updated:** 2025-11-03
