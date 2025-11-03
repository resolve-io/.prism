# Connection Discovery - Orca SQL Server

This document details how the orca-migration-manager agent discovers and caches SQL Server connection parameters.

## Overview

Connection discovery is a **two-tier system**:
1. **Fast path**: Use cached connection (~100ms)
2. **Slow path**: Full discovery via Docker (~2-5 seconds)

## Discovery Strategies

### Strategy 1: Cache Hit (Fast Path)

**Conditions:** Cache file exists and connection test passes

**Process:**
1. Read cache file: `$env:USERPROFILE\.claude-orca\connection-cache`
2. Parse key-value pairs:
   ```
   SQL_CONTAINER=sql-cc67ab6e00
   SA_PASSWORD=Ux8Ge+ZJb4{{hT)d)n!(z_
   TENANT_DATABASE=RDTest
   SERVER=127.0.0.1,1433
   ```
3. Test connection:
   ```powershell
   docker exec $sqlContainer /opt/mssql-tools18/bin/sqlcmd `
     -S localhost -U sa -P "$saPassword" -C -Q "SELECT 1"
   ```
4. If test succeeds, return cached values immediately

**Time:** <100ms (no Docker queries needed)

**Success Rate:** ~95% (only fails if container recreated or password changed)

---

### Strategy 2: Full Discovery (Slow Path)

**Triggers:**
- No cache file exists (first run)
- Cached container doesn't exist anymore
- Connection test fails (wrong password)
- `-Force` parameter used

**Process:**

#### Step 1: Find SQL Container

**Method:** Query Docker for containers exposing port 1433

```powershell
docker ps --filter "expose=1433" --format "{{.Names}}" 2>$null |
    Select-String -Pattern "sql" |
    Select-Object -First 1
```

**What it does:**
- Lists all running containers
- Filters to those exposing port 1433 (SQL Server default)
- Searches for "sql" in container name
- Returns first match

**Expected result:** Container name like `sql-cc67ab6e00`

**Failure cases:**
- No containers found → "No SQL container found with port 1433 exposed"
- Multiple containers → Uses first match (deterministic)

#### Step 2: Extract SA Password

**Method:** Inspect container environment variables

```powershell
$envVars = docker inspect $sqlContainer --format='{{range .Config.Env}}{{println .}}{{end}}'
$saPassword = ($envVars | Select-String "MSSQL_SA_PASSWORD=" |
    ForEach-Object { $_ -replace "MSSQL_SA_PASSWORD=", "" }).Trim()
```

**What it does:**
- Gets all environment variables from container
- Finds `MSSQL_SA_PASSWORD=<value>` line
- Extracts password value
- Trims whitespace

**Expected result:** Strong password like `Ux8Ge+ZJb4{{hT)d)n!(z_`

**Failure cases:**
- Environment variable missing → "Could not find MSSQL_SA_PASSWORD in container"
- Empty password → Rare, but validation fails

#### Step 3: Discover Tenant Database

**Method:** SQL query via sqlcmd in container

```powershell
$query = @"
SET NOCOUNT ON;
SELECT name FROM sys.databases
WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb', 'ResolveMaster', 'featureflagDb')
"@

$sqlCmd = "docker exec $sqlContainer /opt/mssql-tools18/bin/sqlcmd " +
    "-S localhost -U sa -P `"$saPassword`" -C -Q `"$query`" -h -1"

$tenantDatabase = Invoke-Expression $sqlCmd 2>$null |
    Where-Object { $_.Trim() } |
    Select-Object -First 1 |
    ForEach-Object { $_.Trim() }
```

**What it does:**
- Executes SQL query inside container
- Lists all databases
- Excludes system databases (master, tempdb, model, msdb)
- Excludes Resolve system databases (ResolveMaster, featureflagDb)
- Returns first user database found

**Excluded databases:**
- `master` - SQL Server system database
- `tempdb` - Temporary storage
- `model` - Template for new databases
- `msdb` - SQL Agent database
- `ResolveMaster` - Resolve platform database
- `featureflagDb` - Feature flag database

**Expected result:** Tenant database name like `RDTest`

**Failure cases:**
- No user databases → "No tenant database found"
- Multiple tenant databases → Uses first match

#### Step 4: Build Connection String

**Format:** Standard SQL Server connection string

```powershell
$server = "127.0.0.1,1433"
$connectionString = "Server=$server;" +
    "Database=$tenantDatabase;" +
    "User Id=sa;" +
    "Password=$saPassword;" +
    "Encrypt=False;" +
    "TrustServerCertificate=True;"
```

**Parameters:**
- `Server`: Localhost with port 1433
- `Database`: Discovered tenant database
- `User Id`: SA (system administrator)
- `Password`: Extracted from container
- `Encrypt`: False (local development)
- `TrustServerCertificate`: True (self-signed cert)

#### Step 5: Update Cache

**Cache format:** Simple key-value pairs

```powershell
$cacheContent = @"
# Orca Migrations Connection Cache
# Auto-updated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")

SQL_CONTAINER=$sqlContainer
SA_PASSWORD=$saPassword
TENANT_DATABASE=$tenantDatabase
SERVER=$server
"@

Set-Content -Path $connectionCacheFile -Value $cacheContent
```

**Cache location:** `$env:USERPROFILE\.claude-orca\connection-cache`

**Cache lifecycle:**
- Created: First discovery run
- Updated: Every successful discovery
- Invalidated: Never (relies on connection test failure to trigger rediscovery)
- Deleted: Manually by user (forces rediscovery)

---

## Cache File Format

### Structure

```
# Comments (lines starting with #)
KEY=VALUE
KEY2=VALUE2
```

### Example

```
# Orca Migrations Connection Cache
# Auto-updated: 2025-11-03 14:23:15 UTC

SQL_CONTAINER=sql-cc67ab6e00
SA_PASSWORD=Ux8Ge+ZJb4{{hT)d)n!(z_
TENANT_DATABASE=RDTest
SERVER=127.0.0.1,1433
```

### Parsing Logic

```powershell
$cacheContent = Get-Content $connectionCacheFile -Raw
$cache = @{}

foreach ($line in ($cacheContent -split "`n")) {
    if ($line -match "^([^=]+)=(.+)$") {
        $cache[$matches[1]] = $matches[2].Trim()
    }
}
```

**Rules:**
- Ignore blank lines
- Ignore comment lines (start with `#`)
- Parse `KEY=VALUE` format
- Trim whitespace from values
- Store in hashtable for lookup

---

## Connection Testing

### Test Query

```sql
SELECT 1
```

**Why this query?**
- Minimal overhead
- Tests authentication
- Tests database connectivity
- Returns immediately
- No side effects

### Test Command

```powershell
docker exec $sqlContainer /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U sa -P "$saPassword" -C -Q "SELECT 1"
```

**Exit codes:**
- `0` - Success (connection valid)
- `1` - Authentication failed (wrong password)
- `2` - Connection failed (container not running)

### Failure Handling

**On test failure:**
1. Log verbose message: "Cached connection test failed, rediscovering..."
2. Fall through to full discovery
3. Don't throw error (graceful degradation)

**On discovery failure:**
1. Throw exception with clear message
2. Don't update cache (preserve last good state)
3. Agent reports error to user

---

## Performance Characteristics

### Cache Hit Path

**Timeline:**
```
0ms     - Read cache file
2ms     - Parse cache content
10ms    - Start Docker exec (connection test)
100ms   - Connection test completes
102ms   - Return connection object
```

**Total: ~100ms**

### Cache Miss Path

**Timeline:**
```
0ms     - Read cache file (or detect missing)
2ms     - Parse fails or test fails
10ms    - Start container discovery
500ms   - Docker ps completes
510ms   - Start inspect for password
800ms   - Docker inspect completes
810ms   - Start sqlcmd for database discovery
2000ms  - Database query completes
2010ms  - Build connection string
2020ms  - Write cache file
2030ms  - Return connection object
```

**Total: ~2-5 seconds** (varies by Docker performance)

### First Run

**No cache file exists:**
- Skip cache read
- Immediately run full discovery
- Create cache for future runs

**Time:** 2-5 seconds (same as cache miss)

---

## Environment Assumptions

### Docker Container

**Required:**
- Container must be running
- Container name contains "sql"
- Container exposes port 1433
- SQL Server running inside container

**Tools inside container:**
- `/opt/mssql-tools18/bin/sqlcmd` - SQL Server command-line tool
- Standard SQL Server 2022 container includes this

### SQL Server

**Required:**
- SA account enabled (default)
- SA password set via `MSSQL_SA_PASSWORD` environment variable
- At least one tenant database exists

**Optional:**
- ResolveMaster database (excluded from discovery)
- featureflagDb database (excluded from discovery)

### PowerShell

**Required:**
- Docker CLI available in PATH
- PowerShell 5.1 or later

**Cmdlets used:**
- `Get-Content` - Read cache file
- `Set-Content` - Write cache file
- `Test-Path` - Check cache existence
- `Select-String` - Pattern matching
- `Invoke-Expression` - Execute Docker commands

---

## Troubleshooting

### "No SQL container found"

**Cause:** No container exposing port 1433 with "sql" in name

**Solutions:**
1. Check if Orca is running: `docker ps`
2. Start Orca: Launch via orca skill
3. Verify container naming: `docker ps --filter "expose=1433"`

### "Could not find MSSQL_SA_PASSWORD"

**Cause:** Container missing environment variable

**Solutions:**
1. Container created incorrectly (not by Orca)
2. Recreate container: Stop Orca, remove containers, relaunch
3. Check manually: `docker inspect <container> --format='{{.Config.Env}}'`

### "No tenant database found"

**Cause:** No user databases exist (only system databases)

**Solutions:**
1. Fresh Orca install (no tenant created yet)
2. Create tenant via Orca UI
3. Run migrations: `dotnet ef database update`

### "Login failed for user 'sa'"

**Cause:** Cached password wrong (container recreated)

**Solutions:**
1. Delete cache: `Remove-Item "$env:USERPROFILE\.claude-orca\connection-cache"`
2. Rediscover: Use `-Force` parameter
3. Connection will be rediscovered automatically

### "Cannot open database"

**Cause:** Cached database name wrong (database deleted/renamed)

**Solutions:**
1. Delete cache (same as above)
2. Rediscovery will find current database
3. If no database exists, agent will report error

---

## Force Rediscovery

### When to Use

- After Orca restart (new containers)
- After database restore
- After manual Docker changes
- Testing connection discovery

### Command

**Agent request:** `"rediscover orca database connection"`

**Script call:**
```powershell
& .\Discover-OrcaConnection.ps1 -Force
```

**Effect:**
- Ignores cache completely
- Runs full discovery
- Updates cache with new values
- Returns fresh connection

---

## Related Scripts

- **Discover-OrcaConnection.ps1** - This discovery process
- **Get-CachePath.ps1** (shared) - Cache directory management

---

**Last Updated:** 2025-11-03
