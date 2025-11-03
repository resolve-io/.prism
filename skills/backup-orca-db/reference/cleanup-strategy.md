# Cleanup Strategy - Automatic Backup Management

This document describes the automatic cleanup strategy for managing Orca database backups.

## Overview

The backup system includes automatic cleanup to prevent disk space exhaustion while preserving important backups. Cleanup is based on two policies: retention days and maximum backup count.

## Cleanup Triggers

### Manual Trigger

**Flag:** `-AutoCleanup` parameter

```powershell
& .\Backup-DockerVolume.ps1 -AutoCleanup
```

Runs cleanup immediately after creating a backup.

### Automatic Trigger (Future)

**Config:** `autoCleanupOldBackups: true` in `config.json`

```json
{
  "autoCleanupOldBackups": true
}
```

When enabled, cleanup runs automatically after every backup (not yet implemented - always requires `-AutoCleanup` flag currently).

## Cleanup Policies

### Policy 1: Retention Period

**Setting:** `backupRetentionDays` (default: 30)

**Rule:** Delete backups older than N days

**Example:**
```json
{
  "backupRetentionDays": 30
}
```

**Logic:**
```powershell
$cutoffDate = (Get-Date).AddDays(-30)
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.LastWriteTime -lt $cutoffDate }
```

**Behaviors:**
- Uses file system `LastWriteTime` (not filename timestamp)
- Applies to ALL backups (timestamped and custom named)
- Exception: Just-created backup is never deleted

**Use Cases:**
- Keep recent history: `7` days (one week)
- Development backups: `30` days (one month)
- Long-term archives: `90` or `180` days

### Policy 2: Maximum Count

**Setting:** `maxBackupCount` (default: 10)

**Rule:** Keep only the N most recent backups

**Example:**
```json
{
  "maxBackupCount": 10
}
```

**Logic:**
```powershell
$allBackups = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Sort-Object LastWriteTime -Descending

if ($allBackups.Count -gt 10) {
    $toDelete = $allBackups | Select-Object -Skip 10
    # Delete $toDelete
}
```

**Behaviors:**
- Sorts by `LastWriteTime` (not filename)
- Keeps N most recent (by file modification time)
- Applies after retention period cleanup

**Use Cases:**
- Disk space constrained: `5` backups
- Regular development: `10` backups (default)
- Extensive testing: `20` or `50` backups

## Cleanup Order

Cleanup runs in two phases:

### Phase 1: Age-Based Cleanup

**Order:** First

**Criteria:** `backupRetentionDays`

**Example:**
```
Before:
- orca-db-2025-09-15-10-00.tar.gz (47 days old) → DELETE
- orca-db-2025-10-01-14-30.tar.gz (31 days old) → DELETE
- orca-db-2025-10-15-09-00.tar.gz (17 days old) → KEEP
- orca-db-2025-10-25-16-45.tar.gz (7 days old)  → KEEP
- orca-db-2025-10-31-14-30.tar.gz (1 day old)   → KEEP

After Phase 1 (retentionDays=30):
- orca-db-2025-10-15-09-00.tar.gz (17 days old)
- orca-db-2025-10-25-16-45.tar.gz (7 days old)
- orca-db-2025-10-31-14-30.tar.gz (1 day old)
```

### Phase 2: Count-Based Cleanup

**Order:** Second (after age cleanup)

**Criteria:** `maxBackupCount`

**Example:**
```
After Phase 1 (3 backups remain):
- orca-db-2025-10-15-09-00.tar.gz (17 days old)
- orca-db-2025-10-25-16-45.tar.gz (7 days old)
- orca-db-2025-10-31-14-30.tar.gz (1 day old)

maxBackupCount=2:

After Phase 2:
- orca-db-2025-10-25-16-45.tar.gz (7 days old)  → KEEP (2nd most recent)
- orca-db-2025-10-31-14-30.tar.gz (1 day old)   → KEEP (most recent)
- orca-db-2025-10-15-09-00.tar.gz (17 days old) → DELETE (exceeds max count)
```

## Policy Interactions

### Both Policies Active

**Config:**
```json
{
  "backupRetentionDays": 30,
  "maxBackupCount": 10
}
```

**Rule:** A backup is deleted if it violates EITHER policy

**Examples:**

**Example 1: Age violation**
- Backup is 45 days old
- Only 5 total backups exist (under max count)
- **Result:** Deleted (age > 30 days)

**Example 2: Count violation**
- Backup is 10 days old (under retention)
- Total of 15 backups exist (over max count)
- This backup is 11th oldest
- **Result:** Deleted (exceeds max count of 10)

**Example 3: Both satisfied**
- Backup is 15 days old (under 30)
- This is the 8th most recent (under 10)
- **Result:** Kept (satisfies both policies)

### Only Retention Active

**Config:**
```json
{
  "backupRetentionDays": 30,
  "maxBackupCount": 999
}
```

**Behavior:** Only age matters, keep unlimited recent backups

**Use Case:** "Keep everything from last month"

### Only Count Active

**Config:**
```json
{
  "backupRetentionDays": 9999,
  "maxBackupCount": 10
}
```

**Behavior:** Only count matters, keep last N regardless of age

**Use Case:** "Keep last 10 backups, even if they're months old"

## Configuration File

### Location

**Path:** `$env:USERPROFILE\.claude-orca\config.json`

**Example:** `C:\Users\DanPuzon\.claude-orca\config.json`

### Full Configuration

```json
{
  "maxBackupCount": 10,
  "backupRetentionDays": 30,
  "autoCleanupOldBackups": true
}
```

**Fields:**
- `maxBackupCount`: Max number of backups to keep (default: 10)
- `backupRetentionDays`: Max age in days (default: 30)
- `autoCleanupOldBackups`: Auto-run cleanup after backup (default: false)

### Creating Configuration

**Manual creation:**
```powershell
$configPath = "$env:USERPROFILE\.claude-orca\config.json"
$config = @{
    maxBackupCount = 15
    backupRetentionDays = 60
    autoCleanupOldBackups = $true
} | ConvertTo-Json

Set-Content -Path $configPath -Value $config
```

**Result:**
- Keeps last 15 backups
- Deletes backups older than 60 days
- Runs cleanup automatically after each backup

### Default Values

If config file doesn't exist or is malformed:
- `maxBackupCount`: 10
- `backupRetentionDays`: 30
- `autoCleanupOldBackups`: false (must use `-AutoCleanup` flag)

## Cleanup Behavior Details

### Protected Backups

**Current backup is NEVER deleted:**
```powershell
Where-Object { $_.LastWriteTime -lt $cutoffDate -and $_.Name -ne $backupFile }
```

Even if it somehow matches deletion criteria, the just-created backup is explicitly excluded.

### Custom Named Backups

**Custom names are NOT protected by default.**

**They follow the same rules:**
- Deleted if older than `backupRetentionDays`
- Deleted if they exceed `maxBackupCount`

**Example:**
```
Backups:
- orca-db-migration-test.tar.gz (45 days old)
- orca-db-release-v2.0.tar.gz (60 days old)

retentionDays=30:
Both are deleted (older than 30 days)
```

**To preserve custom backups:**
- Set very high `backupRetentionDays` (e.g., 365 or 9999)
- Manually move important backups outside the cleanup directory
- Store milestone backups in a separate location

### File System Timestamp vs Filename Timestamp

**Cleanup uses `LastWriteTime` (file system), not filename timestamp.**

**Why:**
- Custom named backups have no timestamp in filename
- File system timestamp is reliable and always present
- Handles manually copied/restored backup files

**Example:**
```
File: orca-db-2025-10-15-14-30.tar.gz
Filename timestamp: 2025-10-15 14:30
LastWriteTime: 2025-10-31 16:00 (file was copied today)

Cleanup uses: 2025-10-31 (LastWriteTime)
```

This means a copied backup file is treated as "new" even if the filename suggests it's old.

## Cleanup Output

### Console Output

**Example:**
```
Cleaning up old backups...
  Removing: orca-db-2025-09-15-10-00.tar.gz (older than 30 days)
  Removing: orca-db-2025-10-01-14-30.tar.gz (older than 30 days)
  Removing: orca-db-2025-10-10-09-00.tar.gz (exceeds max count 10)
  ✓ Removed 3 old backup(s)
```

**Or if nothing to clean:**
```
Cleaning up old backups...
  ✓ No old backups to remove
```

### Verbose Output

**Flag:** `-Verbose`

```powershell
& .\Backup-DockerVolume.ps1 -AutoCleanup -Verbose
```

**Output includes:**
```
VERBOSE: Loaded config: maxBackupCount=10, retentionDays=30
VERBOSE: Cutoff date: 2025-10-01
VERBOSE: Found 15 total backups
VERBOSE: 5 backups older than cutoff
VERBOSE: 2 backups exceed max count after age cleanup
```

## Disk Space Management

### Estimating Space Usage

**Typical backup sizes:**
- Empty database: ~50 MB
- Development database: 100-300 MB
- Large database: 500+ MB

**Space calculation:**
```
10 backups × 200 MB average = 2 GB total
50 backups × 200 MB average = 10 GB total
```

**Check current usage:**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
$totalSize = (Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Measure-Object -Property Length -Sum).Sum
$totalSizeMB = [math]::Round($totalSize / 1MB, 2)
Write-Host "Total backup space: $totalSizeMB MB"
```

### Recommended Settings by Disk Space

**Limited Space (<5 GB available):**
```json
{
  "maxBackupCount": 5,
  "backupRetentionDays": 7,
  "autoCleanupOldBackups": true
}
```

**Moderate Space (5-20 GB available):**
```json
{
  "maxBackupCount": 10,
  "backupRetentionDays": 30,
  "autoCleanupOldBackups": true
}
```

**Ample Space (>20 GB available):**
```json
{
  "maxBackupCount": 50,
  "backupRetentionDays": 90,
  "autoCleanupOldBackups": true
}
```

## Manual Cleanup

### Delete All Backups

```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Remove-Item "$backupsDir\orca-db-*.tar.gz" -Force
```

**Warning:** This deletes ALL backups, including custom named ones.

### Delete Old Backups Manually

```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
$cutoffDate = (Get-Date).AddDays(-30)

Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.LastWriteTime -lt $cutoffDate } |
    Remove-Item -Force
```

### Delete Specific Backup

```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Remove-Item "$backupsDir\orca-db-migration-test.tar.gz" -Force
```

### List All Backups with Size

```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Sort-Object LastWriteTime -Descending |
    Format-Table Name, @{Label="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}, LastWriteTime -AutoSize
```

## Cleanup Algorithm Pseudocode

```
function Cleanup-Backups {
    # Load configuration
    config = Load-Config() ?? Defaults

    # Get all backups (except just-created one)
    allBackups = Get-AllBackups(exclude: currentBackup)

    # Phase 1: Age-based cleanup
    cutoffDate = Now - config.retentionDays
    oldBackups = allBackups.where(lastWriteTime < cutoffDate)
    Delete(oldBackups)

    # Phase 2: Count-based cleanup
    remainingBackups = Get-AllBackups(exclude: currentBackup)
    remainingBackups.sortBy(lastWriteTime, descending)

    if remainingBackups.count > config.maxBackupCount {
        excessBackups = remainingBackups.skip(config.maxBackupCount)
        Delete(excessBackups)
    }

    # Report results
    deletedCount = oldBackups.count + excessBackups.count
    Report(deletedCount)
}
```

## Future Enhancements

### Planned Features

1. **Protected Milestones:** Tag custom backups as "protected" to exclude from cleanup
2. **Differential Retention:** Different policies for timestamped vs custom backups
3. **Size-Based Cleanup:** Delete oldest when total size exceeds limit
4. **Archive Old Backups:** Move to cold storage instead of deleting
5. **Cleanup Schedule:** Run cleanup daily/weekly independent of backups
6. **Dry-Run Mode:** Preview what would be deleted without deleting

### Possible Improvements

- Cleanup report with detailed statistics
- Email notification of cleanup actions
- Backup metadata (description, tags) to inform cleanup decisions
- Cloud backup integration (cleanup local, keep remote)
- Compression level adjustment for old backups (recompress with higher ratio)

## Related Documentation

- [Backup Workflow](./backup-workflow.md) - Complete backup process
- [Naming Conventions](./backup-naming.md) - Backup naming patterns
- [Troubleshooting](./troubleshooting.md) - Common issues

---

**Last Updated:** 2025-10-31
