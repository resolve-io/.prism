# Repository Mappings

This document lists all repositories tracked by the orca skill and their build configurations.

## Overview

The orca skill manages **11 repositories** across two build systems:
- **4 Dotnet repositories** (use `dotnet build`)
- **7 MSBuild repositories** (use `MSBuild.exe`)

All configurations are **embedded** in `Get-ActionsRepos.ps1` - no external dependencies.

## Dotnet Repositories (.NET Core/9)

### orca

**Description:** Main Orca application (AppHost)

**Configuration:**
- **Path:** `{devRoot}/orca`
- **Solution:** `orca.sln`
- **Build Type:** `dotnet`
- **Bin Path:** `Orca.AppHost/bin/Debug/net9.0`
- **Target Framework:** `.NET 9.0`

**Build Command:**
```powershell
dotnet build "D:\dev\orca\orca.sln" -c Debug -v q
```

**Launch Command:**
```bash
cd /d/dev/orca/Orca.AppHost && dotnet run --no-build
```

---

### actions.api

**Description:** Actions API service

**Configuration:**
- **Path:** `{devRoot}/actions.api`
- **Solution:** `actions.api.sln`
- **Build Type:** `dotnet`
- **Bin Path:** `src/bin/Debug/net9.0`
- **Target Framework:** `.NET 9.0`

**Build Command:**
```powershell
dotnet build "D:\dev\actions.api\actions.api.sln" -c Debug -v q
```

**Key DLLs:**
- `actions.api.dll`

---

### actions.engine

**Description:** Actions execution engine

**Configuration:**
- **Path:** `{devRoot}/actions.engine`
- **Solution:** `actions.engine.sln`
- **Build Type:** `dotnet`
- **Bin Path:** `libs` (multiple project directories)
- **Target Framework:** `.NET 9.0`

**Build Command:**
```powershell
dotnet build "D:\dev\actions.engine\actions.engine.sln" -c Debug -v q
```

**Note:** Multiple lib projects, DLLs scattered across `libs/` subdirectories

---

### actions.manager

**Description:** Actions management service

**Configuration:**
- **Path:** `{devRoot}/actions.manager`
- **Solution:** `actions.manager.sln`
- **Build Type:** `dotnet`
- **Bin Path:** `src/bin/Debug/net9.0`
- **Target Framework:** `.NET 9.0`

**Build Command:**
```powershell
dotnet build "D:\dev\actions.manager\actions.manager.sln" -c Debug -v q
```

---

## MSBuild Repositories (.NET Framework)

### express-comm

**Description:** Communication server

**Configuration:**
- **Path:** `{devRoot}/express-comm`
- **Solution:** `src/eyeShare Comm Server/eyeShare Comm Server.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `src/eyeShare Comm Server/bin`
- **Target Framework:** `.NET Framework 4.x`

**Build Command:**
```powershell
& "C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\MSBuild.exe" `
  "D:\dev\express-comm\src\eyeShare Comm Server\eyeShare Comm Server.sln" `
  /p:Configuration=Debug /verbosity:minimal
```

---

### express-remote-comm

**Description:** Remote communication server

**Configuration:**
- **Path:** `{devRoot}/express-remote-comm`
- **Solution:** `eyeShareProj/eyeShare Comm Server Remote/eyeShare Comm Server Remote.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `eyeShareProj/eyeShare Comm Server Remote/bin`
- **Target Framework:** `.NET Framework 4.x`

---

### express-engine

**Description:** Workflow execution engine

**Configuration:**
- **Path:** `{devRoot}/express-engine`
- **Solution:** `eyeShareEngine/eyeShareEngine.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `eyeShareEngine/bin`
- **Target Framework:** `.NET Framework 4.x`

---

### express-executor

**Description:** Workflow executor service

**Configuration:**
- **Path:** `{devRoot}/express-executor`
- **Solution:** `eyeShareExecutor/eyeShareExecutorServer.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `eyeShareExecutor/eyeShareExecutorServer/bin`
- **Target Framework:** `.NET Framework 4.x`

---

### express-scheduler

**Description:** Workflow scheduling service

**Configuration:**
- **Path:** `{devRoot}/express-scheduler`
- **Solution:** `eyeShareSchedulerServer/eyeShareSchedulerServer.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `eyeShareSchedulerServer/bin`
- **Target Framework:** `.NET Framework 4.x`

---

### express-integrations

**Description:** Third-party integrations/modules

**Configuration:**
- **Path:** `{devRoot}/express-integrations`
- **Solution:** `ModulesSharedProject.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `bin`
- **Target Framework:** `.NET Framework 4.x`

---

### express-web-api

**Description:** Web API service

**Configuration:**
- **Path:** `{devRoot}/express-web-api`
- **Solution:** `AyehuWebApi/EyeShare.sln`
- **Build Type:** `msbuild`
- **Bin Path:** `AyehuWebApi/EyeShare.Api/bin`
- **Target Framework:** `.NET Framework 4.x`

**Key DLLs:**
- `EyeShare.Api.dll`

---

## Build Path Patterns

### Dotnet Projects

**Pattern:** `{ProjectDir}/bin/{Configuration}/{TargetFramework}/`

**Examples:**
```
orca/Orca.AppHost/bin/Debug/net9.0/
actions.api/src/bin/Debug/net9.0/
actions.manager/src/bin/Debug/net9.0/
```

### MSBuild Projects

**Pattern:** `{ProjectDir}/bin/`

**Examples:**
```
express-web-api/AyehuWebApi/EyeShare.Api/bin/
express-comm/src/eyeShare Comm Server/bin/
express-executor/eyeShareExecutor/eyeShareExecutorServer/bin/
```

**Note:** No `{Configuration}` or `{TargetFramework}` subdirectories

## Repository Detection

### Existence Check

**Script:** `Get-ActionsRepos.ps1`

**Logic:**
```powershell
$repos = @(
    # All 11 repos defined
)

# Filter to existing repos only
$existingRepos = $repos | Where-Object { Test-Path $_.Path }
```

**Result:** Only repositories that exist on disk are checked

**Use Case:** Not all developers have all repos

### Missing Repositories

If a repo doesn't exist:
- **Skipped** in build check
- **Not built**
- **No error** (graceful degradation)

**Example:** Developer only has `orca` and `actions.api`
- Only these 2 are checked and built
- Other 9 repos ignored

## Dev Root Discovery

### Strategies (in order)

1. **Environment Variable:** `$env:DEV_ROOT`
2. **Upward Search:** Look for `resolve.dev.resources` repo
3. **Common Locations:** `D:\dev`, `C:\dev`, etc.
4. **Fallback:** `D:\dev`

**Script:** `Get-DevRoot.ps1`

**Result:** All repo paths computed from discovered dev root

## Build Configuration

### Debug vs Release

**Current:** Always builds `Debug` configuration

**Rationale:**
- Development launches (not production)
- Faster builds (no optimization)
- Better debugging (symbols included)

**Future:** Could add Release option

### Verbosity

**Dotnet:** `-v q` (quiet)
**MSBuild:** `/verbosity:minimal`

**Rationale:**
- Reduces noise in output
- Faster console rendering
- Errors still shown

## Adding New Repositories

### Steps

1. **Edit Get-ActionsRepos.ps1**
2. **Add configuration:**
   ```powershell
   [PSCustomObject]@{
       Name = "new-repo"
       Path = Join-Path $devRoot "new-repo"
       BuildType = "dotnet"  # or "msbuild"
       SolutionPath = "new-repo.sln"
       BinPath = "bin/Debug/net9.0"
   }
   ```
3. **Test:** Launch orca, verify repo is checked

### Considerations

- **Build Type:** Must match project type
- **Bin Path:** Relative to repo root
- **Solution Path:** Relative to repo root
- **Name:** Used in branch cache

## Related Documentation

- [Build Detection](./build-detection.md) - How builds are triggered
- [Branch Tracking](./branch-tracking.md) - Branch cache format
- [Launch Workflow](./launch-workflow.md) - Complete process

---

**Last Updated:** 2025-11-03
