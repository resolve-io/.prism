# Backup Naming Conventions

This document describes the naming patterns for Orca database backups.

## Overview

Backups use consistent naming to enable:
- Easy identification
- Chronological sorting
- Automated cleanup
- Milestone tracking

## Naming Patterns

### Timestamped Backups (Default)

**Pattern:** `orca-db-{YYYY-MM-DD-HH-mm}.tar.gz`

**Examples:**
```
orca-db-2025-10-31-14-30.tar.gz
orca-db-2025-11-01-09-15.tar.gz
orca-db-2025-11-02-16-45.tar.gz
```

**Components:**
- `orca-db-` - Prefix (identifies Orca database backups)
- `{YYYY-MM-DD-HH-mm}` - Timestamp in ISO 8601-like format
  - `YYYY` - 4-digit year (2025)
  - `MM` - 2-digit month (01-12)
  - `DD` - 2-digit day (01-31)
  - `HH` - 2-digit hour (00-23, 24-hour format)
  - `mm` - 2-digit minute (00-59)
- `.tar.gz` - Archive format (gzip-compressed tar)

**Benefits:**
- **Sortable:** Alphabetical sort = chronological sort
- **Unique:** No collisions (same minute unlikely)
- **Readable:** Easy to identify when backup was created
- **Parseable:** Easy to extract date/time programmatically

**Use Cases:**
- Regular automated backups
- Development snapshots
- Quick backups before changes

### Custom Named Backups

**Pattern:** `orca-db-{custom-name}.tar.gz`

**Examples:**
```
orca-db-migration-test.tar.gz
orca-db-before-plat-1234.tar.gz
orca-db-release-v2.0-gold.tar.gz
orca-db-pre-schema-change.tar.gz
```

**Constraints:**
- **Sanitized:** Invalid characters replaced with `-`
- **Windows-safe:** No `\ / : * ? " < > |` characters
- **Case-preserved:** `MigrationTest` remains `MigrationTest`
- **Length:** Practical limit ~100 characters

**Sanitization Examples:**
```
Input:  "my:test:backup"
Output: "orca-db-my-test-backup.tar.gz"

Input:  "before/migration"
Output: "orca-db-before-migration.tar.gz"

Input:  "v2.0*final"
Output: "orca-db-v2.0-final.tar.gz"
```

**Benefits:**
- **Meaningful:** Describes purpose or milestone
- **Memorable:** Easier to recall than timestamps
- **Persistent:** Won't be auto-deleted (not timestamped)

**Use Cases:**
- Important milestones
- Named test scenarios
- Release checkpoints
- Specific feature branches

## Comparison: Timestamped vs Custom

| Aspect | Timestamped | Custom |
|--------|-------------|--------|
| **Uniqueness** | Automatic (timestamp) | Manual (user ensures) |
| **Sortability** | Chronological | Alphabetical |
| **Readability** | Date/time clear | Purpose clear |
| **Auto-cleanup** | Yes (by age/count) | No (kept indefinitely) |
| **Collision risk** | Very low | Moderate (manual) |
| **Use case** | Regular backups | Milestones |

## Filesystem Sorting

### Chronological View (Timestamped)

```
Directory of C:\Users\DanPuzon\.claude-orca\backups

2025-10-31  02:30 PM       145,234,567 orca-db-2025-10-31-14-30.tar.gz
2025-11-01  09:15 AM       147,123,456 orca-db-2025-11-01-09-15.tar.gz
2025-11-02  04:45 PM       148,987,654 orca-db-2025-11-02-16-45.tar.gz
```

Natural sorting order matches creation order.

### Mixed View (Timestamped + Custom)

```
Directory of C:\Users\DanPuzon\.claude-orca\backups

2025-10-31  02:30 PM       145,234,567 orca-db-2025-10-31-14-30.tar.gz
2025-11-01  09:15 AM       147,123,456 orca-db-2025-11-01-09-15.tar.gz
2025-10-30  03:00 PM       146,000,000 orca-db-before-migration-test.tar.gz
2025-10-29  05:30 PM       144,500,000 orca-db-release-v2.0-gold.tar.gz
```

Custom names sort alphabetically, not chronologically.

## Backup Selection Logic

### Most Recent Timestamped Backup

**Restore workflow default:**
```powershell
Get-ChildItem "$backupsDir" -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.Name -match "orca-db-\d{4}-\d{2}-\d{2}" } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
```

**Result:** Most recently created timestamped backup

### Specific Named Backup

**User specifies:**
```
"restore orca database from migration-test"
```

**Script looks for:**
```powershell
$backupPath = Join-Path $backupsDir "orca-db-migration-test.tar.gz"
if (Test-Path $backupPath) {
    # Use this backup
}
```

### All Backups (Chronological)

**For listing:**
```powershell
Get-ChildItem "$backupsDir" -Filter "orca-db-*.tar.gz" |
    Sort-Object LastWriteTime -Descending
```

**Output:**
```
orca-db-2025-11-02-16-45.tar.gz (latest)
orca-db-2025-11-01-09-15.tar.gz
orca-db-2025-10-31-14-30.tar.gz
orca-db-before-migration-test.tar.gz (custom)
```

## Naming Best Practices

### For Timestamped Backups

**Do:**
- Let the system generate automatically
- Trust the timestamp format
- Use for regular backups

**Don't:**
- Manually create timestamped names
- Rename timestamped backups
- Mix timestamp formats

### For Custom Named Backups

**Do:**
- Use descriptive, specific names
- Include ticket numbers: `before-plat-1234`
- Include version numbers: `release-v2.0`
- Use consistent naming patterns

**Don't:**
- Use generic names: `backup1`, `test`
- Use spaces (converted to `-` anyway)
- Use special characters (sanitized)
- Make names too long (>50 chars recommended)

### Naming Patterns for Teams

**Ticket-based:**
```
orca-db-before-plat-1234.tar.gz
orca-db-after-plat-1234.tar.gz
orca-db-plat-1234-test1.tar.gz
```

**Feature-based:**
```
orca-db-pre-auth-refactor.tar.gz
orca-db-post-auth-refactor.tar.gz
orca-db-auth-refactor-v1.tar.gz
```

**Release-based:**
```
orca-db-release-v2.0-rc1.tar.gz
orca-db-release-v2.0-rc2.tar.gz
orca-db-release-v2.0-gold.tar.gz
```

**Environment-based:**
```
orca-db-dev-snapshot.tar.gz
orca-db-staging-baseline.tar.gz
orca-db-prod-mirror.tar.gz
```

## Programmatic Parsing

### Extract Timestamp from Filename

```powershell
$filename = "orca-db-2025-10-31-14-30.tar.gz"

# Regex pattern
$pattern = "orca-db-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.tar\.gz"

if ($filename -match $pattern) {
    $year = $matches[1]    # 2025
    $month = $matches[2]   # 10
    $day = $matches[3]     # 31
    $hour = $matches[4]    # 14
    $minute = $matches[5]  # 30

    $datetime = Get-Date -Year $year -Month $month -Day $day -Hour $hour -Minute $minute
    Write-Host "Backup created: $datetime"
}
```

### Filter by Date Range

```powershell
# Get backups from last 7 days
$cutoff = (Get-Date).AddDays(-7)

Get-ChildItem "$backupsDir" -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.LastWriteTime -gt $cutoff }
```

### Group by Month

```powershell
Get-ChildItem "$backupsDir" -Filter "orca-db-*.tar.gz" |
    Where-Object { $_.Name -match "orca-db-\d{4}-\d{2}" } |
    Group-Object { $_.Name.Substring(8, 7) } # "2025-10"
```

## Collision Handling

### Timestamped Collisions

**Unlikely:** Same minute = collision
**Probability:** Low (requires two backups in same minute)

**If collision occurs:**
```powershell
if (Test-Path $backupPath) {
    Write-Host "⚠ Warning: Backup file already exists"
    $overwrite = Read-Host "Overwrite? (y/n)"
    if ($overwrite -ne 'y') {
        # Cancel backup
        return
    }
}
```

**Future enhancement:** Add seconds to timestamp
```
orca-db-2025-10-31-14-30-45.tar.gz (includes seconds)
```

### Custom Name Collisions

**Likely:** Users may reuse names
**Example:** Multiple `test` backups

**Handling:**
```powershell
if (Test-Path $backupPath) {
    # Prompt user
    $overwrite = Read-Host "Backup 'test' already exists. Overwrite? (y/n)"

    if ($overwrite -eq 'y') {
        Remove-Item $backupPath -Force
        # Proceed with backup
    } else {
        # Suggest alternative name
        Write-Host "Suggestion: Use 'test-v2' or 'test-$(Get-Date -Format 'HH-mm')'"
        # Cancel backup
    }
}
```

## Special Characters Reference

### Invalid Windows Filename Characters

**Not allowed in filenames:**
```
\  Backslash
/  Forward slash
:  Colon
*  Asterisk
?  Question mark
"  Double quote
<  Less than
>  Greater than
|  Pipe
```

**Sanitization rule:** Replace with `-` (hyphen)

### Valid Characters

**Allowed:**
- Letters: `A-Z a-z`
- Numbers: `0-9`
- Hyphen: `-`
- Underscore: `_`
- Period: `.` (but only before `.tar.gz`)
- Space: (converted to `-` for consistency)

## Configuration

### Default Naming (config.json)

```json
{
  "defaultNamingPattern": "timestamp",
  "timestampFormat": "yyyy-MM-dd-HH-mm",
  "customNameSanitization": true,
  "maxCustomNameLength": 100
}
```

**Not currently implemented** - future enhancement

## Related Documentation

- [Backup Workflow](./backup-workflow.md) - Complete backup process
- [Cleanup Strategy](./cleanup-strategy.md) - How naming affects cleanup
- [Troubleshooting](./troubleshooting.md) - Name-related issues

---

**Last Updated:** 2025-10-31
