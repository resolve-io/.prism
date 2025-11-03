# Migration Commands - Entity Framework Core

This document details all Entity Framework Core migration commands used by the orca-migration-manager agent.

## Command Structure

### Base Command Template

```bash
cd /d/dev/actions.api && dotnet ef database update <target> \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build \
  --connection "<connection-string>"
```

**Parameters:**
- `<target>` - Migration name to apply (or omit for latest)
- `--project` - Project containing DbContext
- `--context` - Which DbContext to use
- `--no-build` - Skip build (use existing binaries)
- `--connection` - Connection string from discovery

### Why actions.api?

**Migration Location:** Entity Framework migrations are stored in the actions.api project

**DbContext:** `TenantDbContext` manages tenant database schema

**Project Structure:**
```
actions.api/
├── src/
│   ├── actions.api.csproj
│   ├── Data/
│   │   └── TenantDbContext.cs
│   └── Migrations/
│       ├── 20231015120000_InitialCreate.cs
│       ├── 20231016140000_AddUserTable.cs
│       └── ...
```

---

## Migration Listing

### Command: List All Migrations

```bash
cd /d/dev/actions.api && dotnet ef migrations list \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build
```

**Output Format:**
```
20231015120000_InitialCreate (Applied)
20231016140000_AddUserTable (Applied)
20231017160000_AddWorkflowTable (Pending)
20231018180000_AddSchedulerTable (Pending)
```

**Status Indicators:**
- `(Applied)` - Migration already applied to database
- `(Pending)` - Migration exists in code but not in database

**Parsing Logic:**
```powershell
$output = dotnet ef migrations list --project ... --no-build
$appliedMigrations = $output | Where-Object { $_ -like "*(Applied)" }
$pendingMigrations = $output | Where-Object { $_ -like "*(Pending)" }
```

### Migration Name Format

**Pattern:** `<timestamp>_<description>`

**Example:** `20231015120000_InitialCreate`

**Parts:**
- `20231015120000` - Timestamp (YYYYMMDDHHmmss)
- `_` - Separator
- `InitialCreate` - Human-readable description

**Why Timestamps?**
- Ensures chronological order
- Prevents naming conflicts
- Tracks creation time

---

## Rolling Back Migrations

### Rollback One Migration

**User Request:** `"roll back orca migration"`

**Process:**

1. **Get Current Migration:**
   ```powershell
   $migrations = dotnet ef migrations list --project ... --no-build
   $appliedMigrations = $migrations | Where-Object { $_ -like "*(Applied)" }
   $currentMigration = $appliedMigrations[-1]  # Last applied
   ```

2. **Get Previous Migration:**
   ```powershell
   $previousMigration = $appliedMigrations[-2]  # Second-to-last
   $previousName = $previousMigration -replace ' \(Applied\)', ''
   ```

3. **Execute Rollback:**
   ```bash
   cd /d/dev/actions.api && dotnet ef database update $previousName \
     --project src/actions.api.csproj \
     --context TenantDbContext \
     --no-build \
     --connection "$connectionString"
   ```

**What Happens:**
- Current migration's `Down()` method executes
- Schema changes reversed
- Migration marked as pending
- Database returns to previous state

**Example:**

**Before:**
```
InitialCreate (Applied)
AddUserTable (Applied)      <- Current
AddWorkflowTable (Pending)
```

**Command:** Roll back one migration

**After:**
```
InitialCreate (Applied)      <- Rolled back to this
AddUserTable (Pending)       <- Now pending
AddWorkflowTable (Pending)
```

### Rollback to Specific Migration

**User Request:** `"roll back to migration InitialCreate"`

**Process:**

1. **Validate Migration Exists:**
   ```powershell
   $migrations = dotnet ef migrations list --project ... --no-build
   $targetExists = $migrations | Where-Object { $_ -like "*InitialCreate*" }
   if (!$targetExists) {
       throw "Migration 'InitialCreate' not found"
   }
   ```

2. **Execute Rollback:**
   ```bash
   cd /d/dev/actions.api && dotnet ef database update InitialCreate \
     --project src/actions.api.csproj \
     --context TenantDbContext \
     --no-build \
     --connection "$connectionString"
   ```

**What Happens:**
- All migrations after target's `Down()` methods execute **in reverse order**
- Schema changes reversed for each
- Migrations marked as pending
- Database returns to target state

**Example:**

**Before:**
```
InitialCreate (Applied)
AddUserTable (Applied)
AddWorkflowTable (Applied)
AddSchedulerTable (Applied)  <- Current
```

**Command:** Roll back to `AddUserTable`

**After:**
```
InitialCreate (Applied)
AddUserTable (Applied)       <- Rolled back to this
AddWorkflowTable (Pending)   <- Rolled back
AddSchedulerTable (Pending)  <- Rolled back
```

**Down() Execution Order:**
1. `AddSchedulerTable.Down()` (most recent first)
2. `AddWorkflowTable.Down()` (next)
3. Stop at `AddUserTable` (target reached)

### Special Case: Rollback to 0 (Empty Database)

**Command:** `"roll back to migration 0"` or `"roll back all migrations"`

**Process:**
```bash
cd /d/dev/actions.api && dotnet ef database update 0 \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build \
  --connection "$connectionString"
```

**What Happens:**
- ALL migrations' `Down()` methods execute in reverse order
- Database schema completely removed
- Only `__EFMigrationsHistory` table remains (empty)
- Useful for testing initial migration or complete reset

---

## Rolling Forward Migrations

### Apply All Pending Migrations

**User Request:** `"apply all orca migrations"` or `"roll forward"`

**Process:**

1. **Check for Pending:**
   ```powershell
   $migrations = dotnet ef migrations list --project ... --no-build
   $pendingMigrations = $migrations | Where-Object { $_ -like "*(Pending)" }
   if ($pendingMigrations.Count -eq 0) {
       Write-Host "No pending migrations"
       return
   }
   ```

2. **Execute Update:**
   ```bash
   cd /d/dev/actions.api && dotnet ef database update \
     --project src/actions.api.csproj \
     --context TenantDbContext \
     --no-build \
     --connection "$connectionString"
   ```

**What Happens:**
- All pending migrations' `Up()` methods execute **in chronological order**
- Schema changes applied for each
- Migrations marked as applied
- Database brought to latest state

**Example:**

**Before:**
```
InitialCreate (Applied)
AddUserTable (Applied)
AddWorkflowTable (Pending)   <- Will apply
AddSchedulerTable (Pending)  <- Will apply
```

**Command:** Apply all migrations

**After:**
```
InitialCreate (Applied)
AddUserTable (Applied)
AddWorkflowTable (Applied)   <- Applied
AddSchedulerTable (Applied)  <- Applied
```

**Up() Execution Order:**
1. `AddWorkflowTable.Up()` (oldest pending first)
2. `AddSchedulerTable.Up()` (next)

### Apply Specific Migration (Jump Forward)

**Rare Use Case:** Jump forward to specific migration (skipping others)

**Command:**
```bash
cd /d/dev/actions.api && dotnet ef database update AddSchedulerTable \
  --project src/actions.api.csproj \
  --context TenantDbContext \
  --no-build \
  --connection "$connectionString"
```

**What Happens:**
- All migrations up to and including target execute
- Cannot skip migrations (dependencies)

**Example:**

**Before:**
```
InitialCreate (Pending)
AddUserTable (Pending)
AddWorkflowTable (Pending)
AddSchedulerTable (Pending)
```

**Command:** Update to `AddWorkflowTable`

**After:**
```
InitialCreate (Applied)      <- Applied (dependency)
AddUserTable (Applied)       <- Applied (dependency)
AddWorkflowTable (Applied)   <- Applied (target)
AddSchedulerTable (Pending)  <- Skipped (after target)
```

---

## Migration History Table

### __EFMigrationsHistory

**Location:** Target database (e.g., RDTest)

**Structure:**
```sql
CREATE TABLE [__EFMigrationsHistory] (
    [MigrationId] nvarchar(150) NOT NULL PRIMARY KEY,
    [ProductVersion] nvarchar(32) NOT NULL
);
```

**Example Data:**
```
MigrationId                           | ProductVersion
--------------------------------------|----------------
20231015120000_InitialCreate          | 9.0.0
20231016140000_AddUserTable           | 9.0.0
20231017160000_AddWorkflowTable       | 9.0.0
```

**Purpose:**
- Tracks applied migrations
- Prevents duplicate application
- Determines what to apply/rollback

**Querying:**
```sql
SELECT MigrationId FROM [__EFMigrationsHistory] ORDER BY MigrationId;
```

**Manual Manipulation (DANGEROUS):**
- Can manually insert/delete rows to force migration state
- **NOT RECOMMENDED** - Can cause schema/history mismatch
- Use only for recovery scenarios

---

## Migration File Structure

### Migration Class

```csharp
public partial class AddUserTable : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "Users",
            columns: table => new
            {
                Id = table.Column<int>(nullable: false)
                    .Annotation("SqlServer:Identity", "1, 1"),
                Username = table.Column<string>(maxLength: 100, nullable: false),
                Email = table.Column<string>(maxLength: 255, nullable: false),
                CreatedAt = table.Column<DateTime>(nullable: false)
            },
            constraints: table =>
            {
                table.PrimaryKey("PK_Users", x => x.Id);
            });
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropTable(name: "Users");
    }
}
```

**Up() Method:**
- Applied when rolling forward
- Creates/modifies schema
- Adds tables, columns, indexes, etc.

**Down() Method:**
- Applied when rolling back
- Reverses Up() changes
- Drops tables, removes columns, etc.

**Important:** Down() must perfectly reverse Up() for idempotent migrations

---

## Common Scenarios

### Scenario 1: Test New Migration

**Steps:**
```
1. Create migration:
   dotnet ef migrations add NewFeature --project src/actions.api.csproj --context TenantDbContext

2. Build actions.api:
   dotnet build actions.api.sln

3. Apply migration:
   "apply all orca migrations"

4. Test feature in Orca

5. If issues, rollback:
   "roll back orca migration"

6. Fix migration code

7. Remove migration:
   dotnet ef migrations remove --project src/actions.api.csproj --context TenantDbContext

8. Recreate migration (repeat from step 1)
```

### Scenario 2: Verify Down() Works

**Steps:**
```
1. Apply migration:
   "apply all orca migrations"

2. Verify schema changes:
   Check database in SSMS/Azure Data Studio

3. Roll back:
   "roll back orca migration"

4. Verify rollback:
   Confirm tables/columns removed

5. Roll forward:
   "apply all orca migrations"

6. Verify reapplication:
   Confirm idempotence (same result as step 2)
```

### Scenario 3: Return to Baseline

**Steps:**
```
1. Check current state:
   "list orca migrations"

2. Roll back to baseline:
   "roll back to migration InitialCreate"

3. Verify clean state:
   Check database schema

4. Delete test migrations (if needed):
   dotnet ef migrations remove --project src/actions.api.csproj

5. Rebuild from baseline:
   "apply all orca migrations"
```

---

## Error Handling

### "Migration <name> not found"

**Cause:** Migration doesn't exist in code

**Solutions:**
1. Check migration list: `dotnet ef migrations list`
2. Verify spelling of migration name
3. Ensure project built: `dotnet build actions.api.sln`

### "Unable to connect to database"

**Cause:** Connection string invalid or database unreachable

**Solutions:**
1. Check connection cache: `$env:USERPROFILE\.claude-orca\connection-cache`
2. Test connection manually: `docker exec <container> /opt/mssql-tools18/bin/sqlcmd ...`
3. Rediscover connection: `"rediscover orca database connection"`

### "Foreign key constraint violation"

**Cause:** Down() method trying to drop table with foreign key references

**Solutions:**
1. Check migration order (dependencies)
2. Fix Down() method to drop constraints first
3. Manually remove constraints before rollback (last resort)

### "Column <name> does not exist"

**Cause:** Schema out of sync with migration history

**Solutions:**
1. Check __EFMigrationsHistory table
2. Manually apply missing migrations
3. Restore database from backup (nuclear option)

---

## Performance Considerations

### Migration Speed

**Fast migrations (~1-5 seconds):**
- Add column
- Add index
- Add table (small)

**Slow migrations (~10-60 seconds):**
- Add column with default value to large table
- Create index on large table
- Data migration (transforming rows)

### Build Requirement

**--no-build flag:**
- Assumes actions.api already built
- Faster execution (skips compilation)
- **Prerequisite:** Run `dotnet build actions.api.sln` first

**Without --no-build:**
- Rebuilds actions.api every time
- Slower (adds 20-40 seconds)
- Safe but unnecessary if no code changes

---

## Migration Workflow Integration

### Orca must be running or stopped?

**Either works:**
- Orca running → Migrations applied while app running (hot update)
- Orca stopped → Migrations applied before launch

**Best practice:**
- Stop Orca if schema changes are breaking
- Keep running if additive changes only (new columns, tables)

### Build actions.api first?

**Yes, always:**
```
1. Make code changes
2. Build actions.api: dotnet build actions.api.sln
3. Apply migrations: "apply all orca migrations"
```

**Why?**
- Migration files compiled into DLL
- `--no-build` flag requires existing binaries
- Avoids redundant builds

---

## Related Documentation

- [Connection Discovery](./connection-discovery.md) - How connection string is obtained
- [Troubleshooting](./troubleshooting.md) - Common migration issues

---

**Last Updated:** 2025-11-03
