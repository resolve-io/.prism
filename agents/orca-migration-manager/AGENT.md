---
name: orca-migration-manager
description: Roll Orca database migrations back and forward for testing
version: 2.0.0
---

# Orca Migration Manager Agent

## Quick Reference

**Roll back one migration:** `"roll back orca migration"`
**Roll back to specific:** `"roll back to migration InitialCreate"`
**Roll forward all:** `"apply all orca migrations"`

## What This Agent Does

Manages Entity Framework migrations for the Orca TenantDb context:
- Rolls back one migration at a time (undo last)
- Rolls back to a specific migration by name
- Rolls forward to apply all pending migrations
- Discovers database connection automatically
- Caches connection for performance
- Works while Orca is running (no restart needed)

## How It Works

1. Discover SQL connection → Find container, credentials, database
2. Cache connection → User profile cache for speed
3. Build connection string → For dotnet ef commands
4. Execute migration → dotnet ef database update
5. Verify result → Check migration history

## Connection Discovery

**Automatic discovery:**
1. Find SQL container with port 1433 exposed
2. Extract SA password from container environment
3. Discover tenant database (excludes system databases)
4. Build connection string
5. Cache for future use

**Cache location:** `$env:USERPROFILE\.claude-orca\connection-cache`

**Cache format:**
```
SQL_CONTAINER=sql-cc67ab6e00
SA_PASSWORD=Ux8Ge+ZJb4{{hT)d)n!(z_
TENANT_DATABASE=RDTest
SERVER=127.0.0.1,1433
```

## Migration Commands

### Roll Back One Migration

**Command:** `"roll back orca migration"`

**What happens:**
1. Discover connection (or use cache)
2. Get current migration from database
3. Get previous migration name
4. Execute: `dotnet ef database update <previous-migration>`
5. Down() method runs on current migration

**Use case:** Undo last migration to test changes

### Roll Back to Specific Migration

**Command:** `"roll back to migration <name>"`

**What happens:**
1. Discover connection
2. Execute: `dotnet ef database update <migration-name>`
3. Down() methods run for all migrations after target

**Use case:** Return to known state, undo multiple migrations

**Example:** `"roll back to migration InitialCreate"`

### Roll Forward (Apply All)

**Command:** `"apply all orca migrations"`

**What happens:**
1. Discover connection
2. Execute: `dotnet ef database update` (no target = latest)
3. Up() methods run for all pending migrations

**Use case:** Apply all migrations, restore to latest

## EF Core Command Details

### Base Command Structure

```bash
cd /d/dev/actions.api && dotnet ef database update <target> \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build \
  --connection "<connection-string>"
```

**Parameters:**
- `<target>` - Migration name or omit for latest
- `--project` - Project with DbContext
- `--context` - Which DbContext to use
- `--no-build` - Use existing binaries (faster)
- `--connection` - Connection string from discovery

### Migration History

**List migrations:**
```bash
dotnet ef migrations list \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build
```

**Output format:**
```
20231015120000_InitialCreate (Applied)
20231016140000_AddUserTable (Applied)
20231017160000_AddWorkflowTable (Pending)
```

### Rollback Mechanics

**Current migration:** `AddWorkflowTable`

**Roll back one:**
```bash
dotnet ef database update AddUserTable
```

**Result:** `AddWorkflowTable.Down()` executes

**Roll back to initial:**
```bash
dotnet ef database update InitialCreate
```

**Result:** Both `Down()` methods execute in reverse order

## Prerequisites

- Orca can be running or stopped (works either way)
- actions.api project must be built
- SQL Server container running
- Database accessible

## Cache Management

### Cache Hit (Fast Path)

**Conditions:** Cache exists and connection test passes

**Time:** <100ms (no discovery needed)

**Process:**
1. Read cache file
2. Test connection: `SELECT 1`
3. If success, use cached values

### Cache Miss (Discovery Path)

**Triggers:**
- No cache file exists (first run)
- Cached container doesn't exist
- Cached password wrong
- Cached database unavailable

**Time:** 2-5 seconds (Docker queries)

**Process:**
1. Find SQL container
2. Extract credentials
3. Discover database
4. Update cache

### Force Rediscovery

**Command:** `"rediscover orca database connection"`

**Effect:** Ignores cache, runs full discovery

**Use case:** After Orca restart or container recreation

## Common Scenarios

### Scenario 1: Testing New Migration

```
1. Create migration: dotnet ef migrations add NewFeature
2. Build actions.api
3. Apply migration: "apply all orca migrations"
4. Test feature
5. If issues: "roll back orca migration"
6. Fix migration code
7. Recreate migration
8. Apply again
```

### Scenario 2: Debugging Migration Rollback

```
1. Apply migration: "apply all orca migrations"
2. Verify Up() worked correctly
3. Roll back: "roll back orca migration"
4. Verify Down() cleaned up correctly
5. Roll forward: "apply all orca migrations"
6. Verify idempotence
```

### Scenario 3: Return to Baseline

```
1. Multiple test migrations applied
2. Want clean slate
3. "roll back to migration InitialCreate"
4. All test migrations undone
5. Database at known state
```

## Error Handling

**"No SQL container found"**
- Docker Desktop not running
- SQL container not started
- Port 1433 not exposed

**"Login failed for user 'sa'"**
- Wrong password in cache
- Delete cache and retry

**"Cannot open database"**
- Database name changed
- Database deleted
- Delete cache and retry

**"Migration not found"**
- Wrong migration name
- Migration removed from code
- Check: `dotnet ef migrations list`

## Performance

**With cache hit:** <5 seconds total
- Connection: <100ms (cached)
- EF command: 2-4 seconds

**With cache miss:** 10-15 seconds total
- Discovery: 2-5 seconds
- EF command: 2-4 seconds
- Cache update: <100ms

**Subsequent runs:** Fast (cache hit)

## Related Skills

- [Backup Orca Database](../../skills/backup-orca-db/AGENT.md) - Backup before risky migrations
- [Restore Orca Database](../../skills/restore-orca-db/AGENT.md) - Restore if migration breaks
- [Orca](../../skills/orca/AGENT.md) - Launch Orca after migrations

## Reference Documentation

- [Connection Discovery](./reference/connection-discovery.md) - Discovery process details
- [Migration Commands](./reference/migration-commands.md) - All EF Core commands
- [Troubleshooting](./reference/troubleshooting.md) - Common issues

## Scripts

- `Discover-OrcaConnection.ps1` - Connection discovery and caching

---

**Version:** 2.0.0
**Last Updated:** 2025-11-03
