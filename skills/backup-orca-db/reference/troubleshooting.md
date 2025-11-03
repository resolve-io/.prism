# Troubleshooting Guide - Backup Issues and Solutions

This document provides solutions to common issues when backing up the Orca database.

## Quick Diagnostics

### Health Check Script

Run this to diagnose common issues:

```powershell
Write-Host "=== Orca Backup Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check 1: Docker Desktop running
Write-Host "1. Docker Desktop:" -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "   ✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Docker is not running" -ForegroundColor Red
}

# Check 2: Orca volume exists
Write-Host "2. Orca SQL Volume:" -ForegroundColor Yellow
$volume = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" 2>$null |
    Where-Object { $_ -like "*sql-data*" } | Select-Object -First 1
if ($volume) {
    Write-Host "   ✓ Found: $volume" -ForegroundColor Green
} else {
    Write-Host "   ✗ Orca volume not found" -ForegroundColor Red
}

# Check 3: Backup directory accessible
Write-Host "3. Backup Directory:" -ForegroundColor Yellow
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
if (Test-Path $backupsDir) {
    Write-Host "   ✓ Exists: $backupsDir" -ForegroundColor Green
    $free = (Get-PSDrive -Name ($backupsDir.Substring(0,1))).Free / 1GB
    Write-Host "   ✓ Free space: $([math]::Round($free, 2)) GB" -ForegroundColor Green
} else {
    Write-Host "   ✗ Directory not found: $backupsDir" -ForegroundColor Red
}

# Check 4: Recent backups
Write-Host "4. Recent Backups:" -ForegroundColor Yellow
$recent = Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3
if ($recent) {
    foreach ($backup in $recent) {
        $sizeMB = [math]::Round($backup.Length / 1MB, 2)
        Write-Host "   ✓ $($backup.Name) ($sizeMB MB)" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠ No backups found" -ForegroundColor Yellow
}
```

## Common Issues

### Issue 1: "Orca SQL volume not found"

**Error Message:**
```
Orca SQL volume not found. Is Orca installed? Run 'docker volume ls' to see available volumes.
```

**Causes:**
1. Orca is not installed
2. Docker Desktop is not running
3. Volume was deleted or renamed
4. Wrong Docker context

**Solutions:**

**Solution 1: Start Docker Desktop**
```powershell
# Check if Docker Desktop is running
docker version

# If error, start Docker Desktop manually
# Wait 30-60 seconds for Docker to fully start
```

**Solution 2: Verify Orca Installation**
```powershell
# List all volumes
docker volume ls

# Look for volumes containing "orca" and "sql"
docker volume ls | Select-String "orca"
```

**Expected output:**
```
orca.apphost-cc67ab6e00-sql-data
```

**Solution 3: Reinstall Orca**
If volume is truly missing:
```powershell
# Launch Orca (will recreate volume)
# Use orca skill or manual launch
```

**Solution 4: Check Docker Context**
```powershell
# Check current context
docker context ls

# Switch to default context if needed
docker context use default
```

---

### Issue 2: "Backup file already exists"

**Warning Message:**
```
⚠ Warning: Backup file already exists: orca-db-migration-test.tar.gz
Overwrite? (y/n)
```

**Causes:**
1. Backup with same name already exists (custom name)
2. Backup with same timestamp already exists (rare)

**Solutions:**

**Solution 1: Overwrite Existing Backup**
```
Overwrite? (y/n): y
```
Old backup will be deleted and replaced.

**Solution 2: Use Different Custom Name**
```powershell
# Add version number
& .\Backup-DockerVolume.ps1 -CustomName "migration-test-v2"

# Add timestamp to custom name
$timestamp = Get-Date -Format "HH-mm"
& .\Backup-DockerVolume.ps1 -CustomName "migration-test-$timestamp"
```

**Solution 3: Use Timestamped Backup (No Custom Name)**
```powershell
# Let system generate unique timestamp
& .\Backup-DockerVolume.ps1
```

**Solution 4: Delete Old Backup First**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Remove-Item "$backupsDir\orca-db-migration-test.tar.gz" -Force
& .\Backup-DockerVolume.ps1 -CustomName "migration-test"
```

---

### Issue 3: "Docker export failed with exit code 1"

**Error Message:**
```
Docker export failed with exit code 1. Output: ...
```

**Causes:**
1. Docker Desktop not running
2. Insufficient disk space
3. Permission issues
4. Docker resource limits

**Solutions:**

**Solution 1: Restart Docker Desktop**
```powershell
# Stop Docker Desktop (via system tray or Task Manager)
# Wait 10 seconds
# Start Docker Desktop
# Wait 30-60 seconds for full startup
# Retry backup
```

**Solution 2: Check Disk Space**
```powershell
# Check available space on C: drive
Get-PSDrive -Name C

# Free up space if needed:
# - Delete temp files
# - Remove old backups manually
# - Clean Docker images/containers
docker system prune -a
```

**Solution 3: Check Docker Resources**
```
Docker Desktop → Settings → Resources
- Increase Memory limit (to 4GB+)
- Increase Disk image size
```

**Solution 4: Run as Administrator**
```powershell
# Right-click PowerShell → Run as Administrator
cd D:\dev\.prism\skills\backup-orca-db\scripts
& .\Backup-DockerVolume.ps1
```

---

### Issue 4: "Backup file not found after export"

**Error Message:**
```
Backup file not found after export: C:\Users\...\orca-db-2025-10-31-14-30.tar.gz
```

**Causes:**
1. Docker export failed silently
2. File was created then deleted (antivirus)
3. Permission issues prevented file creation
4. Path too long (Windows MAX_PATH limit)

**Solutions:**

**Solution 1: Check Docker Output**
```powershell
# Run with verbose output
& .\Backup-DockerVolume.ps1 -Verbose

# Look for docker command output
# Check for error messages
```

**Solution 2: Check Antivirus**
```powershell
# Temporarily disable antivirus
# Retry backup
# If successful, add exclusion:
#   C:\Users\YourName\.claude-orca\backups\
```

**Solution 3: Verify Directory Permissions**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
$acl = Get-Acl $backupsDir
$acl.Access | Format-Table IdentityReference, FileSystemRights
```

**Solution 4: Use Shorter Custom Name**
```powershell
# Windows MAX_PATH = 260 characters
# Keep custom names under 50 characters
& .\Backup-DockerVolume.ps1 -CustomName "short-name"
```

---

### Issue 5: "Access denied to backup directory"

**Error Message:**
```
Access denied to backup directory: C:\Users\...\
```

**Causes:**
1. User profile permissions
2. OneDrive folder redirection issues
3. Antivirus blocking
4. Corporate group policy restrictions

**Solutions:**

**Solution 1: Check Folder Permissions**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
icacls $backupsDir
```

**Solution 2: Create Directory Manually**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
New-Item -ItemType Directory -Path $backupsDir -Force
```

**Solution 3: Run as Administrator**
```powershell
# Right-click PowerShell → Run as Administrator
# Retry backup operation
```

**Solution 4: Check OneDrive Sync**
If user profile is in OneDrive:
```powershell
# Check if path is synced
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Write-Host $backupsDir

# If OneDrive path, wait for sync to complete
# Or move .claude-orca outside OneDrive folder
```

---

### Issue 6: "Backup is unusually small"

**Warning Message:**
```
⚠ Warning: Backup seems unusually small: 5.23 MB
```

**Causes:**
1. Database is actually empty/new
2. Export captured partial data
3. Compression issue
4. Wrong volume exported

**Solutions:**

**Solution 1: Verify Volume Contents**
```powershell
$volumeName = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" |
    Where-Object { $_ -like "*sql-data*" }

# Inspect volume
docker run --rm -v "${volumeName}:/volume:ro" alpine ls -lah /volume
```

**Expected output (healthy database):**
```
total 500M
drwxr-xr-x    5 root     root        4.0K Oct 31 14:30 .
drwxr-xr-x    1 root     root        4.0K Oct 31 14:30 ..
-rw-r--r--    1 root     root      200.0M Oct 31 14:30 master.mdf
-rw-r--r--    1 root     root       50.0M Oct 31 14:30 master.ldf
-rw-r--r--    1 root     root      150.0M Oct 31 14:30 Tenant.mdf
```

**Solution 2: Check if Orca is Running**
```powershell
# Orca should be running for database to have data
docker ps | Select-String "orca"
```

**Solution 3: Retry Backup**
```powershell
# Sometimes first backup after Orca restart is small
# Wait 1-2 minutes and retry
Start-Sleep -Seconds 120
& .\Backup-DockerVolume.ps1
```

---

### Issue 7: "No space left on device"

**Error Message:**
```
tar: can't open '/backup/orca-db-2025-10-31-14-30.tar.gz': No space left on device
```

**Causes:**
1. Drive full (C: drive in this case)
2. User profile quota exceeded
3. Too many existing backups

**Solutions:**

**Solution 1: Free Up Disk Space**
```powershell
# Check available space
Get-PSDrive -Name C

# Remove old backups
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Sort-Object LastWriteTime |
    Select-Object -First 5 |
    Remove-Item -Force
```

**Solution 2: Enable Auto-Cleanup**
```powershell
# Create config for automatic cleanup
$configPath = "$env:USERPROFILE\.claude-orca\config.json"
$config = @{
    maxBackupCount = 5
    backupRetentionDays = 7
    autoCleanupOldBackups = $true
} | ConvertTo-Json
Set-Content -Path $configPath -Value $config
```

**Solution 3: Move Backups to Different Drive**
```powershell
# Move existing backups to external drive
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
$externalDrive = "E:\Orca-Backups"
New-Item -ItemType Directory -Path $externalDrive -Force
Move-Item "$backupsDir\orca-db-*.tar.gz" $externalDrive
```

**Solution 4: Clean Docker Images**
```powershell
# Free up Docker disk space
docker system prune -a -f
```

---

### Issue 8: "Permission denied: /volume"

**Error Message:**
```
tar: can't open '/volume': Permission denied
```

**Causes:**
1. Volume mount permissions
2. Docker Desktop WSL2 issues
3. Windows file sharing settings

**Solutions:**

**Solution 1: Restart Docker Desktop**
```powershell
# Stop Docker Desktop
# Start Docker Desktop
# Wait for full startup
# Retry backup
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
(WARNING: This will delete all Docker data)
```

---

### Issue 9: "Backup takes too long"

**Symptom:**
Backup hangs or takes more than 5 minutes

**Causes:**
1. Very large database (>1 GB)
2. Slow disk (HDD vs SSD)
3. Docker resource limits
4. Background processes

**Solutions:**

**Solution 1: Check Database Size**
```powershell
$volumeName = docker volume ls --filter "name=orca.apphost" --format "{{.Name}}" |
    Where-Object { $_ -like "*sql-data*" }

# Check volume size
docker run --rm -v "${volumeName}:/volume:ro" alpine du -sh /volume
```

**Solution 2: Increase Docker Resources**
```
Docker Desktop → Settings → Resources
- Memory: 4GB → 8GB
- CPUs: 2 → 4
```

**Solution 3: Close Unnecessary Applications**
- Close Visual Studio, browsers, etc.
- Stop other Docker containers
- Pause OneDrive sync temporarily

**Solution 4: Use Faster Compression (Future Enhancement)**
```powershell
# Current: gzip (slower, better compression)
# Future: Use -CompressionLevel flag
& .\Backup-DockerVolume.ps1 -CompressionLevel Fast
```

---

### Issue 10: "Backup corrupted or unreadable"

**Symptom:**
Restore fails with "invalid tar archive" or similar

**Causes:**
1. Backup interrupted mid-creation
2. Disk errors during write
3. File transferred incorrectly (wrong mode)
4. Antivirus quarantine

**Solutions:**

**Solution 1: Verify Backup Integrity**
```powershell
$backupPath = "$env:USERPROFILE\.claude-orca\backups\orca-db-2025-10-31-14-30.tar.gz"

# Test tar.gz file
docker run --rm -v "$($backupPath):/test.tar.gz:ro" alpine tar -tzf /test.tar.gz
```

**Expected output:** List of files in archive

**Error output:**
```
gzip: stdin: not in gzip format
tar: This does not look like a tar archive
```

**Solution 2: Create New Backup**
```powershell
# Delete corrupted backup
Remove-Item $backupPath -Force

# Create fresh backup
& .\Backup-DockerVolume.ps1
```

**Solution 3: Check Antivirus Logs**
- Check if backup was quarantined
- Add exclusion for `.claude-orca\backups\`
- Restore from quarantine if possible

**Solution 4: Check Disk Health**
```powershell
# Run disk check (requires admin)
chkdsk C: /F
```

## Performance Optimization

### Slow Backups

**Diagnosis:**
```powershell
# Time a backup
Measure-Command {
    & .\Backup-DockerVolume.ps1 -CustomName "perf-test"
}
```

**Optimizations:**

1. **Use SSD for user profile** (if currently on HDD)
2. **Increase Docker memory** (Settings → Resources → Memory: 8GB+)
3. **Close unnecessary applications** during backup
4. **Pause antivirus scanning** temporarily
5. **Run backup during low-activity times**

### Large Backup Files

**Diagnosis:**
```powershell
$backupsDir = "$env:USERPROFILE\.claude-orca\backups"
Get-ChildItem $backupsDir -Filter "orca-db-*.tar.gz" |
    Sort-Object Length -Descending |
    Select-Object Name, @{Label="Size (MB)";Expression={[math]::Round($_.Length/1MB,2)}}
```

**Optimizations:**

1. **Clean up old Orca data** before backup
2. **Enable aggressive cleanup** (keep only 5 backups)
3. **Archive old backups** to external storage
4. **Consider incremental backups** (future feature)

## Getting Help

### Enable Verbose Output

```powershell
& .\Backup-DockerVolume.ps1 -Verbose
```

Shows detailed diagnostic information.

### Capture Full Output

```powershell
& .\Backup-DockerVolume.ps1 -Verbose *>&1 | Tee-Object -FilePath "backup-log.txt"
```

Saves all output to file for troubleshooting.

### Check Docker Logs

```powershell
docker ps -a | Select-String "alpine"
docker logs <container-id>
```

### Environment Information

```powershell
Write-Host "=== Environment Information ===" -ForegroundColor Cyan
Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"
Write-Host "OS: $(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty Caption)"
Write-Host "User Profile: $env:USERPROFILE"
docker version
docker info
```

## Related Documentation

- [Backup Workflow](./backup-workflow.md) - Complete backup process
- [Naming Conventions](./backup-naming.md) - Backup naming patterns
- [Cleanup Strategy](./cleanup-strategy.md) - Retention policies

---

**Last Updated:** 2025-10-31
