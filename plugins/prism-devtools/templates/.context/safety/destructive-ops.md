# Critical Lessons Learned - File Deletion Incident

**Date:** 2025-10-21
**Severity:** CRITICAL
**Impact:** All repositories in D:\dev\ deleted (successfully recovered)

---

## Incident Summary

A malformed PowerShell command intended to clean IIS Express temp files accidentally deleted all repositories from D:\dev\ due to bash escaping issues and insufficient validation.

### What Happened

**Command Executed:**
```bash
powershell.exe -NoProfile -Command "\$iisExpressPath = \"\$env:USERPROFILE\\Documents\\IISExpress\"; if (Test-Path \$iisExpressPath) { Get-ChildItem \$iisExpressPath -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Write-Host 'All IIS Express temp files cleared' } else { Write-Host 'IIS Express directory not found' }"
```

**Root Cause:**
1. Bash → PowerShell escaping failed: `\$iisExpressPath` didn't set variable
2. PowerShell interpreted path as `\` (backslash only)
3. Defaulted to current drive root: `D:\`
4. `Remove-Item -Recurse -Force` deleted everything accessible on D:\
5. `-ErrorAction SilentlyContinue` masked the path error

**Deleted:**
- 16 repositories from D:\dev\
- .claude junction (skills preserved due to junction nature)

**Preserved:**
- express-web-client (survived)
- resolve.dev.resources (survived)
- Documents\Claude folder (protected by junction)

**Recovery:**
- All repositories re-cloned from resolve-io organization on GitHub
- .claude junction recreated
- Claude folder migrated to OneDrive for backup

---

## MANDATORY RULES FOR DESTRUCTIVE FILE OPERATIONS

### Rule 1: ALWAYS Write PowerShell Scripts to Files
**NEVER use inline PowerShell commands with complex escaping for file operations.**

```bash
# ✅ CORRECT: Write to file first
cat > /tmp/cleanup.ps1 <<'EOF'
$iisExpressPath = "$env:USERPROFILE\Documents\IISExpress"
if (Test-Path $iisExpressPath) {
    Get-ChildItem $iisExpressPath -Recurse -Force | Remove-Item -Recurse -Force
}
EOF
powershell.exe -ExecutionPolicy Bypass -File /tmp/cleanup.ps1

# ❌ WRONG: Inline with escaping
powershell.exe -Command "\$var = \"value\"; Remove-Item..."
```

### Rule 2: ALWAYS Validate Paths Before Deletion
**Validate the resolved path matches expected patterns.**

```powershell
$targetPath = "$env:USERPROFILE\Documents\IISExpress"

# Resolve and validate
if (Test-Path $targetPath) {
    $resolvedPath = (Resolve-Path $targetPath).Path

    # Multi-factor validation
    if ($resolvedPath.Length -lt 10) {
        Write-Error "Path too short - refusing for safety: $resolvedPath"
        exit 1
    }

    if ($resolvedPath -match '^[A-Z]:\\$') {
        Write-Error "Cannot delete drive root: $resolvedPath"
        exit 1
    }

    if ($resolvedPath -notlike "*\Documents\IISExpress*") {
        Write-Error "Path validation failed - unexpected location: $resolvedPath"
        exit 1
    }

    # Safe to proceed
    Write-Host "Validated path: $resolvedPath"
    Remove-Item $resolvedPath -Recurse -Force
}
```

### Rule 3: NEVER Use -ErrorAction SilentlyContinue with Destructive Operations
**Errors during deletion must be visible and must stop execution.**

```powershell
# ❌ WRONG: Hides critical errors
Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue

# ✅ CORRECT: Let errors stop execution
Remove-Item $path -Recurse -Force

# ✅ ALSO ACCEPTABLE: Log errors but still show them
Remove-Item $path -Recurse -Force -ErrorAction Stop
```

### Rule 4: ALWAYS Use -WhatIf First
**Test destructive operations before executing.**

```powershell
# Step 1: Preview what will be deleted
Remove-Item $path -Recurse -Force -WhatIf

# Step 2: Show user and get confirmation
Write-Host "The above files will be deleted. Press Ctrl+C to cancel..."
Start-Sleep -Seconds 3

# Step 3: Execute only after preview
Remove-Item $path -Recurse -Force
```

### Rule 5: Prefer Desktop Commander Tools
**Use MCP tools with built-in safety for file operations.**

```bash
# ✅ PREFERRED: Use Desktop Commander
mcp__desktop-commander__list_directory
mcp__desktop-commander__read_file
mcp__desktop-commander__write_file

# ⚠️ USE WITH EXTREME CAUTION: Direct shell commands
Bash tool with rm, Remove-Item, del
```

### Rule 6: Add Guardrails for Path Length and Patterns
**Refuse to delete suspiciously short or dangerous paths.**

```powershell
# Check path length (drive roots are 3 chars: "C:\")
if ($path.Length -lt 10) {
    Write-Error "Path suspiciously short: '$path' (length: $($path.Length))"
    exit 1
}

# Check for drive root patterns
if ($path -match '^[A-Z]:\\$') {
    Write-Error "Refusing to delete drive root: $path"
    exit 1
}

# Check for single character paths (like "\")
if ($path -eq '\' -or $path -eq '/') {
    Write-Error "Refusing to delete root path: $path"
    exit 1
}
```

---

## Pre-Execution Checklist for Destructive Operations

Before executing any command that deletes, moves, or modifies files in bulk:

- [ ] **Is this a PowerShell command?** → Write to file, don't use inline
- [ ] **Does it use Remove-Item, rm, del, or similar?** → Add path validation
- [ ] **Is path validation implemented?** → Check length, pattern, resolved path
- [ ] **Does it use -ErrorAction SilentlyContinue?** → Remove it
- [ ] **Can I use -WhatIf first?** → Always test before executing
- [ ] **Is there a safer alternative?** → Prefer Desktop Commander tools
- [ ] **Have I shown the user the exact script?** → Get implicit approval
- [ ] **Are there guardrails for root paths?** → Add length/pattern checks

**If ANY checkbox is unchecked, DO NOT PROCEED with the operation.**

---

## Evidence from This Incident

**Shell ID:** da7f02
**Command stderr showed:**
```
\ : The term '\' is not recognized...
Get-ChildItem : Access to the path 'D:\$RECYCLE.BIN\S-1-5-18' is denied.
Get-ChildItem : Access to the path 'D:\System Volume Information' is denied.
```

**This clearly indicated:**
- Path resolved to `\` (backslash only)
- Command was operating on `D:\` drive root
- Should have been caught by validation before deletion occurred

---

## Conclusion

**This incident was 100% preventable.** The six rules above would have stopped this error at multiple points:
1. Writing to a file would have avoided escaping issues
2. Path validation would have rejected `\` as invalid
3. Removing SilentlyContinue would have shown the error immediately
4. -WhatIf would have revealed the wrong path before deletion
5. Desktop Commander tools have built-in safety
6. Guardrails would have rejected the single-character path

**These rules are MANDATORY for all future destructive file operations.**

---

**Document Created:** 2025-10-21
**Last Updated:** 2025-10-21
**Status:** ACTIVE - Review before ANY destructive file operation
