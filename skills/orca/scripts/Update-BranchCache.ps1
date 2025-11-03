<#
.SYNOPSIS
    Updates the branch cache with current branch information.

.DESCRIPTION
    Writes current branch names for all repositories to the cache file.
    Called after successful builds to track which branches were built.

.PARAMETER BranchInfo
    Hashtable with repo names as keys and branch names as values

.EXAMPLE
    $branches = @{
        "orca" = "main"
        "actions.api" = "feature/new-api"
    }
    & .\Update-BranchCache.ps1 -BranchInfo $branches

.NOTES
    Cache location: $env:USERPROFILE\.claude-orca\branch-cache
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [hashtable]$BranchInfo
)

# Get cache path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Split-Path -Parent $scriptDir
$backupSkillDir = Join-Path (Split-Path -Parent $skillDir) "backup-orca-db"
$cacheScript = Join-Path $backupSkillDir "scripts\Get-CachePath.ps1"

$cacheDir = & $cacheScript
$branchCacheFile = Join-Path $cacheDir "branch-cache"

Write-Verbose "Updating branch cache: $branchCacheFile"

# Build cache content
$lines = @()
foreach ($repo in $BranchInfo.Keys) {
    $branch = $BranchInfo[$repo]
    $lines += "${repo}:${branch}"
    Write-Verbose "  $repo -> $branch"
}

# Write to file
Set-Content -Path $branchCacheFile -Value $lines

Write-Verbose "Branch cache updated with $($lines.Count) entries"
