<#
.SYNOPSIS
    Discovers Orca SQL Server connection parameters.

.DESCRIPTION
    Finds the SQL container, extracts credentials, and discovers the tenant database.
    Caches the connection information for performance.

.PARAMETER Force
    Force rediscovery even if cache exists

.OUTPUTS
    [PSCustomObject] with properties:
    - SqlContainer (string)
    - SaPassword (string)
    - TenantDatabase (string)
    - Server (string)
    - ConnectionString (string)

.EXAMPLE
    $conn = & .\Discover-OrcaConnection.ps1
    Write-Host "Database: $($conn.TenantDatabase)"

.NOTES
    Cache location: $env:USERPROFILE\.claude-orca\connection-cache
#>

[CmdletBinding()]
param(
    [switch]$Force
)

# Get cache path
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$agentDir = Split-Path -Parent $scriptDir
$agentsDir = Split-Path -Parent $agentDir
$prismDir = Split-Path -Parent $agentsDir
$backupSkillDir = Join-Path $prismDir "skills\backup-orca-db"
$cacheScript = Join-Path $backupSkillDir "scripts\Get-CachePath.ps1"

$cacheDir = & $cacheScript
$connectionCacheFile = Join-Path $cacheDir "connection-cache"

Write-Verbose "Connection cache file: $connectionCacheFile"

# Try cached connection first (unless Force)
if (!$Force -and (Test-Path $connectionCacheFile)) {
    Write-Verbose "Reading connection cache..."

    $cacheContent = Get-Content $connectionCacheFile -Raw
    $cache = @{}

    foreach ($line in ($cacheContent -split "`n")) {
        if ($line -match "^([^=]+)=(.+)$") {
            $cache[$matches[1]] = $matches[2].Trim()
        }
    }

    # Test cached connection
    if ($cache["SQL_CONTAINER"] -and $cache["SA_PASSWORD"]) {
        Write-Verbose "Testing cached connection..."

        try {
            $testCmd = "docker exec $($cache['SQL_CONTAINER']) /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P `"$($cache['SA_PASSWORD'])`" -C -Q `"SELECT 1`""
            $result = Invoke-Expression $testCmd 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Using cached connection" -ForegroundColor Green

                return [PSCustomObject]@{
                    SqlContainer = $cache["SQL_CONTAINER"]
                    SaPassword = $cache["SA_PASSWORD"]
                    TenantDatabase = $cache["TENANT_DATABASE"]
                    Server = $cache["SERVER"]
                    ConnectionString = "Server=$($cache['SERVER']);Database=$($cache['TENANT_DATABASE']);User Id=sa;Password=$($cache['SA_PASSWORD']);Encrypt=False;TrustServerCertificate=True;"
                }
            } else {
                Write-Verbose "Cached connection test failed, rediscovering..."
            }
        } catch {
            Write-Verbose "Cached connection test failed: $_"
        }
    }
}

# Discovery process
Write-Host "Discovering Orca SQL connection..." -ForegroundColor Yellow

# Step 1: Find SQL container
Write-Verbose "Finding SQL container..."
$sqlContainer = docker ps --filter "expose=1433" --format "{{.Names}}" 2>$null |
    Select-String -Pattern "sql" |
    Select-Object -First 1 |
    ForEach-Object { $_.ToString() }

if (!$sqlContainer) {
    throw "No SQL container found with port 1433 exposed"
}

Write-Host "  [OK] Found SQL container: $sqlContainer" -ForegroundColor Green

# Step 2: Extract SA password
Write-Verbose "Extracting SA password..."
$envVars = docker inspect $sqlContainer --format='{{range .Config.Env}}{{println .}}{{end}}' 2>$null
$saPassword = ($envVars | Select-String "MSSQL_SA_PASSWORD=" | ForEach-Object { $_ -replace "MSSQL_SA_PASSWORD=", "" }).Trim()

if (!$saPassword) {
    throw "Could not find MSSQL_SA_PASSWORD in container $sqlContainer"
}

Write-Host "  [OK] Found SA password" -ForegroundColor Green

# Step 3: Discover tenant database
Write-Verbose "Discovering tenant database..."
$query = "SET NOCOUNT ON; SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb', 'ResolveMaster', 'featureflagDb')"
$sqlCmd = "docker exec $sqlContainer /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P `"$saPassword`" -C -Q `"$query`" -h -1"

$tenantDatabase = Invoke-Expression $sqlCmd 2>$null |
    Where-Object { $_.Trim() } |
    Select-Object -First 1 |
    ForEach-Object { $_.Trim() }

if (!$tenantDatabase) {
    throw "No tenant database found"
}

Write-Host "  [OK] Found tenant database: $tenantDatabase" -ForegroundColor Green

# Step 4: Build connection info
$server = "127.0.0.1,1433"
$connectionString = "Server=$server;Database=$tenantDatabase;User Id=sa;Password=$saPassword;Encrypt=False;TrustServerCertificate=True;"

# Step 5: Update cache
Write-Verbose "Updating connection cache..."
$cacheContent = @"
# Orca Migrations Connection Cache
# Auto-updated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss UTC")

SQL_CONTAINER=$sqlContainer
SA_PASSWORD=$saPassword
TENANT_DATABASE=$tenantDatabase
SERVER=$server
"@

Set-Content -Path $connectionCacheFile -Value $cacheContent
Write-Host "  [OK] Connection cache updated" -ForegroundColor Green

return [PSCustomObject]@{
    SqlContainer = $sqlContainer
    SaPassword = $saPassword
    TenantDatabase = $tenantDatabase
    Server = $server
    ConnectionString = $connectionString
}
