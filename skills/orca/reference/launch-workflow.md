# Launch Workflow - Complete Process

This document describes the complete step-by-step workflow for launching Orca with smart build detection.

## Overview

The launch process consists of 8 main steps:

1. Get repository list
2. Load branch cache
3. Check build requirements
4. Stop processes (if needed)
5. Build repositories (if needed)
6. Update branch cache
7. Launch Orca
8. Return dashboard URL

## Step-by-Step Workflow

### Step 1: Get Repository List

**Script:** `Get-ActionsRepos.ps1`

**Purpose:** Enumerate all Actions/Orca repositories

**Process:**
1. Discover dev root (see [Dev Root Discovery](#dev-root-discovery))
2. Define repository configurations (embedded)
3. Filter to existing repos
4. Return list of PSCustomObjects

**Output:**
```powershell
@(
    [PSCustomObject]@{ Name="orca"; Path="D:\dev\orca"; BuildType="dotnet"; ... },
    [PSCustomObject]@{ Name="actions.api"; Path="D:\dev\actions.api"; BuildType="dotnet"; ... },
    # ... 9 more repos
)
```

**Console Output:**
```
Getting repository list...
  [OK] Found 11 repositories
```

---

### Step 2: Load Branch Cache

**Script:** `Get-BranchCache.ps1`

**Purpose:** Load previously built branch names

**Process:**
1. Get cache path: `$env:USERPROFILE\.claude-orca\branch-cache`
2. If exists, read file
3. Parse lines: `<repo>:<branch>`
4. Return hashtable

**Output:**
```powershell
@{
    "orca" = "main"
    "actions.api" = "feature/test"
    "actions.manager" = "develop"
}
```

**Console Output:**
```
Checking branch cache...
  [OK] Loaded cache (11 entries)
```

**First Run:** Returns empty hashtable (no cache file yet)

---

### Step 3: Check Build Requirements

**Script:** `Check-BuildRequired.ps1` (called for each repo)

**Purpose:** Determine which repos need building

**Process (per repo):**

1. **Get Current Branch:**
   ```powershell
   Push-Location $repo.Path
   $currentBranch = git rev-parse --abbrev-ref HEAD
   Pop-Location
   ```

2. **Compare with Cache:**
   ```powershell
   if ($currentBranch -ne $branchCache[$repo.Name]) {
       return "BranchChanged"
   }
   ```

3. **Check Build Output:**
   ```powershell
   $binPath = Join-Path $repo.Path $repo.BinPath
   if (!(Test-Path $binPath)) {
       return "NoBuildOutput"
   }
   ```

4. **Find Newest DLL:**
   ```powershell
   $newestDll = Get-ChildItem $binPath -Filter "*.dll" -Recurse |
       Sort-Object LastWriteTime -Descending |
       Select-Object -First 1
   ```

5. **Check Source Files:**
   ```powershell
   $newerSource = Get-ChildItem $repo.Path -Include @("*.cs","*.csproj",...) |
       Where-Object { $_.LastWriteTime -gt $newestDll.LastWriteTime }
   ```

6. **Return Decision:**
   ```powershell
   [PSCustomObject]@{
       BuildRequired = $true/$false
       Reason = "BranchChanged"|"NoBuildOutput"|"SourceNewer"|"UpToDate"
       CurrentBranch = "main"
       CachedBranch = "main"
   }
   ```

**Console Output:**
```
Checking build requirements...
  [BUILD] orca: BranchChanged
  [OK] actions.api: Up to date
  [BUILD] express-web-api: SourceNewer
  [OK] express-comm: Up to date
  ...
```

**Result:** List of repos requiring builds

---

### Step 4: Stop Processes (Conditional)

**Script:** `Stop-ActionsProcesses.ps1`

**Trigger:** Only if ANY repo needs building

**Purpose:** Prevent file locking during builds

**Process:**
1. Define process names:
   ```powershell
   @("Orca.AppHost", "dotnet", "eyeShareComm", "w3wp", ...)
   ```

2. Find and kill each:
   ```powershell
   Get-Process -Name $processName | Stop-Process -Force
   ```

3. Wait for termination:
   ```powershell
   Start-Sleep -Seconds 2
   ```

**Console Output:**
```
Stopping Actions/Orca processes...
  [OK] Stopped 3 process(es)
```

**Skip If:** No builds needed (processes can keep running)

---

### Step 5: Build Repositories (Conditional)

**Script:** `Build-Solution.ps1` (called for each repo needing build)

**Trigger:** Only for repos marked for build in Step 3

**Process (per repo):**

1. **Get Solution Path:**
   ```powershell
   $solutionPath = Join-Path $repo.Path $repo.SolutionPath
   ```

2. **Choose Build Tool:**
   ```powershell
   if ($repo.BuildType -eq "dotnet") {
       dotnet build "$solutionPath" -c Debug -v q
   } elseif ($repo.BuildType -eq "msbuild") {
       & "C:\...\MSBuild.exe" "$solutionPath" /p:Configuration=Debug /verbosity:minimal
   }
   ```

3. **Check Exit Code:**
   ```powershell
   if ($LASTEXITCODE -ne 0) {
       throw "Build failed"
   }
   ```

**Console Output:**
```
Building 2 repository/repositories...
Building orca.sln (dotnet)...
  [OK] Build succeeded
Building EyeShare.sln (msbuild)...
  [OK] Build succeeded
```

**Error Handling:** Throws on first build failure, stops workflow

---

### Step 6: Update Branch Cache

**Script:** `Update-BranchCache.ps1`

**Trigger:** After successful builds (if any repos built)

**Purpose:** Record current branch names for next run

**Process:**
1. Collect current branches from Step 3:
   ```powershell
   $currentBranches = @{
       "orca" = "main"
       "actions.api" = "feature/test"
       # ... all repos
   }
   ```

2. Write to cache file:
   ```powershell
   $lines = @()
   foreach ($repo in $currentBranches.Keys) {
       $lines += "$repo:$($currentBranches[$repo])"
   }
   Set-Content "$env:USERPROFILE\.claude-orca\branch-cache" -Value $lines
   ```

**Console Output:**
```
Updating branch cache...
  [OK] Branch cache updated
```

**Skip If:** No builds occurred

---

### Step 7: Launch Orca

**Command:** `cd /d/dev/orca/Orca.AppHost && dotnet run --no-build`

**Execution:** Claude Code Bash tool with `run_in_background: true`

**Process:**
1. Change to Orca.AppHost directory
2. Run dotnet with `--no-build` flag
3. Background execution (timeout: 600000ms = 10 minutes)
4. Return shell ID for monitoring

**Console Output:**
```
Launching Orca...
  Use BashOutput to monitor logs
  Use KillShell or Stop-ActionsProcesses to stop

[Shell ID returned for monitoring]
```

**Why --no-build?**
- Binaries already built in Step 5
- Avoids rebuilding during launch
- Faster startup

---

### Step 8: Monitor for Dashboard URL

**Tool:** BashOutput (to read shell output)

**Process:**
1. Wait ~10-15 seconds for startup
2. Read bash output:
   ```
   BashOutput(shell_id)
   ```

3. Look for URL pattern:
   ```
   Login to the dashboard at https://localhost:17206/login?t=<token>
   ```

4. Extract and display URL

**Dashboard URL:**
- **Protocol:** HTTPS
- **Port:** Typically 17206 (may vary)
- **Path:** `/login`
- **Token:** Unique per launch
- **Example:** `https://localhost:17206/login?t=CfDJ8A...`

---

## Execution Paths

### Path 1: No Builds Needed

```
1. Get repos (11 found)
2. Load cache (11 entries)
3. Check builds → All up-to-date
4. Skip process stop
5. Skip builds
6. Skip cache update
7. Launch Orca (--no-build)
8. Monitor for URL

Total time: ~15 seconds
```

### Path 2: Some Repos Need Building

```
1. Get repos (11 found)
2. Load cache (11 entries)
3. Check builds → 2 need building
4. Stop processes (3 stopped)
5. Build 2 repos (~60 seconds)
6. Update cache
7. Launch Orca (--no-build)
8. Monitor for URL

Total time: ~90 seconds
```

### Path 3: Branch Changed (Force Rebuild)

```
1. Get repos (11 found)
2. Load cache (11 entries)
3. Check builds → Branch changed on 1 repo
4. Stop processes (3 stopped)
5. Build 1 repo (~30 seconds)
6. Update cache (update branch)
7. Launch Orca (--no-build)
8. Monitor for URL

Total time: ~60 seconds
```

### Path 4: First Run (No Cache)

```
1. Get repos (11 found)
2. Load cache (empty)
3. Check builds → Timestamp-based only
4. If builds needed:
   a. Stop processes
   b. Build affected repos
   c. Create cache (first time)
5. Launch Orca
6. Monitor for URL

Total time: Varies (0-120 seconds)
```

## Dev Root Discovery

**Script:** `Get-DevRoot.ps1`

**Strategies (in order):**

1. **Environment Variable:**
   ```powershell
   if ($env:DEV_ROOT -and (Test-Path $env:DEV_ROOT)) {
       return $env:DEV_ROOT
   }
   ```

2. **Upward Search:**
   ```powershell
   $dir = Get-Location
   while ($dir) {
       if (Test-Path "$dir\resolve.dev.resources") {
           return $dir
       }
       $dir = Split-Path -Parent $dir
   }
   ```

3. **Common Locations:**
   ```powershell
   foreach ($location in @("D:\dev", "C:\dev", "C:\source\resolve")) {
       if (Test-Path "$location\resolve.dev.resources") {
           return $location
       }
   }
   ```

4. **Fallback:**
   ```powershell
   return "D:\dev"
   ```

## Error Handling

### Build Failure

**Trigger:** Build exit code ≠ 0

**Behavior:**
- Stop workflow immediately
- Display build output
- Throw exception
- Don't update cache
- Don't launch Orca

**Recovery:**
- Fix compilation errors
- Rerun launch

### Process Stop Failure

**Trigger:** Process cannot be killed

**Behavior:**
- Continue anyway (best effort)
- Build may fail with "file in use"

**Recovery:**
- Manually kill via Task Manager
- Rerun launch

### Git Command Failure

**Trigger:** Not a git repo or git not available

**Behavior:**
- Treat as non-git repo
- Skip branch checks
- Use timestamp logic only

### Cache File Issues

**Trigger:** Cannot read/write cache

**Behavior:**
- Continue without cache
- Branch tracking disabled
- Use timestamp logic only

## Performance Metrics

### Check Phase (~5 seconds)
- Get repos: <100ms
- Load cache: <10ms
- Check builds (11 repos): ~500ms
- Overhead: ~4 seconds

### Build Phase (varies)
- Single dotnet repo: 20-40 seconds
- Single msbuild repo: 30-60 seconds
- All repos: 3-5 minutes

### Launch Phase (~15 seconds)
- Process stop: 2 seconds
- Orca startup: 10-15 seconds
- Dashboard ready: +2 seconds

## Related Documentation

- [Build Detection](./build-detection.md) - Build requirement logic
- [Branch Tracking](./branch-tracking.md) - Branch cache details
- [Repository Mappings](./repo-mappings.md) - All repo configurations
- [Troubleshooting](./troubleshooting.md) - Common issues

---

**Last Updated:** 2025-11-03
