<#
.SYNOPSIS
    Restores the Orca SQL Docker volume from a backup.

.DESCRIPTION
    Restores a Docker volume from a tar.gz backup archive. Can restore from the most recent
    backup or a specific named backup. Safely stops containers, clears the volume, and imports
    the backup data.

.PARAMETER BackupName
    Optional name of a specific backup to restore (e.g., "migration-test")
    If not provided, restores from the most recent timestamped backup.

.PARAMETER SkipConfirmation
    Skip the 3-second safety countdown before restoring.

.OUTPUTS
    [PSCustomObject] with properties:
    - Success (bool)
    - VolumeName (string)
    - BackupFile (string)
    - Message (string)

.EXAMPLE
    & .\Restore-DockerVolume.ps1
    # Restores from most recent backup

.EXAMPLE
    & .\Restore-DockerVolume.ps1 -BackupName "migration-test"
    # Restores from orca-db-migration-test.tar.gz

.EXAMPLE
    & .\Restore-DockerVolume.ps1 -SkipConfirmation
    # Restores without 3-second countdown

.NOTES
    Requires Docker CLI and Docker Desktop running.
    Will stop and remove any containers using the volume.
#>

[CmdletBinding()]
param(
    [string]$BackupName,
    [switch]$SkipConfirmation
)

# Get paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillDir = Split-Path -Parent $scriptDir
$backupSkillDir = Join-Path (Split-Path -Parent $skillDir) "backup-orca-db"
$volumeScript = Join-Path $backupSkillDir "scripts\Find-OrcaVolume.ps1"
$cacheScript = Join-Path $backupSkillDir "scripts\Get-CachePath.ps1"

# Get backup directory
$backupsDir = & $cacheScript -SubPath "backups"

Write-Host "Orca Database Restore Tool" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host ""

# Find Orca SQL volume
Write-Host "Finding Orca SQL volume..." -ForegroundColor Yellow
try {
    $volumeName = & $volumeScript
    Write-Host "  [OK] Found volume: $volumeName" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    throw
}

# Validate volume name for safety
if ($volumeName.Length -lt 20) {
    throw "Volume name too short (safety check failed): $volumeName"
}

if ($volumeName -notmatch "orca\.apphost.*sql-data") {
    throw "Volume name doesn't match expected pattern: $volumeName"
}

# Find backup file
Write-Host ""
Write-Host "Finding backup file..." -ForegroundColor Yellow

if ($BackupName) {
    # Use specific named backup
    $backupFile = "orca-db-$BackupName.tar.gz"
    $backupPath = Join-Path $backupsDir $backupFile

    if (!(Test-Path $backupPath)) {
        throw "Backup file not found: $backupPath"
    }
} else {
    # Find most recent timestamped backup
    $timestampedBackups = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
        Where-Object { $_.Name -match "orca-db-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}\.tar\.gz" } |
        Sort-Object LastWriteTime -Descending

    if ($timestampedBackups.Count -eq 0) {
        throw "No timestamped backups found in $backupsDir"
    }

    $backupPath = $timestampedBackups[0].FullName
    $backupFile = $timestampedBackups[0].Name
}

$backupSize = (Get-Item $backupPath).Length
$backupSizeMB = [math]::Round($backupSize / 1MB, 2)
$backupDate = (Get-Item $backupPath).LastWriteTime

Write-Host "  [OK] Found backup: $backupFile" -ForegroundColor Green
Write-Host "    Date: $backupDate" -ForegroundColor Gray
Write-Host "    Size: $backupSizeMB MB" -ForegroundColor Gray

# Check for containers using the volume
Write-Host ""
Write-Host "Checking for running containers..." -ForegroundColor Yellow

$containers = docker ps -a --filter "volume=$volumeName" --format "{{.ID}}" 2>$null

if ($containers) {
    Write-Host "  [OK] Found container(s) using the volume" -ForegroundColor Yellow

    foreach ($containerId in $containers) {
        $containerName = docker ps -a --filter "id=$containerId" --format "{{.Names}}" 2>$null

        Write-Host "  Stopping container: $containerName ($containerId)" -ForegroundColor Yellow
        docker stop $containerId 2>&1 | Out-Null

        Write-Host "  Removing container: $containerName" -ForegroundColor Yellow
        docker rm $containerId 2>&1 | Out-Null
    }

    Write-Host "  [OK] All containers stopped and removed" -ForegroundColor Green
} else {
    Write-Host "  [OK] No containers using the volume" -ForegroundColor Green
}

# Safety confirmation
Write-Host ""
Write-Host "WARNING: This will DELETE all data in volume: $volumeName" -ForegroundColor Red
Write-Host "WARNING: And restore from backup: $backupFile" -ForegroundColor Red
Write-Host ""

if (!$SkipConfirmation) {
    Write-Host "Press Ctrl+C to cancel, or wait 3 seconds to continue..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    Write-Host ""
}

# Clear existing volume data
Write-Host "Clearing existing volume data..." -ForegroundColor Yellow
try {
    $clearCommand = "docker run --rm -v `"${volumeName}:/data`" alpine sh -c `"rm -rf /data/*`""
    Write-Verbose "Running: $clearCommand"

    $output = Invoke-Expression $clearCommand 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clear volume. Output: $output"
    }

    Write-Host "  [OK] Volume cleared" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to clear volume: $_" -ForegroundColor Red
    throw
}

# Import backup
Write-Host ""
Write-Host "Importing backup..." -ForegroundColor Yellow
try {
    # Use PowerShell paths for Docker (avoid bash path conversion issues)
    $importCommand = "docker run --rm -v `"${volumeName}:/data`" -v `"${backupsDir}:/backup:ro`" alpine tar -xzf `"/backup/$backupFile`" -C /data"
    Write-Verbose "Running: $importCommand"

    $output = Invoke-Expression $importCommand 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to import backup. Output: $output"
    }

    Write-Host "  [OK] Backup imported" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to import backup: $_" -ForegroundColor Red
    throw
}

# Verify restore
Write-Host ""
Write-Host "Verifying restore..." -ForegroundColor Yellow
try {
    $verifyCommand = "docker run --rm -v `"${volumeName}:/data`" alpine sh -c `"ls -1 /data | wc -l`""
    $fileCount = Invoke-Expression $verifyCommand 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to verify restore"
    }

    Write-Host "  [OK] Restored $fileCount files/directories" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Failed to verify: $_" -ForegroundColor Red
    throw
}

Write-Host ""
Write-Host "[SUCCESS] Database restore complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To use the restored database, launch Orca using the 'orca' skill." -ForegroundColor Cyan
Write-Host ""

return [PSCustomObject]@{
    Success = $true
    VolumeName = $volumeName
    BackupFile = $backupFile
    Message = "Database restored successfully"
}
