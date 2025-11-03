<#
.SYNOPSIS
    Retrieves cached branch information for repositories.

.DESCRIPTION
    Reads the branch cache file from user profile to check which branches
    were active during the last build. This helps detect branch changes
    that require rebuilds.

.OUTPUTS
    Hashtable with repo names as keys and branch names as values
    Example: @{ "orca" = "main"; "actions.api" = "feature/test" }

.EXAMPLE
    $branchCache = & .\Get-BranchCache.ps1
    if ($branchCache["orca"] -ne "main") {
        Write-Host "Orca branch has changed!"
    }

.NOTES
    Cache location: $env:USERPROFILE\.claude-orca\branch-cache
#>

[CmdletBinding()]
param()

# Get cache path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Split-Path -Parent $scriptDir
$backupSkillDir = Join-Path (Split-Path -Parent $skillDir) "backup-orca-db"
$cacheScript = Join-Path $backupSkillDir "scripts\Get-CachePath.ps1"

$cacheDir = & $cacheScript
$branchCacheFile = Join-Path $cacheDir "branch-cache"

Write-Verbose "Branch cache file: $branchCacheFile"

$branchCache = @{}

if (Test-Path $branchCacheFile) {
    Write-Verbose "Reading branch cache..."

    $lines = Get-Content $branchCacheFile

    foreach ($line in $lines) {
        if ($line -match "^([^:]+):(.+)$") {
            $repoName = $matches[1]
            $branchName = $matches[2]
            $branchCache[$repoName] = $branchName
            Write-Verbose "  $repoName -> $branchName"
        }
    }

    Write-Verbose "Loaded $($branchCache.Count) cached branches"
} else {
    Write-Verbose "No branch cache file found (first run)"
}

return $branchCache
