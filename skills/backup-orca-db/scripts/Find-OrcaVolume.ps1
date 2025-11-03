<#
.SYNOPSIS
    Finds the active Orca SQL Server Docker volume.

.DESCRIPTION
    Dynamically discovers the Orca SQL data volume by searching for volumes
    matching the pattern "orca.apphost*sql-data".

    This handles volume name changes (hash changes) automatically without
    requiring hard-coded volume names.

.PARAMETER Interactive
    When true, prompts user to choose if multiple volumes exist or if no volumes are in use.
    When false, throws an error if ambiguous.

.OUTPUTS
    String - Volume name (e.g., "orca.apphost-cc67ab6e00-sql-data")

.EXAMPLE
    $volumeName = & .\Find-OrcaVolume.ps1
    # Returns: orca.apphost-cc67ab6e00-sql-data

.EXAMPLE
    $volumeName = & .\Find-OrcaVolume.ps1 -Interactive
    # Prompts user if multiple volumes found or none in use

.NOTES
    Requires Docker CLI to be available and Docker Desktop to be running.
#>

[CmdletBinding()]
param(
    [switch]$Interactive
)

Write-Verbose "Searching for Orca SQL volume..."

# Find all volumes matching Orca pattern
$allVolumes = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" 2>$null | Where-Object { $_ -like "*sql-data*" }

if (!$allVolumes) {
    throw "Orca SQL volume not found. Is Orca installed? Run 'docker volume ls' to see available volumes."
}

# Gather information about each volume
$volumeInfo = @()
foreach ($volume in $allVolumes) {
    $containers = docker ps -a --filter "volume=$volume" --format "{{json .}}" 2>$null
    $inUse = $false
    $containerNames = @()

    Write-Verbose "Checking volume: $volume"
    Write-Verbose "  Containers result: $($containers -ne $null)"

    if ($containers) {
        Write-Verbose "  Has containers, parsing JSON..."
        # Convert to array to handle both single and multiple containers
        $containerObjects = @($containers | ForEach-Object { $_ | ConvertFrom-Json })
        $inUse = $true
        $containerNames = @($containerObjects | ForEach-Object { $_.Names })
        Write-Verbose "  Found $($containerNames.Count) container(s): $($containerNames -join ', ')"
    } else {
        Write-Verbose "  No containers found"
    }

    $volumeInfo += [PSCustomObject]@{
        Name = $volume
        InUse = $inUse
        Containers = $containerNames
    }
}

Write-Verbose "Total volumes found: $($volumeInfo.Count)"
Write-Verbose "Volumes in use: $(($volumeInfo | Where-Object { $_.InUse }).Count)"

# Filter to volumes in use - force array to handle single-item case
$volumesInUse = @($volumeInfo | Where-Object { $_.InUse })

# Case 1: Exactly one volume in use - use it
if ($volumesInUse.Count -eq 1) {
    $volumeName = $volumesInUse[0].Name
    Write-Verbose "Found active volume in use by container: $volumeName"
    return $volumeName
}

# Case 2: Multiple volumes in use - ambiguous
if ($volumesInUse.Count -gt 1) {
    if ($Interactive) {
        Write-Host ""
        Write-Host "Multiple Orca SQL volumes are in use:" -ForegroundColor Yellow
        for ($i = 0; $i -lt $volumesInUse.Count; $i++) {
            Write-Host "  [$($i + 1)] $($volumesInUse[$i].Name)" -ForegroundColor Cyan
            Write-Host "      Containers: $($volumesInUse[$i].Containers -join ', ')" -ForegroundColor Gray
        }
        Write-Host ""

        $choice = Read-Host "Enter the number of the volume to use (1-$($volumesInUse.Count))"
        $index = [int]$choice - 1

        if ($index -ge 0 -and $index -lt $volumesInUse.Count) {
            return $volumesInUse[$index].Name
        } else {
            throw "Invalid choice: $choice"
        }
    } else {
        $volumeList = ($volumesInUse | ForEach-Object { $_.Name }) -join ", "
        throw "Multiple Orca SQL volumes are in use: $volumeList. Cannot automatically determine which to use. Please specify the volume explicitly or run with -Interactive flag."
    }
}

# Case 3: No volumes in use
if ($Interactive) {
    Write-Host ""
    Write-Host "No Orca SQL volumes are currently in use by containers." -ForegroundColor Yellow
    Write-Host "Available volumes:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $volumeInfo.Count; $i++) {
        Write-Host "  [$($i + 1)] $($volumeInfo[$i].Name)" -ForegroundColor Cyan
        Write-Host "      Status: NOT IN USE" -ForegroundColor Gray
    }
    Write-Host ""

    $choice = Read-Host "Enter the number of the volume to use (1-$($volumeInfo.Count))"
    $index = [int]$choice - 1

    if ($index -ge 0 -and $index -lt $volumeInfo.Count) {
        return $volumeInfo[$index].Name
    } else {
        throw "Invalid choice: $choice"
    }
} else {
    $volumeList = ($volumeInfo | ForEach-Object { $_.Name }) -join ", "
    throw "No Orca SQL volumes are in use by containers. Available volumes: $volumeList. Cannot automatically determine which to use. Please specify the volume explicitly or run with -Interactive flag."
}
