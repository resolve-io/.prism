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

# Find all volumes matching Orca pattern
$allVolumes = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" 2>$null | Where-Object { $_ -like "*sql-data*" }

if (!$allVolumes) {
    throw "Orca SQL volume not found. Is Orca installed? Run 'docker volume ls' to see available volumes."
}

# Prefer the volume that's currently in use by a container
$volumeName = $null
foreach ($volume in $allVolumes) {
    $containers = docker ps -a --filter "volume=$volume" --format "{{.ID}}" 2>$null
    if ($containers) {
        $volumeName = $volume
        Write-Verbose "Found active volume in use by container: $volumeName"
        break
    }
}

# If no volume is in use, fall back to the first one found
if (!$volumeName) {
    $volumeName = $allVolumes | Select-Object -First 1
    Write-Verbose "No volume in active use, using first available: $volumeName"
}

Write-Verbose "Found Orca SQL volume: $volumeName"

return $volumeName
