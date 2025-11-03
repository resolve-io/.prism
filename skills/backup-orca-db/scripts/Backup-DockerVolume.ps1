<#
.SYNOPSIS
    Creates a backup of the Orca SQL Docker volume.

.DESCRIPTION
    Exports a Docker volume to a tar.gz archive and stores it in the user profile cache.
    Supports automatic timestamped naming or custom naming for milestones.

    Backup location: $env:USERPROFILE\.claude-orca\backups\

.PARAMETER CustomName
    Optional custom name for the backup (e.g., "migration-test")
    If not provided, uses timestamp: orca-db-{YYYY-MM-DD-HH-mm}.tar.gz

.PARAMETER AutoCleanup
    Automatically cleanup old backups based on config.json settings

.OUTPUTS
    [PSCustomObject] with properties:
    - Success (bool)
    - BackupPath (string)
    - BackupSize (string)
    - Message (string)

.EXAMPLE
    & .\Backup-DockerVolume.ps1
    # Creates: orca-db-2025-10-31-14-30.tar.gz

.EXAMPLE
    & .\Backup-DockerVolume.ps1 -CustomName "migration-test"
    # Creates: orca-db-migration-test.tar.gz

.EXAMPLE
    & .\Backup-DockerVolume.ps1 -AutoCleanup
    # Creates backup and removes old backups per config

.NOTES
    Requires Docker CLI and Docker Desktop running.
    Volume is exported read-only (no modifications during backup).
#>

[CmdletBinding()]
param(
    [string]$CustomName,
    [switch]$AutoCleanup
)

# Get paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cacheScript = Join-Path $scriptDir "Get-CachePath.ps1"
$volumeScript = Join-Path $scriptDir "Find-OrcaVolume.ps1"

# Get backup directory
$backupsDir = & $cacheScript -SubPath "backups"

Write-Host "Orca Database Backup Tool" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

# Find Orca SQL volume
Write-Host "Finding Orca SQL volume..." -ForegroundColor Yellow
try {
    $volumeName = & $volumeScript -Interactive
    if ($volumeName) {
        Write-Host "  [OK] Selected volume: $volumeName" -ForegroundColor Green
    }
} catch {
    Write-Host "  [ERROR] $_" -ForegroundColor Red
    throw
}

# Generate backup filename
if ($CustomName) {
    # Sanitize custom name (remove invalid characters)
    $safeName = $CustomName -replace '[\\/:*?"<>|]', '-'
    $backupFile = "orca-db-$safeName.tar.gz"
} else {
    $timestamp = Get-Date -Format "yyyy-MM-dd-HH-mm"
    $backupFile = "orca-db-$timestamp.tar.gz"
}

$backupPath = Join-Path $backupsDir $backupFile

Write-Host ""
Write-Host "Backup file: $backupFile" -ForegroundColor Yellow
Write-Host "Destination: $backupsDir" -ForegroundColor Yellow
Write-Host ""

# Check if backup file already exists
if (Test-Path $backupPath) {
    Write-Host "Warning: Backup file already exists: $backupFile" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne 'y') {
        Write-Host "Backup cancelled." -ForegroundColor Yellow
        return [PSCustomObject]@{
            Success = $false
            BackupPath = $null
            BackupSize = $null
            Message = "Backup cancelled - file already exists"
        }
    }
    Remove-Item $backupPath -Force
}

# Export volume to tar.gz
Write-Host "Exporting volume..." -ForegroundColor Yellow

try {
    # Use docker run to export volume to tar.gz
    # Mount volume as /volume (read-only) and backups dir as /backup
    $exportCommand = "docker run --rm -v `"${volumeName}:/volume:ro`" -v `"${backupsDir}:/backup`" alpine tar -czf `"/backup/$backupFile`" -C /volume ."

    Write-Verbose "Running: $exportCommand"

    $output = Invoke-Expression $exportCommand 2>&1

    if ($LASTEXITCODE -ne 0) {
        throw "Docker export failed with exit code $LASTEXITCODE. Output: $output"
    }

    Write-Host "  [OK] Volume exported" -ForegroundColor Green

} catch {
    Write-Host "  [ERROR] Export failed: $_" -ForegroundColor Red
    throw "Failed to export volume: $_"
}

# Verify backup exists and get size
if (!(Test-Path $backupPath)) {
    throw "Backup file not found after export: $backupPath"
}

$backupSize = (Get-Item $backupPath).Length
$backupSizeMB = [math]::Round($backupSize / 1MB, 2)

Write-Host ""
Write-Host "[SUCCESS] Backup complete!" -ForegroundColor Green
Write-Host "  Path: $backupPath" -ForegroundColor Gray
Write-Host "  Size: $backupSizeMB MB" -ForegroundColor Gray

# Optional: Auto cleanup old backups
if ($AutoCleanup) {
    Write-Host ""
    Write-Host "Cleaning up old backups..." -ForegroundColor Yellow

    $configPath = & $cacheScript -SubPath "config.json"
    $maxBackupCount = 10  # Default
    $retentionDays = 30   # Default

    # Load config if exists
    if (Test-Path $configPath) {
        try {
            $config = Get-Content $configPath | ConvertFrom-Json
            if ($config.maxBackupCount) { $maxBackupCount = $config.maxBackupCount }
            if ($config.backupRetentionDays) { $retentionDays = $config.backupRetentionDays }
            Write-Verbose "Loaded config: maxBackupCount=$maxBackupCount, retentionDays=$retentionDays"
        } catch {
            Write-Verbose "Failed to load config, using defaults"
        }
    }

    # Delete backups older than retention period
    $cutoffDate = (Get-Date).AddDays(-$retentionDays)
    $oldBackups = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
        Where-Object { $_.LastWriteTime -lt $cutoffDate -and $_.Name -ne $backupFile }

    $deletedCount = 0
    foreach ($old in $oldBackups) {
        Write-Host "  Removing: $($old.Name) (older than $retentionDays days)" -ForegroundColor Gray
        Remove-Item $old.FullName -Force
        $deletedCount++
    }

    # Keep only last N backups (by date)
    $allBackups = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
        Sort-Object LastWriteTime -Descending

    if ($allBackups.Count -gt $maxBackupCount) {
        $toDelete = $allBackups | Select-Object -Skip $maxBackupCount
        foreach ($del in $toDelete) {
            Write-Host "  Removing: $($del.Name) (exceeds max count $maxBackupCount)" -ForegroundColor Gray
            Remove-Item $del.FullName -Force
            $deletedCount++
        }
    }

    if ($deletedCount -gt 0) {
        Write-Host "  [OK] Removed $deletedCount old backup(s)" -ForegroundColor Green
    } else {
        Write-Host "  [OK] No old backups to remove" -ForegroundColor Green
    }
}

Write-Host ""

return [PSCustomObject]@{
    Success = $true
    BackupPath = $backupPath
    BackupSize = "$backupSizeMB MB"
    Message = "Backup created successfully"
}
