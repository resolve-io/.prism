# Branch Tracking System

This document explains how the orca skill tracks Git branches to detect when rebuilds are necessary.

## Why Track Branches?

**Problem:** Branch switches leave behind incompatible build artifacts

**Example:**
```
1. Checkout branch "main"
2. Build (creates bin/Debug/App.dll with "main" code)
3. Checkout branch "feature/breaking-changes"
4. Don't rebuild (bin/Debug/App.dll still has "main" code)
5. Launch app (runtime errors - wrong binaries!)
```

**Solution:** Track which branch was used for the last build, force rebuild on branch change.

## Branch Cache

### Location

**Path:** `$env:USERPROFILE\.claude-orca\branch-cache`

**Example:** `C:\Users\DanPuzon\.claude-orca\branch-cache`

### Format

Plain text file, one line per repository:

```
<repo-name>:<branch-name>
```

**Example File:**
```
orca:main
actions.api:feature/content-bridge
actions.manager:develop
actions.engine:main
express-web-api:master
express-comm:master
express-executor:master
```

### Why User Profile?

- **Survives dev root wipes** - Can delete entire `D:\dev`
- **Portable** - Works across different dev root locations
- **User-specific** - Each developer has their own cache
- **Consistent location** - Same path on all machines

## Cache Operations

### Read Cache (Get-BranchCache.ps1)

**Purpose:** Load cached branch names before build check

**Returns:**
```powershell
@{
    "orca" = "main"
    "actions.api" = "feature/test"
    "actions.manager" = "develop"
}
```

**Logic:**
```powershell
$cacheFile = "$env:USERPROFILE\.claude-orca\branch-cache"

if (Test-Path $cacheFile) {
    $lines = Get-Content $cacheFile
    foreach ($line in $lines) {
        if ($line -match "^([^:]+):(.+)$") {
            $branchCache[$matches[1]] = $matches[2]
        }
    }
}
```

### Update Cache (Update-BranchCache.ps1)

**Purpose:** Save current branch names after successful build

**Input:**
```powershell
$currentBranches = @{
    "orca" = "main"
    "actions.api" = "feature/new-api"
}
```

**Logic:**
```powershell
$lines = @()
foreach ($repo in $currentBranches.Keys) {
    $lines += "$repo:$($currentBranches[$repo])"
}
Set-Content -Path $cacheFile -Value $lines
```

## Branch Detection

### Get Current Branch

**Per Repository:**
```powershell
Push-Location $repoPath
$currentBranch = git rev-parse --abbrev-ref HEAD
Pop-Location
```

**Output Examples:**
```
main
develop
feature/new-api
hotfix/urgent-fix
release/v2.0
```

### Compare Branches

**Logic:**
```powershell
$currentBranch = "feature/test"
$cachedBranch = $branchCache["orca"]  # "main"

if ($currentBranch -ne $cachedBranch) {
    # Branch changed - force rebuild
    return "BranchChanged"
}
```

### First Run (No Cache)

**Scenario:** Branch cache doesn't exist yet

**Behavior:**
```powershell
if (!$cachedBranch) {
    # No cached branch - fall through to timestamp check
    # Build only if source is newer than binaries
}
```

First run doesn't force rebuild - uses timestamp logic instead.

## Workflow Integration

### Launch Workflow

```
1. Get repository list
2. Read branch cache ← Get-BranchCache.ps1
3. For each repo:
   a. Get current branch (git command)
   b. Compare with cached branch
   c. If different → Mark for rebuild
   d. If same → Check timestamps
4. Build marked repos
5. Update branch cache ← Update-BranchCache.ps1
6. Launch Orca
```

### Cache Update Timing

**When:** After **successful** builds

**Why:** Only update cache if build succeeded
- Failed build = old binaries still present
- Update cache = next run thinks build is up-to-date
- Result = running with old binaries

**Implementation:**
```powershell
# Build all repos
foreach ($repo in $reposNeedingBuild) {
    $result = Build-Solution $repo
    if (!$result.Success) {
        throw "Build failed - not updating cache"
    }
}

# All builds succeeded - update cache
Update-BranchCache -BranchInfo $currentBranches
```

## Common Scenarios

### Scenario 1: Switch Branch and Launch

**Steps:**
```bash
git checkout feature/new-api
"launch orca"
```

**What Happens:**
1. Read cache: `orca:main`
2. Get current: `feature/new-api`
3. Compare: `main` ≠ `feature/new-api`
4. Result: Build required (BranchChanged)
5. Build orca
6. Update cache: `orca:feature/new-api`
7. Launch

**Next Launch:** No rebuild (same branch, timestamps ok)

### Scenario 2: Make Changes on Same Branch

**Steps:**
```bash
# Edit SomeFile.cs
"launch orca"
```

**What Happens:**
1. Read cache: `orca:main`
2. Get current: `main`
3. Compare: `main` = `main` ✓
4. Check timestamps: SomeFile.cs newer than DLLs
5. Result: Build required (SourceNewer)
6. Build orca
7. Cache unchanged: Still `orca:main`
8. Launch

### Scenario 3: Launch Without Changes

**Steps:**
```bash
"launch orca"
```

**What Happens:**
1. Read cache: `orca:main`
2. Get current: `main`
3. Compare: `main` = `main` ✓
4. Check timestamps: All source older
5. Result: Build NOT required
6. Skip build
7. Launch with existing binaries

### Scenario 4: Multiple Repos, Mixed Branches

**Setup:**
```
orca: main → feature/ui
actions.api: main (no change)
express-web-api: master (no change)
```

**What Happens:**
1. Check orca: Branch changed → Build required
2. Check actions.api: Branch same → Check timestamps
3. Check express-web-api: Branch same → Check timestamps
4. Build only orca
5. Update cache: Only orca branch changes

**Result:** Selective rebuild based on branch changes

## Cache File Lifecycle

### Creation

**When:** First successful build after orca skill installation

**How:**
```powershell
# No cache file exists
$cacheFile = "$env:USERPROFILE\.claude-orca\branch-cache"

# After first build
Update-BranchCache -BranchInfo $branches
# Creates file with current branches
```

### Updates

**Frequency:** After every build (if any repo built)

**Scope:**
- Updates ALL tracked repos (not just built ones)
- Ensures cache has complete snapshot

### Deletion

**Manual:** User can delete to force full rebuild

**Effect:**
```bash
rm "$env:USERPROFILE\.claude-orca\branch-cache"
"launch orca"
# No branch cache → Uses timestamp logic only
# Rebuilds if needed, recreates cache
```

### Corruption

**Symptoms:**
- Build always required
- Branch detection not working

**Fix:**
```bash
# Delete and recreate
rm "$env:USERPROFILE\.claude-orca\branch-cache"
"launch orca"
```

## Branch Names

### Supported Formats

**Standard:**
- `main`
- `develop`
- `master`

**Feature Branches:**
- `feature/new-api`
- `feature/PLAT-1234`

**Release Branches:**
- `release/v2.0`
- `release/2.0.0`

**Hotfix Branches:**
- `hotfix/urgent-fix`
- `hotfix/PLAT-5678`

**All Git branch names are supported** - no restrictions

### Special Cases

**Detached HEAD:**
```bash
git checkout abc123
# Returns: HEAD
```

**Cached:** `main`
**Current:** `HEAD`
**Result:** Branch changed → Rebuild

**Tags:**
```bash
git checkout v2.0.0
# Returns: v2.0.0
```

**Cached:** `main`
**Current:** `v2.0.0`
**Result:** Branch changed → Rebuild

## Performance

### Read Performance

**Cache Read:** <1ms (small text file)

**Git Command:** 10-50ms per repo
```powershell
git rev-parse --abbrev-ref HEAD
```

**Total:** ~500ms for 10 repos (parallel not implemented)

### Cache Size

**Typical:**
- 10 repos × 30 bytes/line = 300 bytes
- Negligible disk usage

**Growth:** Linear with repo count

## Troubleshooting

### "Build required every launch"

**Symptom:** Always rebuilds, even without changes

**Possible Causes:**

1. **Branch cache not updating**
   ```powershell
   # Check if file exists
   Test-Path "$env:USERPROFILE\.claude-orca\branch-cache"

   # Check contents
   Get-Content "$env:USERPROFILE\.claude-orca\branch-cache"
   ```

2. **Git command failing**
   ```powershell
   cd D:\dev\orca
   git rev-parse --abbrev-ref HEAD
   # Should return branch name
   ```

3. **Cache permissions**
   ```powershell
   $cacheFile = "$env:USERPROFILE\.claude-orca\branch-cache"
   icacls $cacheFile
   ```

### "Branch change not detected"

**Symptom:** Switched branches but no rebuild triggered

**Possible Causes:**

1. **Cache has wrong branch**
   ```powershell
   # Check cached branch
   $cache = Get-Content "$env:USERPROFILE\.claude-orca\branch-cache"
   $cache | Select-String "orca:"
   ```

2. **Git not returning branch name**
   ```powershell
   cd D:\dev\orca
   git rev-parse --abbrev-ref HEAD
   ```

### "Cache file corrupted"

**Symptom:** Error reading cache

**Fix:**
```powershell
# Delete cache
Remove-Item "$env:USERPROFILE\.claude-orca\branch-cache" -Force

# Relaunch
"launch orca"
# Cache will be recreated
```

## Related Documentation

- [Build Detection](./build-detection.md) - Complete build logic
- [Repository Mappings](./repo-mappings.md) - All tracked repos
- [Troubleshooting](./troubleshooting.md) - Common issues

---

**Last Updated:** 2025-11-03
