# Git Branching and Push Policy

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
