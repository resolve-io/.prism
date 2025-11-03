<#
.SYNOPSIS
    Launches Orca with smart build detection.

.DESCRIPTION
    Main orchestration script that:
    1. Checks all repositories for build requirements
    2. Stops processes if builds are needed
    3. Builds affected repositories
    4. Launches Orca
    5. Returns dashboard URL

.PARAMETER Force Build
    Force rebuild of all repositories regardless of changes

.PARAMETER SkipBuild
    Skip build check and launch with existing binaries

.OUTPUTS
    [PSCustomObject] with properties:
    - Success (bool)
    - DashboardUrl (string)
    - BuiltRepos (array)
    - Message (string)

.EXAMPLE
    & .\Launch-Orca.ps1

.NOTES
    This is the main entry point for the orca skill.
#>

[CmdletBinding()]
param(
    [switch]$ForceBuild,
    [switch]$SkipBuild
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Load helper scripts
$getReposScript = Join-Path $scriptDir "Get-ActionsRepos.ps1"
$getBranchCacheScript = Join-Path $scriptDir "Get-BranchCache.ps1"
$checkBuildScript = Join-Path $scriptDir "Check-BuildRequired.ps1"
$stopProcessesScript = Join-Path $scriptDir "Stop-ActionsProcesses.ps1"
$buildSolutionScript = Join-Path $scriptDir "Build-Solution.ps1"
$updateBranchCacheScript = Join-Path $scriptDir "Update-BranchCache.ps1"

Write-Host "Orca Launch Tool" -ForegroundColor Cyan
Write-Host "================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get repository list
Write-Host "Getting repository list..." -ForegroundColor Yellow
$repos = & $getReposScript
Write-Host "  [OK] Found $($repos.Count) repositories" -ForegroundColor Green

# Step 2: Get branch cache
Write-Host ""
Write-Host "Checking branch cache..." -ForegroundColor Yellow
$branchCache = & $getBranchCacheScript
Write-Host "  [OK] Loaded cache ($($branchCache.Count) entries)" -ForegroundColor Green

# Step 3: Check build requirements
Write-Host ""
Write-Host "Checking build requirements..." -ForegroundColor Yellow

$reposNeedingBuild = @()
$currentBranches = @{}

foreach ($repo in $repos) {
    if ($SkipBuild) {
        Write-Host "  [SKIP] $($repo.Name)" -ForegroundColor Gray
        continue
    }

    $buildCheck = & $checkBuildScript -RepoInfo $repo -BranchCache $branchCache
    $currentBranches[$repo.Name] = $buildCheck.CurrentBranch

    if ($ForceBuild -or $buildCheck.BuildRequired) {
        $reason = if ($ForceBuild) { "Forced" } else { $buildCheck.Reason }
        Write-Host "  [BUILD] $($repo.Name): $reason" -ForegroundColor Yellow
        $reposNeedingBuild += $repo
    } else {
        Write-Host "  [OK] $($repo.Name): Up to date" -ForegroundColor Green
    }
}

# Step 4: Stop processes if builds are needed
if ($reposNeedingBuild.Count -gt 0) {
    Write-Host ""
    & $stopProcessesScript
}

# Step 5: Build affected repositories
$builtRepos = @()
if ($reposNeedingBuild.Count -gt 0) {
    Write-Host ""
    Write-Host "Building $($reposNeedingBuild.Count) repository/repositories..." -ForegroundColor Yellow

    foreach ($repo in $reposNeedingBuild) {
        $solutionPath = Join-Path $repo.Path $repo.SolutionPath

        $buildResult = & $buildSolutionScript -SolutionPath $solutionPath -BuildType $repo.BuildType

        if ($buildResult.Success) {
            $builtRepos += $repo.Name
        } else {
            throw "Build failed for $($repo.Name): $($buildResult.Message)"
        }
    }

    # Update branch cache after successful builds
    Write-Host ""
    Write-Host "Updating branch cache..." -ForegroundColor Yellow
    & $updateBranchCacheScript -BranchInfo $currentBranches
    Write-Host "  [OK] Branch cache updated" -ForegroundColor Green
}

# Step 6: Launch Orca
Write-Host ""
Write-Host "Launching Orca..." -ForegroundColor Yellow
Write-Host "  Use BashOutput to monitor logs" -ForegroundColor Gray
Write-Host "  Use KillShell or Stop-ActionsProcesses to stop" -ForegroundColor Gray
Write-Host ""

# Return launch info (actual launch will be done by Claude Code using Bash tool)
return [PSCustomObject]@{
    Success = $true
    LaunchCommand = "cd /d/dev/orca/Orca.AppHost && dotnet run --no-build"
    BuiltRepos = $builtRepos
    Message = "Ready to launch Orca"
}
