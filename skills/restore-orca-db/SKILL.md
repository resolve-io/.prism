---
name: restore-orca-db
description: Restore Orca SQL database from backup in user profile cache
version: 2.0.0
---

# Orca Database Restore Skill

## Quick Reference

**Restore most recent backup:** `"restore orca database"`
**Restore specific backup:** `"restore orca database from migration-test"`

## What This Skill Does

Restores the Orca SQL Server database from a backup file:
- Discovers Orca SQL volume dynamically (no hard-coded names)
- Finds most recent backup or restores specific named backup
- Safely stops and removes containers using the volume
- Clears volume and imports backup data
- Verifies restoration success

## How It Works

1. Find Orca SQL volume → Dynamic discovery
2. Locate backup file → Most recent or specific name
3. Stop containers using volume → Graceful shutdown
4. Clear existing volume data → Prevent conflicts
5. Import backup → Extract tar.gz into volume
6. Verify restoration → Check file count
7. Ready to launch Orca → Use `orca` skill

## Backup Location

**Restores from:** `$env:USERPROFILE\.claude-orca\backups\`

**Backup naming:**
- **Timestamped:** `orca-db-2025-10-31-14-30.tar.gz` (most recent selected)
- **Custom:** `orca-db-{custom-name}.tar.gz` (must specify name)

## Use Cases

- **After database corruption** - Restore known good state
- **Testing migrations** - Restore baseline, test, repeat
- **Development resets** - Return to clean state
- **Before risky changes** - Restore if things go wrong
- **Environment setup** - Restore production snapshot

## Common Commands

```bash
# Restore from most recent backup
"restore orca database"

# Restore from specific backup
"restore orca database from before-migration-123"

# Restore without confirmation prompt
"restore orca database" (with -SkipConfirmation)
```

## Safety Features

- **Volume name validation** - Checks pattern and length
- **Container management** - Gracefully stops SQL containers
- **Data protection** - 3-second countdown before restore
- **Verification** - Confirms files restored successfully
- **Clear warnings** - Shows what will be deleted

## Environment Requirements

- Docker Desktop running
- Docker CLI available
- Backup files in user profile cache
- No running Orca instance (will be stopped automatically)

## Example Output

```
Orca Database Restore Tool
==========================

Finding Orca SQL volume...
  [OK] Found volume: orca.apphost-cc67ab6e00-sql-data

Finding backup file...
  [OK] Found backup: orca-db-2025-10-31-14-30.tar.gz
    Date: 10/31/2025 2:30:45 PM
    Size: 145.23 MB

Checking for running containers...
  Stopping container: sql-cc67ab6e00 (abc123)
  Removing container: sql-cc67ab6e00
  [OK] All containers stopped and removed

WARNING: This will DELETE all data in volume: orca.apphost-cc67ab6e00-sql-data
WARNING: And restore from backup: orca-db-2025-10-31-14-30.tar.gz

Press Ctrl+C to cancel, or wait 3 seconds to continue...

Clearing existing volume data...
  [OK] Volume cleared

Importing backup...
  [OK] Backup imported

Verifying restore...
  [OK] Restored 15 files/directories

[SUCCESS] Database restore complete!

To use the restored database, launch Orca using the 'orca' skill.
```

## Troubleshooting

**"No timestamped backups found"**
- Check: Do backups exist? Run `ls $env:USERPROFILE\.claude-orca\backups\`
- Use custom backup name if only named backups exist

**"Backup file not found"**
- Check backup name spelling
- List available backups in cache directory

**"Failed to clear volume"**
- Check: Is Docker Desktop running?
- Check: Are containers still running?

**"Failed to import backup"**
- Check: Is backup file corrupted?
- Check: Enough disk space?

See: [Troubleshooting Guide](./reference/troubleshooting.md)

## Related Skills

- [Backup Orca Database](../backup-orca-db/SKILL.md) - Create backups before changes
- [Orca](../orca/SKILL.md) - Launch Orca after restore

## Reference Documentation

- [Restore Workflow Details](./reference/restore-workflow.md) - Step-by-step process
- [Troubleshooting](./reference/troubleshooting.md) - Common issues and solutions

## Scripts

- `Restore-DockerVolume.ps1` - Main restore logic

---

**Version:** 2.0.0
**Last Updated:** 2025-11-03
