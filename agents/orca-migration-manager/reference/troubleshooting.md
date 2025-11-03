# Troubleshooting - Orca Migration Manager

This document covers common issues when managing Orca database migrations and their solutions.

## Quick Diagnostics

### Health Check Script

```powershell
Write-Host "=== Orca Migration Manager Health Check ===" -ForegroundColor Cyan
Write-Host ""

# Check 1: Connection cache
Write-Host "1. Connection Cache:" -ForegroundColor Yellow
$cacheFile = "$env:USERPROFILE\.claude-orca\connection-cache"
if (Test-Path $cacheFile) {
    Write-Host "   [OK] Cache exists" -ForegroundColor Green
    Get-Content $cacheFile | Where-Object { $_ -notlike "#*" } | ForEach-Object {
        Write-Host "      $_" -ForegroundColor Gray
    }
} else {
    Write-Host "   [OK] No cache (first run)" -ForegroundColor Yellow
}

# Check 2: SQL Container
Write-Host "2. SQL Container:" -ForegroundColor Yellow
$sqlContainer = docker ps --filter "expose=1433" --format "{{.Names}}" 2>$null |
    Select-String -Pattern "sql" | Select-Object -First 1
if ($sqlContainer) {
    Write-Host "   [OK] Found: $sqlContainer" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] No SQL container found" -ForegroundColor Red
}

# Check 3: actions.api build
Write-Host "3. actions.api Build:" -ForegroundColor Yellow
$devRoot = $env:DEV_ROOT
if (!$devRoot) { $devRoot = "D:\dev" }
$actionsApiBin = "$devRoot\actions.api\src\bin\Debug\net9.0\actions.api.dll"
if (Test-Path $actionsApiBin) {
    $buildDate = (Get-Item $actionsApiBin).LastWriteTime
    Write-Host "   [OK] Built: $buildDate" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] Not built" -ForegroundColor Red
}

# Check 4: EF Core tools
Write-Host "4. EF Core Tools:" -ForegroundColor Yellow
try {
    $efVersion = dotnet ef --version 2>&1 | Select-Object -First 1
    Write-Host "   [OK] $efVersion" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] Not installed" -ForegroundColor Red
}
```

---

## Connection Issues

### Issue 1: "No SQL container found"

**Error Message:**
```
No SQL container found with port 1433 exposed
```

**Causes:**
1. Docker Desktop not running
2. SQL container not started
3. Orca not launched yet
4. Container name doesn't contain "sql"

**Solutions:**

**Solution 1: Start Docker Desktop**
```
1. Open Docker Desktop
2. Wait for engine to start (green indicator)
3. Retry migration command
```

**Solution 2: Launch Orca**
```
"launch orca"
```

Orca will create SQL container automatically on first launch.

**Solution 3: Check Container Manually**
```powershell
docker ps

# Look for container with:
# - Port 1433 exposed
# - Name contains "sql"

# If container exists but name is unexpected:
docker ps --filter "expose=1433"
```

**Solution 4: Recreate Container**
```powershell
# Stop Orca
& "D:\dev\resolve.dev.resources\scripts\Actions Manager Utils.ps1"
Stop-Actions-Processes

# Remove old containers
docker ps -a --filter "name=sql" --format "{{.ID}}" | ForEach-Object {
    docker rm -f $_
}

# Launch Orca (creates fresh container)
"launch orca"
```

---

### Issue 2: "Login failed for user 'sa'"

**Error Message:**
```
Login failed for user 'sa'. Reason: Password did not match
```

**Causes:**
1. Cached password wrong (container recreated)
2. SA password changed
3. Connection cache outdated

**Solutions:**

**Solution 1: Delete Cache**
```powershell
Remove-Item "$env:USERPROFILE\.claude-orca\connection-cache" -Force
```

Next migration command will rediscover connection with new password.

**Solution 2: Force Rediscovery**
```
"rediscover orca database connection"
```

Ignores cache, runs full discovery immediately.

**Solution 3: Manual Password Check**
```powershell
# Get container name
$container = docker ps --filter "expose=1433" --format "{{.Names}}" |
    Select-String "sql" | Select-Object -First 1

# Get SA password from container
$envVars = docker inspect $container --format='{{range .Config.Env}}{{println .}}{{end}}'
$password = ($envVars | Select-String "MSSQL_SA_PASSWORD=") -replace "MSSQL_SA_PASSWORD=", ""

# Test connection
docker exec $container /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U sa -P "$password" -C -Q "SELECT 1"
```

If this works, cache has wrong password - delete cache and retry.

---

### Issue 3: "Cannot open database"

**Error Message:**
```
Cannot open database "<database>". Login failed.
```

**Causes:**
1. Database deleted or renamed
2. Cached database name wrong
3. Database not yet created

**Solutions:**

**Solution 1: Check Database Exists**
```powershell
# Get container and password (from health check script)
$container = docker ps --filter "expose=1433" --format "{{.Names}}" |
    Select-String "sql" | Select-Object -First 1
$envVars = docker inspect $container --format='{{range .Config.Env}}{{println .}}{{end}}'
$password = ($envVars | Select-String "MSSQL_SA_PASSWORD=") -replace "MSSQL_SA_PASSWORD=", ""

# List all databases
docker exec $container /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U sa -P "$password" -C -Q "SELECT name FROM sys.databases"
```

**Solution 2: Delete Cache and Rediscover**
```powershell
Remove-Item "$env:USERPROFILE\.claude-orca\connection-cache" -Force
```

Rediscovery will find correct database name.

**Solution 3: Create Tenant Database**

If no tenant database exists:
1. Launch Orca: `"launch orca"`
2. Access dashboard: `https://localhost:17206/login?t=...`
3. Create tenant via UI
4. Retry migration command

---

## Migration Issues

### Issue 4: "Migration <name> not found"

**Error Message:**
```
Migration 'AddUserTable' not found
```

**Causes:**
1. Wrong migration name (typo)
2. Migration not in code yet
3. actions.api not built
4. Wrong context specified

**Solutions:**

**Solution 1: List Available Migrations**
```bash
cd /d/dev/actions.api && dotnet ef migrations list \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build
```

Compare output to requested migration name.

**Solution 2: Build actions.api**
```bash
cd /d/dev/actions.api && dotnet build actions.api.sln
```

Then retry migration command.

**Solution 3: Check Migration File Exists**
```powershell
$devRoot = $env:DEV_ROOT
if (!$devRoot) { $devRoot = "D:\dev" }

Get-ChildItem "$devRoot\actions.api\src\Migrations\*_AddUserTable.cs"
```

If file missing, migration doesn't exist in code.

---

### Issue 5: "Build required before migration"

**Error Message:**
```
Build actions.api before running migrations
```

**Cause:** actions.api not built (--no-build requires existing binaries)

**Solutions:**

**Solution 1: Build Manually**
```bash
cd /d/dev/actions.api && dotnet build actions.api.sln
```

**Solution 2: Use Orca Skill (Auto-builds)**
```
"launch orca"
```

Orca skill automatically builds actions.api if needed.

**Solution 3: Remove --no-build Flag**

Edit migration commands to remove `--no-build`:
```bash
# Slower but always works
dotnet ef database update --project src/actions.api.csproj --context TenantDbContext
```

---

### Issue 6: "Foreign key constraint violation"

**Error Message:**
```
The DELETE statement conflicted with the REFERENCE constraint
```

**Causes:**
1. Down() method dropping table with foreign key references
2. Migration order incorrect
3. Schema out of sync

**Solutions:**

**Solution 1: Check Migration Dependencies**

Look at Down() method:
```csharp
protected override void Down(MigrationBuilder migrationBuilder)
{
    // WRONG ORDER: Tries to drop Users before UserRoles
    migrationBuilder.DropTable(name: "Users");
    migrationBuilder.DropTable(name: "UserRoles");  // References Users!

    // CORRECT ORDER: Drop referencing table first
    migrationBuilder.DropTable(name: "UserRoles");
    migrationBuilder.DropTable(name: "Users");
}
```

**Solution 2: Drop Constraints First**
```csharp
protected override void Down(MigrationBuilder migrationBuilder)
{
    // Drop foreign key constraints first
    migrationBuilder.DropForeignKey(
        name: "FK_UserRoles_Users_UserId",
        table: "UserRoles");

    // Then drop tables
    migrationBuilder.DropTable(name: "UserRoles");
    migrationBuilder.DropTable(name: "Users");
}
```

**Solution 3: Manual Cleanup (Last Resort)**
```sql
-- Connect to database manually
-- Drop foreign keys first
ALTER TABLE [UserRoles] DROP CONSTRAINT [FK_UserRoles_Users_UserId];

-- Then retry migration rollback
```

---

### Issue 7: "Column <name> already exists"

**Error Message:**
```
There is already an object named 'Email' in the database.
```

**Causes:**
1. Migration history out of sync with schema
2. Migration partially applied
3. Manual schema changes

**Solutions:**

**Solution 1: Check Migration History**
```sql
-- Connect to database
SELECT MigrationId FROM [__EFMigrationsHistory] ORDER BY MigrationId;
```

Compare to actual schema:
```sql
SELECT TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Users'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
```

**Solution 2: Manually Mark Migration as Applied**

If schema change exists but history missing:
```sql
-- Add migration to history (DANGEROUS - use with caution)
INSERT INTO [__EFMigrationsHistory] (MigrationId, ProductVersion)
VALUES ('20231016140000_AddUserTable', '9.0.0');
```

**Solution 3: Restore Database from Backup**

Nuclear option if history completely corrupted:
```
"restore orca database"
```

Then reapply migrations from clean state.

---

### Issue 8: "Pending changes prevent rollback"

**Error Message:**
```
Cannot roll back migration while database has uncommitted changes
```

**Causes:**
1. Open transaction in another session
2. Locked database connections
3. Orca still accessing database

**Solutions:**

**Solution 1: Close Orca Connections**
```powershell
# Stop Orca
& "D:\dev\resolve.dev.resources\scripts\Actions Manager Utils.ps1"
Stop-Actions-Processes

# Wait for connections to close
Start-Sleep -Seconds 3

# Retry migration command
```

**Solution 2: Kill Database Sessions**
```sql
-- Find active sessions (connect to SQL Server)
USE master;
GO

SELECT session_id, login_name, host_name, program_name
FROM sys.dm_exec_sessions
WHERE database_id = DB_ID('RDTest');

-- Kill sessions (use session_id from above)
KILL <session_id>;
```

**Solution 3: Restart SQL Container**
```powershell
# Stop container
docker stop <container-name>

# Start container
docker start <container-name>

# Wait for SQL Server to start
Start-Sleep -Seconds 10

# Retry migration command
```

---

## Performance Issues

### Issue 9: "Migration taking too long"

**Symptom:** Migration command runs for 5+ minutes

**Causes:**
1. Large table with data migration
2. Adding index to large table
3. Network latency (remote database)
4. Slow disk I/O

**Solutions:**

**Solution 1: Check Migration Logic**

Look for expensive operations:
```csharp
// SLOW: Adds column with default to large table
migrationBuilder.AddColumn<string>(
    name: "Status",
    table: "Workflows",
    defaultValue: "Active");  // Updates ALL rows!

// FASTER: Add nullable column, update in batches, then set not null
migrationBuilder.AddColumn<string>(
    name: "Status",
    table: "Workflows",
    nullable: true);

// Update in batches (custom SQL)
migrationBuilder.Sql(@"
    UPDATE TOP (1000) Workflows
    SET Status = 'Active'
    WHERE Status IS NULL
");
```

**Solution 2: Monitor Database Activity**

While migration runs:
```sql
-- Check active queries
SELECT session_id, status, command, wait_type, wait_time,
       percent_complete, estimated_completion_time
FROM sys.dm_exec_requests
WHERE database_id = DB_ID('RDTest');
```

**Solution 3: Run During Off-Hours**

If migration must be slow:
- Run when Orca not in use
- Accept downtime
- Monitor progress

---

### Issue 10: "Connection discovery slow"

**Symptom:** Takes 10+ seconds to discover connection

**Causes:**
1. Docker Desktop slow to respond
2. Many containers running
3. SQL query slow

**Solutions:**

**Solution 1: Use Connection Cache**

Cache hit should be <100ms:
```powershell
# Check cache exists
Test-Path "$env:USERPROFILE\.claude-orca\connection-cache"

# If missing or outdated, delete and recreate
Remove-Item "$env:USERPROFILE\.claude-orca\connection-cache" -Force
```

**Solution 2: Reduce Docker Load**

Stop unnecessary containers:
```powershell
docker ps --format "{{.Names}}" | ForEach-Object {
    if ($_ -notlike "*sql*" -and $_ -notlike "*orca*") {
        docker stop $_
    }
}
```

**Solution 3: Restart Docker Desktop**

If Docker performance degraded:
1. Quit Docker Desktop
2. Wait 10 seconds
3. Start Docker Desktop
4. Wait for engine to start
5. Retry discovery

---

## EF Core Tool Issues

### Issue 11: "dotnet ef command not found"

**Error Message:**
```
'dotnet' is not recognized as an internal or external command
```

**Causes:**
1. .NET SDK not installed
2. .NET not in PATH
3. Wrong PowerShell/terminal

**Solutions:**

**Solution 1: Install .NET SDK**
```
Download: https://dotnet.microsoft.com/download/dotnet/9.0
Install: .NET 9.0 SDK
Restart terminal
```

**Solution 2: Check PATH**
```powershell
$env:PATH -split ';' | Select-String "dotnet"

# Should show:
# C:\Program Files\dotnet\
```

**Solution 3: Use Full Path**
```bash
& "C:\Program Files\dotnet\dotnet.exe" ef database update ...
```

---

### Issue 12: "EF Core tools not installed"

**Error Message:**
```
Could not execute because the specified command or file was not found.
Possible reasons for this include:
  * You misspelled a built-in dotnet command.
  * You intended to execute a .NET program, but dotnet-ef does not exist.
```

**Causes:**
1. EF Core global tools not installed
2. Wrong .NET SDK version
3. Tools outdated

**Solutions:**

**Solution 1: Install EF Core Tools**
```powershell
dotnet tool install --global dotnet-ef
```

**Solution 2: Update EF Core Tools**
```powershell
dotnet tool update --global dotnet-ef
```

**Solution 3: Verify Installation**
```powershell
dotnet ef --version

# Should show: Entity Framework Core .NET Command-line Tools 9.0.x
```

---

## Cache Issues

### Issue 13: "Cache file corrupted"

**Error Message:**
```
Cannot parse connection cache file
```

**Causes:**
1. Manual editing with syntax errors
2. File truncated (disk full)
3. Encoding issues

**Solutions:**

**Solution 1: Delete Cache**
```powershell
Remove-Item "$env:USERPROFILE\.claude-orca\connection-cache" -Force
```

Next command rediscovers connection.

**Solution 2: Manually Fix Cache**

Expected format:
```
# Comments
SQL_CONTAINER=container-name
SA_PASSWORD=password
TENANT_DATABASE=database
SERVER=127.0.0.1,1433
```

Fix syntax errors, save with UTF-8 encoding.

**Solution 3: Recreate Cache Directory**
```powershell
$cacheDir = "$env:USERPROFILE\.claude-orca"
Remove-Item $cacheDir -Recurse -Force
New-Item -ItemType Directory -Path $cacheDir
```

---

## Getting Help

### Enable Verbose Output

```powershell
# Run discovery with verbose
& .\Discover-OrcaConnection.ps1 -Verbose

# Output shows:
# - Cache read attempts
# - Docker commands
# - SQL queries
# - Connection tests
```

### Capture Full Output

```powershell
& .\Discover-OrcaConnection.ps1 -Verbose *>&1 | Tee-Object -FilePath "discovery-log.txt"
```

### Check Individual Components

```powershell
# Test Docker access
docker ps

# Test SQL container access
$container = docker ps --filter "expose=1433" --format "{{.Names}}" |
    Select-String "sql" | Select-Object -First 1
docker exec $container /opt/mssql-tools18/bin/sqlcmd -?

# Test EF Core
dotnet ef --version

# Test actions.api build
cd /d/dev/actions.api && dotnet build actions.api.sln
```

---

## Related Documentation

- [Connection Discovery](./connection-discovery.md) - How connection discovery works
- [Migration Commands](./migration-commands.md) - All EF Core migration commands

---

**Last Updated:** 2025-11-03
