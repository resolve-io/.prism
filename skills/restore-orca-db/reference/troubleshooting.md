# Troubleshooting Guide - Restore Issues and Solutions

This document provides solutions to common issues when restoring the Orca database.

## Quick Diagnostics

### Health Check Script

```powershell
Write-Host "=== Orca Restore Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check 1: Docker running
Write-Host "1. Docker Desktop:" -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "   [OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] Docker is not running" -ForegroundColor Red
}

# Check 2: Orca volume exists
Write-Host "2. Orca SQL Volume:" -ForegroundColor Yellow
$volume = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" 2>$null |
    Where-Object { $_ -like "*sql-data*" }
if ($volume) {
    Write-Host "   [OK] Found: $volume" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] Orca volume not found" -ForegroundColor Red
}

# Check 3: Backups available
Write-Host "3. Available Backups:" -ForegroundColor Yellow
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
$backups = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" -ErrorAction SilentlyContinue
if ($backups) {
    Write-Host "   [OK] Found $($backups.Count) backup(s)" -ForegroundColor Green
    $recent = $backups | Sort-Object LastWriteTime -Descending | Select-Object -First 3
    foreach ($backup in $recent) {
        $sizeMB = [math]::Round($backup.Length / 1MB, 2)
        $age = (Get-Date) - $backup.LastWriteTime
        Write-Host "      - $($backup.Name) ($sizeMB MB, $([math]::Round($age.TotalDays, 1)) days old)" -ForegroundColor Gray
    }
} else {
    Write-Host "   [ERROR] No backups found" -ForegroundColor Red
}

# Check 4: Containers using volume
Write-Host "4. Containers Using Volume:" -ForegroundColor Yellow
if ($volume) {
    $containers = docker ps -a --filter "volume=$volume" --format "{{.Names}}" 2>$null
    if ($containers) {
        Write-Host "   [OK] Found: $containers" -ForegroundColor Yellow
    } else {
        Write-Host "   [OK] No containers using volume" -ForegroundColor Green
    }
}
```

## Common Issues

### Issue 1: "No timestamped backups found"

**Error Message:**
```
No timestamped backups found in C:\Users\DanPuzon\.claude-orca\backups
```

**Causes:**
1. No backups have been created yet
2. Only custom-named backups exist
3. Backup directory doesn't exist

**Solutions:**

**Solution 1: Create a Backup First**
```powershell
# Create a backup before restoring
cd D:\dev\.prism\skills\backup-orca-db\scripts
& .\Backup-DockerVolume.ps1
```

**Solution 2: List Available Backups**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Select-Object Name, LastWriteTime, @{Label="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

**Solution 3: Restore Specific Named Backup**
```powershell
# If only custom-named backups exist
& .\Restore-DockerVolume.ps1 -BackupName "migration-test"
```

---

### Issue 2: "Backup file not found"

**Error Message:**
```
Backup file not found: C:\Users\...\orca-db-migration-test.tar.gz
```

**Causes:**
1. Backup name misspelled
2. Backup was deleted
3. Wrong backup name

**Solutions:**

**Solution 1: List Available Backups**
```powershell
ls "$env:USERPROFILE\.claude-orca\backups\orca-db-*.tar.gz"
```

**Solution 2: Use Correct Name**
```powershell
# Backup filenames have "orca-db-" prefix
# If backup is "orca-db-test.tar.gz", use:
& .\Restore-DockerVolume.ps1 -BackupName "test"

# NOT: -BackupName "orca-db-test"
```

**Solution 3: Restore Most Recent**
```powershell
# Don't specify backup name to use most recent
& .\Restore-DockerVolume.ps1
```

---

### Issue 3: "Failed to clear volume"

**Error Message:**
```
Failed to clear volume. Output: ...
```

**Causes:**
1. Container still using volume
2. Docker Desktop not running
3. Permission issues
4. Volume locked

**Solutions:**

**Solution 1: Manually Stop Containers**
```powershell
# Find containers using volume
$volume = "orca.apphost-cc67ab6e00-sql-data"
$containers = docker ps -a --filter "volume=$volume" --format "{{.ID}}"

# Stop and remove each container
foreach ($c in $containers) {
    docker stop $c
    docker rm $c
}
```

**Solution 2: Restart Docker Desktop**
```
1. Close Docker Desktop
2. Wait 10 seconds
3. Start Docker Desktop
4. Wait 30-60 seconds for full startup
5. Retry restore
```

**Solution 3: Check Volume Permissions**
```powershell
# Inspect volume
docker volume inspect $volumeName
```

---

### Issue 4: "Failed to import backup"

**Error Message:**
```
Failed to import backup. Output: ...
```

**Causes:**
1. Corrupted backup file
2. Insufficient disk space
3. Docker path conversion issues
4. Tar extraction error

**Solutions:**

**Solution 1: Verify Backup Integrity**
```powershell
$backupPath = "$env:USERPROFILE\.claude-orca\backups\orca-db-2025-11-03-07-22.tar.gz"

# Test archive
docker run --rm -v "${backupPath}:/test.tar.gz:ro" alpine tar -tzf /test.tar.gz | Select-Object -First 10
```

**Expected:** List of files
**Error:** `tar: not in gzip format` or `invalid archive`

**Solution 2: Check Disk Space**
```powershell
Get-PSDrive -Name C
```

Need at least 3x backup size free (for extraction).

**Solution 3: Try Different Backup**
```powershell
# Restore from previous backup
& .\Restore-DockerVolume.ps1 -BackupName "older-backup-name"
```

**Solution 4: Create Fresh Backup**
If all backups are corrupted, create a new one before attempting changes.

---

### Issue 5: "Volume name too short (safety check failed)"

**Error Message:**
```
Volume name too short (safety check failed): orca-123
```

**Causes:**
1. Unexpected volume name format
2. Wrong volume detected
3. Manual volume name change

**Solutions:**

**Solution 1: List All Volumes**
```powershell
docker volume ls | Select-String "orca"
```

**Expected Format:**
```
orca.apphost-cc67ab6e00-sql-data
```

**Solution 2: Check Volume Name Manually**
```powershell
# If volume name is correct but short, edit script validation
# (This should be rare - volume names are normally 30+ chars)
```

**Solution 3: Reinstall Orca**
If volume name is wrong, Orca may need to be reinstalled.

---

### Issue 6: "Volume name doesn't match expected pattern"

**Error Message:**
```
Volume name doesn't match expected pattern: some-other-volume
```

**Causes:**
1. Wrong volume selected
2. Non-Orca volume detected
3. Volume naming changed

**Solutions:**

**Solution 1: Verify Volume Name**
```powershell
docker volume ls --filter "name=orca" --format "{{.Name}}"
```

Should contain:
- `orca.apphost`
- `sql-data`

**Solution 2: Check for Multiple Volumes**
```powershell
docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" |
    Where-Object { $_ -like "*sql-data*" }
```

If multiple volumes exist, manually specify correct one.

---

### Issue 7: "Container cannot be stopped"

**Error Message:**
```
Error response from daemon: container xyz cannot be stopped
```

**Causes:**
1. Container hung
2. Process locked
3. Docker issue

**Solutions:**

**Solution 1: Force Kill Container**
```powershell
docker kill $containerId
docker rm -f $containerId
```

**Solution 2: Stop Orca Processes**
```powershell
# Use PowerShell utils from resolve.dev.resources
# Or manually kill processes
Get-Process | Where-Object { $_.Name -like "*orca*" -or $_.Name -like "*dotnet*" } |
    Stop-Process -Force
```

**Solution 3: Restart Docker**
Complete Docker Desktop restart usually resolves hung containers.

---

### Issue 8: "Restored 0 files/directories"

**Error Message:**
```
[OK] Restored 0 files/directories
```

**Causes:**
1. Backup file is empty
2. Extraction failed silently
3. Wrong backup path

**Solutions:**

**Solution 1: Verify Backup Has Contents**
```powershell
$backupPath = "$env:USERPROFILE\.claude-orca\backups\orca-db-test.tar.gz"
docker run --rm -v "${backupPath}:/test.tar.gz:ro" alpine tar -tzf /test.tar.gz | Measure-Object -Line
```

**Expected:** More than 10 lines (files)

**Solution 2: Check Backup Size**
```powershell
Get-Item $backupPath | Select-Object Name, Length
```

**Expected:** At least 10 MB
**Problem:** Less than 5 MB suggests empty/incomplete backup

**Solution 3: Manually Verify Volume After Restore**
```powershell
docker run --rm -v "$volumeName:/data" alpine ls -lah /data
```

---

### Issue 9: "Access denied" or "Permission denied"

**Error Message:**
```
docker: Error response from daemon: ... permission denied
```

**Causes:**
1. Docker Desktop permissions
2. Volume access issues
3. Windows file sharing settings

**Solutions:**

**Solution 1: Run as Administrator**
```powershell
# Right-click PowerShell
# Select "Run as Administrator"
# Retry restore
```

**Solution 2: Check Docker Desktop Settings**
```
Docker Desktop → Settings → Resources → File Sharing
- Ensure C:\ is shared
- Add user profile drive if different
```

**Solution 3: Reset Docker Desktop**
```
Docker Desktop → Troubleshoot → Reset to factory defaults
```

(WARNING: Deletes all Docker data)

---

### Issue 10: Restore Takes Too Long

**Symptom:** Restore hangs or takes more than 5 minutes

**Causes:**
1. Very large backup (>500 MB)
2. Slow disk (HDD vs SSD)
3. Docker resource limits
4. Background processes

**Solutions:**

**Solution 1: Check Backup Size**
```powershell
Get-Item "$env:USERPROFILE\.claude-orca\backups\orca-db-*.tar.gz" |
    Select-Object Name, @{Label="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

**Solution 2: Increase Docker Resources**
```
Docker Desktop → Settings → Resources
- Memory: 4GB → 8GB
- CPUs: 2 → 4
```

**Solution 3: Close Unnecessary Applications**
- Free up CPU and RAM
- Pause OneDrive sync
- Close Visual Studio, browsers

---

## Performance Optimization

### Slow Restores

**Diagnosis:**
```powershell
Measure-Command {
    & .\Restore-DockerVolume.ps1 -SkipConfirmation
}
```

**Optimizations:**
1. Use SSD for user profile (if on HDD)
2. Increase Docker memory
3. Close background applications
4. Pause antivirus during restore

### Large Backups

**Diagnosis:**
```powershell
# Check all backup sizes
Get-ChildItem "$env:USERPROFILE\.claude-orca\backups" -Filter "orca-db-*.tar.gz" |
    Sort-Object Length -Descending |
    Select-Object Name, @{Label="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

**Optimizations:**
1. Clean up old Orca data before backups
2. Use smaller/older backups for testing
3. Consider archiving large backups externally

## Getting Help

### Enable Verbose Output

```powershell
& .\Restore-DockerVolume.ps1 -Verbose
```

Shows detailed diagnostic information.

### Capture Full Output

```powershell
& .\Restore-DockerVolume.ps1 -Verbose *>&1 | Tee-Object -FilePath "restore-log.txt"
```

### Check Docker Logs

```powershell
docker ps -a | Select-String "alpine"
docker logs <container-id>
```

### Environment Information

```powershell
Write-Host "=== Environment ===" -ForegroundColor Cyan
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"
Write-Host "User Profile: $env:USERPROFILE"
docker version
docker info
```

## Related Documentation

- [Restore Workflow](./restore-workflow.md) - Complete restore process
- [Backup Workflow](../../backup-orca-db/reference/backup-workflow.md) - Creating backups

---

**Last Updated:** 2025-11-03
