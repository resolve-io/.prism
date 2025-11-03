<#
.SYNOPSIS
    Finds the active Orca SQL Server Docker volume.

.DESCRIPTION
    Dynamically discovers the Orca SQL data volume by searching for volumes
    matching the pattern "orca.apphost*sql-data".

    This handles volume name changes (hash changes) automatically without
    requiring hard-coded volume names.

.OUTPUTS
    String - Volume name (e.g., "orca.apphost-cc67ab6e00-sql-data")

.EXAMPLE
    $volumeName = & .\Find-OrcaVolume.ps1
    # Returns: orca.apphost-cc67ab6e00-sql-data

.NOTES
    Requires Docker CLI to be available and Docker Desktop to be running.
#>

[CmdletBinding()]
param()

Write-Verbose "Searching for Orca SQL volume..."

# Find volume matching Orca pattern
$volumeName = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" 2>$null | Where-Object { $_ -like "*sql-data*" } | Select-Object -First 1

if (!$volumeName) {
    throw "Orca SQL volume not found. Is Orca installed? Run 'docker volume ls' to see available volumes."
}

Write-Verbose "Found Orca SQL volume: $volumeName"

return $volumeName
