# Backup Workflow - Detailed Process

This document describes the complete workflow for creating Orca database backups.

## Overview

The backup process exports a Docker volume containing the Orca SQL Server database to a compressed tar.gz archive stored in the user profile cache. The process is non-destructive (read-only) and can run while Orca is running or stopped.

## Step-by-Step Workflow

### Step 1: Volume Discovery

**Purpose:** Find the active Orca SQL data volume dynamically

**Script:** `Find-OrcaVolume.ps1`

**Process:**
```powershell
# Search for volumes matching Orca pattern
docker volume ls --filter "name=orca.apphost" --format "{{.Name}}"

# Filter for SQL data volumes
Where-Object { $_ -like "*sql-data*" }
```

**Expected Output:**
```
orca.apphost-cc67ab6e00-sql-data
```

**Why Dynamic:**
- Volume names include a hash that changes
- No hard-coded volume names required
- Works after Orca reinstalls or updates

**Error Conditions:**
- No volume found → Orca not installed
- Multiple volumes found → Returns first match
- Docker not running → Command fails

### Step 2: Backup Filename Generation

**Purpose:** Create unique backup filename (timestamped or custom)

**Script:** `Backup-DockerVolume.ps1` (internal logic)

**Timestamped Naming:**
```powershell
$timestamp = Get-Date -Format "yyyy-MM-dd-HH-mm"
$backupFile = "orca-db-$timestamp.tar.gz"
# Result: orca-db-2025-10-31-14-30.tar.gz
```

**Custom Naming:**
```powershell
$safeName = $CustomName -replace '[\\/:*?"<>|]', '-'
$backupFile = "orca-db-$safeName.tar.gz"
# Result: orca-db-migration-test.tar.gz
```

**Sanitization:**
- Invalid filename characters replaced with `-`
- Windows reserved characters: `\ / : * ? " < > |`
- Example: `"my:backup"` becomes `"my-backup"`

**Collision Detection:**
- Checks if backup file already exists
- Prompts user to overwrite or cancel
- Prevents accidental overwrites

### Step 3: Cache Directory Setup

**Purpose:** Ensure backup destination exists

**Script:** `Get-CachePath.ps1`

**Process:**
```powershell
$basePath = "$env:USERPROFILE\.claude-orca"
$backupsDir = "$basePath\backups"

# Create directories if missing
New-Item -ItemType Directory -Path $basePath -Force
New-Item -ItemType Directory -Path $backupsDir -Force
```

**Directory Structure:**
```
C:\Users\DanPuzon\.claude-orca\
├── backups\                    # Created here
├── branch-cache               # (Other skills)
└── connection-cache           # (Other skills)
```

### Step 4: Volume Export

**Purpose:** Export Docker volume to tar.gz archive

**Script:** `Backup-DockerVolume.ps1` (core logic)

**Export Command:**
```powershell
docker run --rm `
    -v "${volumeName}:/volume:ro" `
    -v "${backupsDir}:/backup" `
    alpine tar -czf "/backup/$backupFile" -C /volume .
```

**How It Works:**

1. **Temporary Alpine Container:**
   - `docker run --rm` - Creates and auto-removes container
   - `alpine` - Lightweight Linux image with tar

2. **Volume Mounts:**
   - `-v "${volumeName}:/volume:ro"` - Mount SQL volume as read-only
   - `:ro` flag prevents modifications during backup
   - `-v "${backupsDir}:/backup"` - Mount backup destination

3. **Tar Compression:**
   - `tar -czf` - Create compressed (gzip) tar archive
   - `/backup/$backupFile` - Output file in mounted backup directory
   - `-C /volume .` - Change to /volume and archive everything

**Performance:**
- Typical backup size: 100-500 MB (compressed)
- Typical backup time: 10-30 seconds
- CPU usage: Moderate (compression)
- Disk I/O: Moderate (read SQL files, write tar.gz)

**Read-Only Safety:**
- Volume mounted with `:ro` flag
- SQL Server not affected by backup
- Can backup while Orca is running
- No database locks or interruptions

### Step 5: Verification

**Purpose:** Ensure backup was created successfully

**Checks:**
```powershell
# 1. File exists
if (!(Test-Path $backupPath)) {
    throw "Backup file not found after export"
}

# 2. Get file size
$backupSize = (Get-Item $backupPath).Length
$backupSizeMB = [math]::Round($backupSize / 1MB, 2)

# 3. Size sanity check (optional)
if ($backupSizeMB -lt 10) {
    Write-Warning "Backup seems unusually small: $backupSizeMB MB"
}
```

**Expected Size:**
- Minimum: ~50 MB (empty database)
- Typical: 100-300 MB (development database)
- Large: 500+ MB (extensive data)

**Integrity Check (Future Enhancement):**
```powershell
# Verify tar.gz is valid (not implemented yet)
tar -tzf $backupPath > $null
if ($LASTEXITCODE -ne 0) {
    throw "Backup file appears corrupted"
}
```

### Step 6: Result Reporting

**Purpose:** Display backup information to user

**Output:**
```
✅ Backup complete!
  Path: C:\Users\DanPuzon\.claude-orca\backups\orca-db-2025-10-31-14-30.tar.gz
  Size: 145.23 MB
```

**Return Value:**
```powershell
[PSCustomObject]@{
    Success = $true
    BackupPath = "C:\Users\DanPuzon\.claude-orca\backups\orca-db-2025-10-31-14-30.tar.gz"
    BackupSize = "145.23 MB"
    Message = "Backup created successfully"
}
```

### Step 7: Optional Cleanup

**Purpose:** Remove old backups based on retention policy

**Trigger:** `-AutoCleanup` flag or `config.json` setting

**See:** [Cleanup Strategy](./cleanup-strategy.md) for details

## Error Handling

### Volume Not Found

**Error:**
```
Orca SQL volume not found. Is Orca installed?
```

**Cause:** No Docker volume matching `orca.apphost*sql-data`

**Resolution:**
1. Check Docker Desktop is running
2. Check Orca is installed: `docker volume ls`
3. Look for volume name containing "orca" and "sql"

### Docker Not Running

**Error:**
```
Docker export failed with exit code 1
```

**Cause:** Docker Desktop not running

**Resolution:**
1. Start Docker Desktop
2. Wait for Docker to fully start (30-60 seconds)
3. Retry backup

### Disk Space Insufficient

**Error:**
```
No space left on device
```

**Cause:** Insufficient disk space in user profile

**Resolution:**
1. Free up disk space on C: drive
2. Remove old backups manually
3. Configure automatic cleanup
4. Consider moving user profile to larger drive

### Permission Denied

**Error:**
```
Access denied to backup directory
```

**Cause:** No write access to `$env:USERPROFILE\.claude-orca\backups\`

**Resolution:**
1. Check folder permissions
2. Run as administrator (if needed)
3. Check antivirus isn't blocking

## Performance Considerations

### Backup Speed

**Factors:**
- Database size (larger = slower)
- Compression level (gzip -9 by default)
- Disk I/O speed (SSD vs HDD)
- Docker performance settings

**Optimization:**
- Use SSD for user profile
- Close unnecessary applications
- Increase Docker resource limits

### Resource Usage

**During Backup:**
- CPU: 20-40% (compression)
- RAM: ~100-200 MB (Docker container)
- Disk Read: Volume size
- Disk Write: Compressed size (~30% of volume)

**After Backup:**
- No ongoing resource usage
- Backup file is static tar.gz

## Best Practices

### When to Backup

**Before:**
- Major database migrations
- Risky schema changes
- Testing new features
- Major Orca updates

**Regular:**
- Daily (if active development)
- Before each sprint
- After milestone completions

**Ad-Hoc:**
- Before troubleshooting
- Before experimenting
- Before cleanup operations

### Naming Conventions

**Timestamped (Default):**
- Use for regular automated backups
- Easy to sort chronologically
- No naming conflicts

**Custom Named:**
- Use for milestones: `before-migration-plat-1234`
- Use for testing: `test-workflow-v1`
- Use for releases: `release-v2.0-gold`

### Storage Management

**Keep:**
- Last 10 backups (default)
- Named milestone backups
- Backups from last 30 days

**Remove:**
- Backups older than retention period
- Excess backups beyond max count
- Failed or incomplete backups

## Integration with Other Skills

### With restore-orca-db

**Workflow:**
1. Backup current state
2. Make risky changes
3. If problem occurs, restore from backup
4. Repeat as needed

### With orca-migration-manager

**Workflow:**
1. Backup before migration
2. Run migration forward
3. Test changes
4. If issues, restore backup
5. If success, backup again (new milestone)

### With orca

**Workflow:**
1. Backup before major code changes
2. Launch Orca
3. Test changes
4. If database corruption, restore backup
5. Continue development

## Security Considerations

### Backup Contents

**Includes:**
- All SQL Server databases
- Master database
- Tenant database(s)
- System databases
- Database logs

**Sensitive Data:**
- May contain passwords (hashed)
- May contain API keys
- May contain user data
- May contain workflow definitions

**Protection:**
- Stored in user profile (Windows protected)
- Not accessible to other users
- File system permissions enforced
- Consider encryption for sensitive environments

### Access Control

**Who Can Backup:**
- Current user only
- Requires Docker Desktop access
- Requires write access to user profile

**Who Can Restore:**
- Same user who created backup
- Users with access to backup files
- Users with Docker Desktop access

## Future Enhancements

### Planned Features

1. **Encryption:** Encrypt backups with password
2. **Compression Levels:** Choose compression (fast vs small)
3. **Remote Storage:** Upload to S3, Azure Blob, etc.
4. **Scheduled Backups:** Automatic daily/weekly backups
5. **Incremental Backups:** Only backup changes
6. **Backup Verification:** Automatic integrity checks
7. **Backup Catalog:** List and search backups
8. **Backup Metadata:** Store backup description, tags

### Possible Improvements

- Parallel compression (faster)
- Progress bar during export
- Email notification on completion
- Backup size estimation before export
- Differential backups (only changes)
- Backup to network share
- Cloud backup integration

## Related Documentation

- [Naming Conventions](./backup-naming.md) - Backup naming patterns
- [Cleanup Strategy](./cleanup-strategy.md) - Retention policies
- [Troubleshooting](./troubleshooting.md) - Common issues

---

**Last Updated:** 2025-10-31
