# Restore Workflow - Detailed Process

This document describes the complete workflow for restoring the Orca database from a backup.

## Overview

The restore process imports a Docker volume backup (tar.gz archive) into the active Orca SQL volume. The process safely stops containers, clears existing data, and imports the backup.

## Step-by-Step Workflow

### Step 1: Volume Discovery

**Purpose:** Find the active Orca SQL data volume dynamically

**Script:** `Find-OrcaVolume.ps1` (from backup-orca-db skill)

**Process:**
```powershell
docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" |
    Where-Object { $_ -like "*sql-data*" }
```

**Expected Output:**
```
orca.apphost-cc67ab6e00-sql-data
```

**Volume Name Validation:**
- Length must be > 20 characters (safety check)
- Must match pattern: `orca.apphost.*sql-data`
- Prevents accidental restore to wrong volume

### Step 2: Backup File Selection

**Purpose:** Find the backup to restore (most recent or specific)

**Most Recent (Default):**
```powershell
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.Name -match "orca-db-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}\.tar\.gz" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
```

**Specific Named Backup:**
```powershell
$backupFile = "orca-db-$BackupName.tar.gz"
$backupPath = Join-Path $backupsDir $backupFile

if (!(Test-Path $backupPath)) {
    throw "Backup file not found"
}
```

**Backup Information Displayed:**
- Filename
- Last modified date
- Size in MB

### Step 3: Container Management

**Purpose:** Stop and remove containers using the volume

**Find Containers:**
```powershell
docker ps -a --filter "volume=$volumeName" --format "{{.ID}}"
```

**Stop and Remove:**
```powershell
foreach ($containerId in $containers) {
    docker stop $containerId
    docker rm $containerId
}
```

**Why Necessary:**
- Docker volumes cannot be modified while in use
- SQL Server must be stopped before restore
- Orca will recreate containers on next launch

### Step 4: Safety Confirmation

**Purpose:** Give user chance to cancel before data deletion

**Display:**
```
WARNING: This will DELETE all data in volume: orca.apphost-cc67ab6e00-sql-data
WARNING: And restore from backup: orca-db-2025-10-31-14-30.tar.gz

Press Ctrl+C to cancel, or wait 3 seconds to continue...
```

**Countdown:** 3 seconds (can be skipped with `-SkipConfirmation`)

**User Actions:**
- Press Ctrl+C to cancel
- Wait 3 seconds to proceed

### Step 5: Clear Existing Volume Data

**Purpose:** Remove all existing data to prevent conflicts

**Command:**
```powershell
docker run --rm -v "${volumeName}:/data" alpine sh -c "rm -rf /data/*"
```

**How It Works:**
- Creates temporary Alpine container
- Mounts volume as `/data`
- Deletes all contents: `rm -rf /data/*`
- Container auto-removes after completion

**CRITICAL:**
- Skipping this step causes merge conflicts
- Merging can corrupt the database
- Always clear before importing

**Safety Checks:**
- Volume name validated before clearing
- Only deletes contents, not volume itself
- No external files affected

### Step 6: Import Backup

**Purpose:** Restore database from tar.gz archive

**Command:**
```powershell
docker run --rm `
    -v "${volumeName}:/data" `
    -v "${backupsDir}:/backup:ro" `
    alpine tar -xzf "/backup/$backupFile" -C /data
```

**How It Works:**
1. **Temporary Container:** Alpine Linux with tar utility
2. **Volume Mounts:**
   - Target volume as `/data` (read-write)
   - Backups directory as `/backup` (read-only)
3. **Tar Extract:**
   - `-x` extract
   - `-z` gunzip
   - `-f` file
   - `-C /data` extract to /data directory

**Performance:**
- Typical restore time: 10-30 seconds
- Depends on backup size and disk speed
- Extraction is CPU-intensive

### Step 7: Verification

**Purpose:** Confirm restore was successful

**Check File Count:**
```powershell
docker run --rm -v "${volumeName}:/data" alpine sh -c "ls -1 /data | wc -l"
```

**Expected Output:**
```
15
```

**Typical Contents:**
- SQL Server system files
- Master database files (`.mdf`, `.ldf`)
- Tenant database files
- SQL Server configuration

**Additional Verification (Optional):**
```powershell
docker run --rm -v "${volumeName}:/data" alpine ls -lh /data
```

Shows detailed file listing with sizes.

### Step 8: Completion

**Purpose:** Report success and next steps

**Output:**
```
[SUCCESS] Database restore complete!

To use the restored database, launch Orca using the 'orca' skill.
```

**Return Value:**
```powershell
[PSCustomObject]@{
    Success = $true
    VolumeName = "orca.apphost-cc67ab6e00-sql-data"
    BackupFile = "orca-db-2025-10-31-14-30.tar.gz"
    Message = "Database restored successfully"
}
```

## Error Handling

### Volume Not Found

**Error:**
```
Orca SQL volume not found. Is Orca installed?
```

**Cause:** No Docker volume matching pattern

**Resolution:**
1. Check Docker Desktop is running
2. Verify Orca is installed: `docker volume ls`
3. Look for volume containing "orca" and "sql"

### No Backups Found

**Error:**
```
No timestamped backups found in C:\Users\...\backups
```

**Cause:** No backup files in cache directory

**Resolution:**
1. Check backup directory exists
2. Run backup skill first: `"backup orca database"`
3. Or specify custom backup name

### Backup File Not Found

**Error:**
```
Backup file not found: ...orca-db-migration-test.tar.gz
```

**Cause:** Specified backup name doesn't exist

**Resolution:**
1. List available backups
2. Check backup name spelling
3. Use most recent backup (don't specify name)

### Failed to Clear Volume

**Error:**
```
Failed to clear volume. Output: ...
```

**Cause:** Docker issue or volume in use

**Resolution:**
1. Restart Docker Desktop
2. Manually stop containers: `docker ps -a`
3. Check disk space

### Failed to Import Backup

**Error:**
```
Failed to import backup. Output: ...
```

**Cause:** Corrupted backup or Docker issue

**Resolution:**
1. Check backup file integrity
2. Try different backup
3. Check available disk space
4. Restart Docker Desktop

## Performance Considerations

### Restore Speed

**Factors:**
- Backup size (larger = slower)
- Disk I/O speed (SSD vs HDD)
- Docker performance settings

**Typical Times:**
- Small backup (50 MB): 5-10 seconds
- Medium backup (200 MB): 15-30 seconds
- Large backup (500 MB): 30-60 seconds

### Resource Usage

**During Restore:**
- CPU: 20-40% (extraction)
- RAM: ~100-200 MB (Docker container)
- Disk Read: Backup file size
- Disk Write: Uncompressed size (~3x backup size)

## Best Practices

### When to Restore

**Before risky operations:**
- Major database migrations
- Schema changes
- Testing new features

**After problems:**
- Database corruption
- Failed migrations
- Data integrity issues

**For testing:**
- Restore baseline
- Run tests
- Restore again for next test

### Backup Selection

**Most Recent (Default):**
- Use when you want latest state
- Safe for routine restores
- Good for "undo last change"

**Specific Named Backup:**
- Use for milestone restores
- Good for "back to known state"
- Requires remembering backup names

### Container Management

**Orca Running:**
- Restore will stop Orca automatically
- SQL containers removed cleanly
- Safe to restore while Orca is running

**After Restore:**
- Launch Orca with `orca` skill
- Database will be in restored state
- No manual container management needed

## Safety Features

### Multiple Validation Checks

1. **Volume name validation** - Prevents wrong volume
2. **Backup file existence** - Ensures backup is available
3. **Container management** - Stops containers safely
4. **Safety countdown** - Gives user chance to cancel
5. **Clear warnings** - Explicit about data deletion
6. **Verification** - Confirms restore success

### Data Protection

**Volume-Only Restore:**
- Only affects Docker volume
- No code changes
- No configuration changes
- Backup files never modified

**Reversible:**
- Can restore again from different backup
- Original backup files preserved
- No permanent changes

## Integration with Other Skills

### With backup-orca-db

**Workflow:**
1. Backup current state
2. Make changes
3. If problems, restore from backup
4. Repeat as needed

### With orca

**Workflow:**
1. Restore database from backup
2. Launch Orca with restored database
3. Continue development

**Example:**
```
User: "restore orca database and launch it"

Steps:
1. Run restore-orca-db skill
2. Wait for restore completion
3. Run orca skill to launch
4. Display dashboard URL
```

### With orca-migrations

**Workflow:**
1. Backup before migration
2. Run migration forward
3. If problems, restore backup
4. Fix migration
5. Restore backup again
6. Re-run migration

## Future Enhancements

### Planned Features

1. **Backup Preview:** Show backup contents before restore
2. **Partial Restore:** Restore specific databases only
3. **Backup Comparison:** Compare backup with current state
4. **Restore Validation:** More thorough verification
5. **Progress Bar:** Show restore progress
6. **Rollback:** Automatic backup before restore

### Possible Improvements

- Faster extraction (parallel processing)
- Backup integrity check before restore
- Automatic Orca restart after restore
- Restore from remote backups (cloud storage)
- Restore to different volume (copy)

## Related Documentation

- [Backup Workflow](../../backup-orca-db/reference/backup-workflow.md) - Creating backups
- [Troubleshooting](./troubleshooting.md) - Common restore issues

---

**Last Updated:** 2025-11-03
