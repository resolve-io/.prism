---
name: backup-orca-db
description: Create ad-hoc backups of Orca SQL database volume to user profile cache
version: 2.0.0
---

# Orca Database Backup Skill

## Quick Reference

**Backup with timestamp:** `"backup orca database"`
**Backup with custom name:** `"backup orca database as migration-test"`

## What This Skill Does

Creates ad-hoc backups of the Orca SQL database volume:
- Discovers Orca SQL volume dynamically (no hard-coded names)
- Exports volume to compressed tar.gz archive
- Stores in user profile cache (survives dev root wipes)
- Automatic timestamped naming or custom milestone names
- Optional automatic cleanup of old backups
- Verifies backup integrity after creation

## How It Works

1. Find Orca SQL volume → [Backup Workflow](./reference/backup-workflow.md)
2. Generate backup filename → [Naming Convention](./reference/backup-naming.md)
3. Export volume to tar.gz (read-only mount)
4. Store in cache: `$env:USERPROFILE\.claude-orca\backups\`
5. Verify backup integrity
6. Report backup size and location
7. Optional: Cleanup old backups → [Cleanup Strategy](./reference/cleanup-strategy.md)

## Backup Location

**All backups stored in:** `$env:USERPROFILE\.claude-orca\backups\`

**Naming:**
- **Timestamped:** `orca-db-2025-10-31-14-30.tar.gz`
- **Custom:** `orca-db-{custom-name}.tar.gz`

**Why User Profile:**
- ✅ Survives dev root wipes (can delete entire `d:\dev`)
- ✅ Not on dev drive (separate code from state)
- ✅ Backed up by Windows user profile sync
- ✅ Portable across dev root locations

## Automatic Cleanup

By default, keeps:
- Last 10 backups (configurable)
- OR backups from last 30 days (configurable)

**Configure:** `$env:USERPROFILE\.claude-orca\config.json`

```json
{
  "maxBackupCount": 10,
  "backupRetentionDays": 30,
  "autoCleanupOldBackups": true
}
```

See: [Cleanup Strategy](./reference/cleanup-strategy.md)

## Use Cases

- **Before major migrations** - Capture current state
- **Before risky database changes** - Safety net
- **Daily development snapshots** - Regular checkpoints
- **Milestone captures** - Named backups for specific points
- **Testing workflows** - Create, test, restore cycle

## Common Commands

```bash
# Timestamped backup
"backup orca database"

# Named backup for milestone
"backup orca database as before-migration-123"

# Backup with auto-cleanup
"backup orca database" (with config.json autoCleanupOldBackups: true)
```

## Environment Requirements

- Docker Desktop running
- Docker CLI available
- Orca installed (volume exists)
- Write access to user profile

## Example Output

```
Orca Database Backup Tool
========================

Finding Orca SQL volume...
  ✓ Found volume: orca.apphost-cc67ab6e00-sql-data

Backup file: orca-db-2025-10-31-14-30.tar.gz
Destination: C:\Users\DanPuzon\.claude-orca\backups\

Exporting volume...
  ✓ Volume exported

✅ Backup complete!
  Path: C:\Users\DanPuzon\.claude-orca\backups\orca-db-2025-10-31-14-30.tar.gz
  Size: 145.23 MB
```

## Troubleshooting

**"Orca SQL volume not found"**
- Check: Is Orca installed? Run `docker volume ls`
- Check: Is Docker Desktop running?

**"Backup file already exists"**
- Prompted to overwrite
- Or use custom name to avoid conflicts

**"Export failed"**
- Check: Docker Desktop running
- Check: Disk space available
- See: [Troubleshooting Guide](./reference/troubleshooting.md)

## Related Skills

- [Restore Orca Database](../restore-orca-db/SKILL.md) - Restore from backups
- [Orca Migrations](../../agents/orca-migration-manager/AGENT.md) - Manage database migrations

## Reference Documentation

- [Backup Workflow Details](./reference/backup-workflow.md) - Step-by-step process
- [Naming Conventions](./reference/backup-naming.md) - Timestamp and custom naming
- [Cleanup Strategy](./reference/cleanup-strategy.md) - Automatic cleanup logic
- [Troubleshooting](./reference/troubleshooting.md) - Common issues and solutions

## Scripts

- `Get-CachePath.ps1` - Get user profile cache location
- `Find-OrcaVolume.ps1` - Discover Orca SQL volume
- `Backup-DockerVolume.ps1` - Export volume to tar.gz

---

**Version:** 2.0.0
**Last Updated:** 2025-10-31
