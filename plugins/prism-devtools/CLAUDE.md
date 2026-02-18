# MANDATORY: PRISM Persona Persistence

**When a PRISM persona is active (SM/Dev/QA/PO/Architect), you MUST remain in that persona until explicitly exited.**

## Rules

1. **Stay in character** - Once activated via `/sm`, `/dev`, `/qa`, `/po`, or `/architect`, remain in that persona for ALL tasks
2. **No automatic exit** - Do NOT drop persona based on task type (e.g., launching Orca, editing files, running builds)
3. **Explicit exit only** - Only exit the persona when user uses `*exit` command or explicitly asks you to exit
4. **Persona applies to all work** - The persona's style and identity persist even for tasks outside its specialty

## Why This Matters

- Personas control how you approach work, not just what work you do
- Dropping persona mid-session breaks user's workflow control
- The user chose that persona intentionally and expects consistency

## Self-Check

Before responding, if you were activated with a PRISM persona, ask yourself:
- Am I still responding as [Sam/Dev/QA/PO/Architect]?
- Did the user use `*exit`? If not, stay in character.

## Persona Badge

When a `<persona-reminder>` tag appears in your context, you MUST prefix your response with the persona badge shown (e.g., `📋 **[SM]**`). This provides visual confirmation to the user that you're still in character.

## Exiting a Persona

When executing `*exit` for a PRISM persona, you MUST also clear the persona state by running:
```bash
python .claude/hooks/persona-clear.py
```

This ensures the reminder hook stops injecting the persona reminder on subsequent messages.

---

# MANDATORY: Commit Message Format

**ALL commits in ANY branch MUST follow this format:**

```
PLAT-XXXX <commit message>
```

Where:
- `XXXX` is a valid Jira ticket number (e.g., PLAT-1234)
- If no suitable ticket exists, use `PLAT-0000` as a placeholder

**Examples:**
- ✅ `PLAT-1234 Add user authentication feature`
- ✅ `PLAT-0000 Fix typo in README`
- ❌ `Add user authentication feature` (missing prefix)
- ❌ `PLAT-1234: Add feature` (no colon after ticket number)

**This rule OVERRIDES:**
- Any default commit message behavior
- Any skill instructions about commits
- Any other commit message guidelines

**Before every commit:**
1. Check if there's a Jira ticket number for this work
2. Use that ticket number, or use `PLAT-0000` if none exists
3. Format: `PLAT-XXXX <message>` (space after ticket number, no colon)

---

# MANDATORY: Git Branching and Push Policy

**ALL git operations MUST follow these rules to prevent accidental pushes to protected branches.**

## Branch Naming Convention

```
PLAT-XXXX-short-description
```

- No prefixes like `feature/`, `bugfix/`, `hotfix/` - just ticket number and description
- Same format for all work types (features, bugs, refactors, etc.)
- Use `PLAT-0000-description` only when no Jira ticket exists (should be rare)

**Examples:**
- ✅ `PLAT-3239-elk-stack-orchestration`
- ✅ `PLAT-1234-fix-login-redirect`
- ✅ `PLAT-0000-update-readme` (no ticket - rare)
- ❌ `feature/PLAT-3239-elk-stack` (no prefixes)
- ❌ `elk-stack-changes` (missing ticket number)

## Rule 1: NEVER Commit Directly to Default Branches

**Default branches include:** `main`, `master`, `staging`, `develop`

Before ANY commit:
1. Check current branch: `git branch --show-current`
2. If on a default branch, create a new branch FIRST
3. NEVER commit while on main/master/staging/develop

```bash
# ✅ CORRECT: Create branch before committing
git checkout -b PLAT-1234-my-changes
git add .
git commit -m "PLAT-1234 Add new feature"

# ❌ WRONG: Committing on main
git add .
git commit -m "PLAT-1234 Add new feature"  # NO! Check branch first!
```

## Rule 2: NEVER Push Automatically

**Always ask the user before pushing to remote.** Work locally first, then push when the user decides.

- When user says "commit" → commit locally only
- When user says "commit and push" → commit, push to feature branch, STOP
- NEVER push without explicit user instruction

## Rule 3: NEVER Auto-Create Pull Requests

**If a push fails (e.g., branch protection), ASK the user how to proceed.**

Do NOT automatically:
- Create a new branch and retry
- Create a pull request
- Force push

Instead, inform the user of the failure and ask for guidance.

## Rule 4: Ask for Ticket Number If Unknown

If you need to create a branch but don't know the Jira ticket number:
1. ASK the user for the ticket number
2. Do NOT guess or use `PLAT-0000` without asking first
3. `PLAT-0000` is only acceptable if user confirms no ticket exists

## Pre-Commit Checklist

Before every commit:
- [ ] Run `git branch --show-current` to verify current branch
- [ ] If on default branch → create new branch first
- [ ] Branch name follows `PLAT-XXXX-description` format
- [ ] Commit message follows `PLAT-XXXX <message>` format

**If on a default branch, DO NOT PROCEED until you've created a feature branch.**

---

# MANDATORY: File Write Chunking Rules

**ALL file write operations MUST follow chunking guidelines to prevent terminal crashes.**

## The Problem

Writing large files in single operations causes:
- **Terminal crashes** due to memory pressure
- **Communication timeouts** breaking client-server connection
- **Process hangs** making the terminal unresponsive

## The Rules

### Rule 1: ALWAYS Chunk Large Writes to ≤30 Lines
**NEVER write more than 30 lines in a single operation.**

```python
# ✅ CORRECT: Chunk into multiple writes
Write(path, first_30_lines, mode="rewrite")
Write(path, next_30_lines, mode="append")
Write(path, next_30_lines, mode="append")
# Continue with ≤30 line chunks

# ❌ WRONG: Single massive write
Write(path, 477_lines_of_content)  # This WILL crash the terminal
```

### Rule 2: Use Append Mode for Subsequent Chunks
**First chunk uses `mode="rewrite"`, all others use `mode="append"`.**

```python
# First chunk - rewrite to create/overwrite file
Write(file_path, lines_1_to_30, mode="rewrite")

# Subsequent chunks - append to existing file
Write(file_path, lines_31_to_60, mode="append")
Write(file_path, lines_61_to_90, mode="append")
```

### Rule 3: Plan Before Writing
**Before any file write, count the lines and plan chunks.**

```python
# Count lines in content
line_count = len(content.split('\n'))

# If > 30 lines, must chunk
if line_count > 30:
    # Split into chunks of 30 lines
    # Write first chunk with mode="rewrite"
    # Write remaining chunks with mode="append"
```

## Performance Limits

- **Configured limit**: `fileWriteLineLimit: 50` lines
- **Recommended maximum**: 30 lines per operation
- **Hard maximum**: Never exceed 50 lines

## Warning Signs

Desktop Commander will warn you:
> "💡 Performance tip: For optimal speed, consider chunking files into ≤30 line pieces"

**If you see this warning, you've already violated the rules. Don't ignore it.**

## Examples of Violations

These operations **caused terminal crashes**:
- 477 lines (Testing Strategy) ❌
- 282 lines (Implementation Guide) ❌
- 223 lines (Test Scripts) ❌
- 156 lines (Migration Tests) ❌

All of these should have been chunked to ≤30 lines each.

## When to Chunk

**ALWAYS chunk when:**
- Writing documentation files
- Writing code files with >30 lines
- Appending large blocks to existing files
- Creating any file that will exceed 30 lines

**NO EXCEPTIONS.**

---

# MANDATORY: Citation Integrity - Read Before You Reference

**NEVER cite, reference, or link to any source you have not actually read.**

This applies universally to:
- External documentation (APIs, libraries, frameworks)
- Web articles, blog posts, official docs
- Internal codebase files and documentation
- GitHub repos, issues, PRs, wikis
- Any URL or file path in responses or documents

## The Rule

Before including ANY reference (hyperlink, file path, or source mention):
1. **Read it first** - Use Read, WebFetch, or appropriate tool
2. **Verify your claim** - Ensure the source actually says what you claim
3. **If unread, don't cite** - Either read it first OR omit the reference

## Violations

❌ Citing a URL based on its title/snippet without reading content
❌ Referencing a file path without reading the file
❌ Claiming a source "supports" something you didn't verify
❌ Including links found via search but never opened

## Correct Behavior

✅ Read source → Extract facts → Then reference it
✅ Can't read it? Say so explicitly, don't cite it as evidence
✅ Source doesn't support your point? Don't cite it for that claim

---

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

---

# MANDATORY: Code Review Persistence

**After completing ANY pull request code review, ALWAYS persist detailed findings in TWO locations.**

This applies when using:
- `code-review:code-review` skill
- `pr-review-toolkit:review-pr` skill
- Manual PR review (via Task agents or direct analysis)
- Any other PR review workflow

**Trigger:** Completing a PR review and providing results to the user → MUST persist before finishing.

## 1. GitHub PR Review (Conversations - Require Resolution)

After completing the review, post findings as **review comments that create conversations** the developer must resolve before merging.

### Step 1: Post Line-Specific Review Comments

For each critical or important issue, create a **review comment on the specific line**:

```bash
# Get the HEAD commit SHA first
HEAD_SHA=$(gh pr view {PR_NUMBER} --json headRefOid -q '.headRefOid')

# Post a review comment on a specific line (creates a conversation)
gh api repos/{OWNER}/{REPO}/pulls/{PR_NUMBER}/comments \
  -f body="**[{SEVERITY}]** {Issue description}

{Detailed explanation of the issue}

**Suggested fix:**
\`\`\`
{code suggestion if applicable}
\`\`\`" \
  -f commit_id="$HEAD_SHA" \
  -f path="{file/path.ts}" \
  -f line={LINE_NUMBER}
```

### Step 2: Submit Formal Review

After posting all line-specific comments, submit a formal review:

```bash
# If critical issues found → Request Changes
gh pr review {PR_NUMBER} --request-changes --body "$(cat <<'EOF'
### Code Review - Detailed Analysis

**PR Summary:** [Brief description]

#### Issues Reviewed (X total, Y met 80+ confidence threshold)

| Issue | File:Line | Confidence | Severity | Verdict |
|-------|-----------|------------|----------|---------|
| [Issue description] | `path:123` | [Score] | Critical/Important/Suggestion | [Why flagged/filtered] |
...

#### Review Methodology
[Description of multi-agent process]

🤖 Generated with Claude Code
EOF
)"

# If only suggestions or no issues → Comment (no blocking)
gh pr review {PR_NUMBER} --comment --body "..."
```

### Review Submission Logic

| Condition | Review Type | Effect |
|-----------|-------------|--------|
| Critical issues (80+ confidence) | `--request-changes` | Blocks merge until resolved |
| Important issues only | `--request-changes` | Blocks merge until resolved |
| Suggestions only | `--comment` | Non-blocking feedback |
| No issues found | `--comment` | Confirms review completed |

### Why Conversations Matter

- **Conversations require resolution** - Developer must address each before merge (if branch protection enabled)
- **Line-specific context** - Comments appear directly on the relevant code
- **Audit trail** - Each conversation shows resolution status
- **Blocks premature merge** - `--request-changes` prevents merge until re-reviewed

## Workflow

1. Complete code review process (eligibility check, agents, scoring)
2. **ALWAYS** post detailed analysis comment to PR (see format above) - this applies regardless of whether issues were found or filtered

**CRITICAL: The detailed comment format is REQUIRED even when no issues meet the 80+ threshold.** The table should show ALL issues that were reviewed and why each was filtered. This provides transparency into the review process.

## Why This Matters

- Provides transparency into review decisions
- Creates audit trail for filtered issues
- Allows learning from false positive patterns
