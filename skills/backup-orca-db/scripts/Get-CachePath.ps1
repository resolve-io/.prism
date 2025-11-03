<#
.SYNOPSIS
    Returns the path to the Orca cache directory in user profile.

.DESCRIPTION
    Returns the base cache path or a subdirectory within the cache.
    Ensures the directory exists before returning.

    Cache location: $env:USERPROFILE\.claude-orca\

    Benefits:
    - Survives dev root wipes
    - Survives repo deletions and re-clones
    - Proper separation of code vs state
    - Standard Windows application data pattern

.PARAMETER SubPath
    Optional subdirectory within cache (e.g., "backups", "branch-cache")

.OUTPUTS
    String - Absolute path to cache directory

.EXAMPLE
    $cachePath = & .\Get-CachePath.ps1
    # Returns: C:\Users\DanPuzon\.claude-orca

.EXAMPLE
    $backupsPath = & .\Get-CachePath.ps1 -SubPath "backups"
    # Returns: C:\Users\DanPuzon\.claude-orca\backups

.EXAMPLE
    $branchCache = & .\Get-CachePath.ps1 -SubPath "branch-cache"
    # Returns: C:\Users\DanPuzon\.claude-orca\branch-cache
#>

[CmdletBinding()]
param(
    [string]$SubPath
)

$basePath = "$env:USERPROFILE\.claude-orca"

# Ensure base cache directory exists
if (!(Test-Path $basePath)) {
    Write-Verbose "Creating cache directory: $basePath"
    New-Item -ItemType Directory -Path $basePath -Force | Out-Null
}

# Ensure backups subdirectory exists (always created)
$backupsPath = Join-Path $basePath "backups"
if (!(Test-Path $backupsPath)) {
    Write-Verbose "Creating backups directory: $backupsPath"
    New-Item -ItemType Directory -Path $backupsPath -Force | Out-Null
}

if ($SubPath) {
    $fullPath = Join-Path $basePath $SubPath

    # Ensure subdirectory parent exists (for files like branch-cache, connection-cache)
    # Don't create the file itself, just ensure parent directory exists
    $parentDir = Split-Path $fullPath -Parent
    if ($parentDir -and !(Test-Path $parentDir)) {
        Write-Verbose "Creating directory: $parentDir"
        New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
    }

    return $fullPath
}

return $basePath
