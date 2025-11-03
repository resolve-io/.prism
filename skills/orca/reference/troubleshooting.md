# Troubleshooting Guide - Orca Launch Issues

This document provides solutions to common issues when launching Orca.

## Quick Diagnostics

### Health Check Script

```powershell
Write-Host "=== Orca Launch Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check 1: Dev root discovery
Write-Host "1. Dev Root:" -ForegroundColor Yellow
$devRoot = & .\Get-DevRoot.ps1
if (Test-Path "$devRoot\resolve.dev.resources") {
    Write-Host "   [OK] Found: $devRoot" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] Invalid dev root: $devRoot" -ForegroundColor Red
}

# Check 2: Repositories
Write-Host "2. Repositories:" -ForegroundColor Yellow
$repos = & .\Get-ActionsRepos.ps1
Write-Host "   [OK] Found $($repos.Count) repositories" -ForegroundColor Green
foreach ($repo in $repos | Select-Object -First 3) {
    Write-Host "      - $($repo.Name)" -ForegroundColor Gray
}

# Check 3: Branch cache
Write-Host "3. Branch Cache:" -ForegroundColor Yellow
$cacheFile = "$env:USERPROFILE\.claude-orca\branch-cache"
if (Test-Path $cacheFile) {
    $lines = Get-Content $cacheFile
    Write-Host "   [OK] Cache exists ($($lines.Count) entries)" -ForegroundColor Green
} else {
    Write-Host "   [OK] No cache (first run)" -ForegroundColor Yellow
}

# Check 4: Build tools
Write-Host "4. Build Tools:" -ForegroundColor Yellow
try {
    $dotnetVersion = dotnet --version
    Write-Host "   [OK] dotnet: $dotnetVersion" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] dotnet not found" -ForegroundColor Red
}

$msbuildPath = "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe"
if (Test-Path $msbuildPath) {
    Write-Host "   [OK] MSBuild found" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] MSBuild not found" -ForegroundColor Red
}
```

## Common Issues

### Issue 1: "Dev root not found"

**Error Message:**
```
Dev root not found or resolve.dev.resources missing
```

**Causes:**
1. Not running from within dev directory
2. `DEV_ROOT` environment variable not set
3. resolve.dev.resources repo missing

**Solutions:**

**Solution 1: Set Environment Variable**
```powershell
# Temporary (current session)
$env:DEV_ROOT = "D:\dev"

# Permanent (system-wide)
[System.Environment]::SetEnvironmentVariable("DEV_ROOT", "D:\dev", "User")
```

**Solution 2: Run from Dev Directory**
```bash
cd /d/dev/orca
"launch orca"
```

**Solution 3: Check resolve.dev.resources Exists**
```powershell
Test-Path "D:\dev\resolve.dev.resources"
# Should return True
```

---

### Issue 2: "Build failed for <repo>"

**Error Message:**
```
Build failed for orca: dotnet build failed with exit code 1
```

**Causes:**
1. Compilation errors in code
2. Missing dependencies
3. NuGet package restore failed
4. Build tools not installed

**Solutions:**

**Solution 1: Check Build Output**
```powershell
# Manual build to see full errors
cd D:\dev\orca
dotnet build
```

**Solution 2: Restore NuGet Packages**
```powershell
cd D:\dev\orca
dotnet restore
```

**Solution 3: Clean and Rebuild**
```powershell
cd D:\dev\orca
dotnet clean
dotnet build
```

**Solution 4: Check .NET SDK**
```powershell
dotnet --version
# Should be 9.0.x or higher for .NET 9 projects
```

---

### Issue 3: "Processes could not be stopped"

**Error Message:**
```
Failed to stop process: Access denied
```

**Causes:**
1. Process running as different user
2. Process locked by antivirus
3. Process in hung state

**Solutions:**

**Solution 1: Manual Kill via Task Manager**
```
1. Open Task Manager (Ctrl+Shift+Esc)
2. Find processes:
   - Orca.AppHost
   - dotnet
   - eyeShareComm*
   - w3wp
3. End Task for each
```

**Solution 2: Force Kill via PowerShell**
```powershell
Get-Process | Where-Object {
    $_.Name -like "*Orca*" -or
    $_.Name -like "*eyeShare*" -or
    $_.Name -eq "dotnet"
} | Stop-Process -Force
```

**Solution 3: Run as Administrator**
```
Right-click PowerShell → Run as Administrator
& .\Launch-Orca.ps1
```

---

### Issue 4: "Build required every time"

**Symptom:** Always rebuilds even when no changes made

**Causes:**
1. Branch cache not updating
2. Build process touching source files
3. Clock skew (file times in future)
4. Git not returning branch name

**Solutions:**

**Solution 1: Check Branch Cache**
```powershell
Get-Content "$env:USERPROFILE\.claude-orca\branch-cache"

# Should show current branches
# If missing or wrong, delete and recreate:
Remove-Item "$env:USERPROFILE\.claude-orca\branch-cache"
"launch orca"
```

**Solution 2: Check Git Branch Command**
```powershell
cd D:\dev\orca
git rev-parse --abbrev-ref HEAD
# Should return branch name (e.g., "main")
```

**Solution 3: Check File Timestamps**
```powershell
# Check if source files have future timestamps
cd D:\dev\orca
Get-ChildItem -Recurse -Filter "*.cs" |
    Where-Object { $_.LastWriteTime -gt (Get-Date) } |
    Select-Object FullName, LastWriteTime
```

---

### Issue 5: "Branch change not detected"

**Symptom:** Switched branches but no rebuild triggered

**Causes:**
1. Cache has stale branch name
2. Git command failing
3. Cache file corrupted

**Solutions:**

**Solution 1: Verify Current Branch**
```powershell
cd D:\dev\orca
git branch --show-current
```

**Solution 2: Check Cached Branch**
```powershell
$cache = Get-Content "$env:USERPROFILE\.claude-orca\branch-cache"
$cache | Select-String "orca:"
# Should match current branch
```

**Solution 3: Force Cache Rebuild**
```powershell
Remove-Item "$env:USERPROFILE\.claude-orca\branch-cache" -Force
"launch orca"
# Cache will be recreated with current branches
```

**Solution 4: Force Rebuild**
```
"launch orca with rebuild"
# Ignores cache, rebuilds everything
```

---

### Issue 6: "Dashboard URL not found"

**Symptom:** Orca launches but no URL displayed

**Causes:**
1. Orca still starting up (too early)
2. Orca failed to start (port conflict)
3. Output not captured

**Solutions:**

**Solution 1: Wait Longer**
```
Wait 15-20 seconds after launch
Use BashOutput to check logs
```

**Solution 2: Check Orca Logs**
```
Use BashOutput with shell ID
Look for errors:
- Port already in use
- Database connection failed
- Configuration errors
```

**Solution 3: Check Port**
```powershell
# Check if port 17206 is in use
netstat -ano | findstr :17206

# If in use, kill the process
$pid = # PID from netstat
Stop-Process -Id $pid -Force
```

**Solution 4: Manual URL**
```
If token is known:
https://localhost:17206/login?t=<token>

Default (may work without token):
https://localhost:17206/
```

---

### Issue 7: "MSBuild not found"

**Error Message:**
```
MSBuild not found at: C:\Program Files\...\MSBuild.exe
```

**Causes:**
1. Visual Studio not installed
2. Different VS version/edition
3. Build Tools not installed

**Solutions:**

**Solution 1: Install Visual Studio**
```
Download Visual Studio 2022 Professional
Install with .NET desktop development workload
```

**Solution 2: Update MSBuild Path**
Edit `Build-Solution.ps1`:
```powershell
# Find your MSBuild location
$msbuildPath = "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"
```

**Solution 3: Use Build Tools**
```
Download: Visual Studio Build Tools 2022
Install: MSBuild component
```

---

### Issue 8: "Repository not found"

**Error Message:**
```
Repository path does not exist: D:\dev\actions.api
```

**Causes:**
1. Repository not cloned
2. Wrong dev root
3. Repository in different location

**Solutions:**

**Solution 1: Clone Missing Repository**
```bash
cd /d/dev
git clone https://github.com/resolve-io/actions.api.git
```

**Solution 2: Check Dev Root**
```powershell
& .\Get-DevRoot.ps1
# Verify it's pointing to correct location
```

**Solution 3: Update Repository List**
If repo is in different location, edit `Get-ActionsRepos.ps1`:
```powershell
[PSCustomObject]@{
    Name = "actions.api"
    Path = "C:\custom\path\actions.api"  # Custom path
    ...
}
```

---

### Issue 9: "Orca launches but crashes immediately"

**Symptom:** Orca process starts then exits

**Causes:**
1. Database connection failed
2. Missing dependencies
3. Port conflict
4. Configuration errors

**Solutions:**

**Solution 1: Check Database**
```powershell
# Check if SQL container is running
docker ps | Select-String "sql"

# If not running, start Orca normally
# It should create the container
```

**Solution 2: Check Orca Logs**
```
Use BashOutput to read full error output
Look for:
- Connection strings
- Missing DLLs
- Configuration errors
```

**Solution 3: Clean Launch**
```powershell
# Stop everything
& .\Stop-ActionsProcesses.ps1

# Remove containers
docker ps -a --filter "name=orca" --format "{{.ID}}" | ForEach-Object {
    docker rm -f $_
}

# Launch fresh
"launch orca with rebuild"
```

---

### Issue 10: "Source files not detected as newer"

**Symptom:** Made changes but build not triggered

**Causes:**
1. File extension not in source list
2. File in bin/obj directory
3. Timestamp precision issues

**Solutions:**

**Solution 1: Check File Extension**
Supported: `.cs`, `.vb`, `.csproj`, `.vbproj`, `.sln`

If using other files:
- `.fs` (F#) - Add to `Check-BuildRequired.ps1`
- `.tsx` (TypeScript) - Not supported (frontend only)

**Solution 2: Verify File Location**
```powershell
# Check if file is in bin/obj (excluded)
$file = "D:\dev\orca\SomeFile.cs"
$file -like "*\bin\*" -or $file -like "*\obj\*"
# Should be False
```

**Solution 3: Force Rebuild**
```
"launch orca with rebuild"
```

---

## Performance Issues

### Slow Build Checks

**Symptom:** Takes 30+ seconds just to check builds

**Solutions:**

1. **Reduce Repo Count**
   Remove unused repos from `Get-ActionsRepos.ps1`

2. **Skip Build Check**
   ```
   "launch orca without building"
   ```

3. **Use Branch Cache**
   Branch cache speeds up checks significantly

### Slow Builds

**Symptom:** Builds take 5+ minutes

**Solutions:**

1. **Build Only Changed**
   Don't force rebuild unnecessarily

2. **Parallel Builds** (future enhancement)
   Not yet implemented

3. **Incremental Builds**
   Don't clean before building

## Getting Help

### Enable Verbose Output

```powershell
& .\Launch-Orca.ps1 -Verbose
```

### Capture Full Output

```powershell
& .\Launch-Orca.ps1 -Verbose *>&1 | Tee-Object -FilePath "launch-log.txt"
```

### Check Individual Scripts

```powershell
# Test dev root discovery
& .\Get-DevRoot.ps1 -Verbose

# Test repo list
& .\Get-ActionsRepos.ps1 -Verbose

# Test branch cache
& .\Get-BranchCache.ps1 -Verbose

# Test build check
$repo = (& .\Get-ActionsRepos.ps1)[0]
$cache = & .\Get-BranchCache.ps1
& .\Check-BuildRequired.ps1 -RepoInfo $repo -BranchCache $cache -Verbose
```

## Related Documentation

- [Build Detection](./build-detection.md) - Build requirement logic
- [Branch Tracking](./branch-tracking.md) - Branch cache details
- [Repository Mappings](./repo-mappings.md) - All repo configurations
- [Launch Workflow](./launch-workflow.md) - Complete process

---

**Last Updated:** 2025-11-03
