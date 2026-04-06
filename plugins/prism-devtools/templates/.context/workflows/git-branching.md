# Git Branching and Push Policy

**These rules prevent accidental pushes to protected branches.**

## Rule 1: NEVER Commit Directly to Default Branches

**Default branches include:** `main`, `master`, `staging`, `develop`

Before ANY commit:
1. Check current branch: `git branch --show-current`
2. If on a default branch, create a new branch FIRST
3. NEVER commit while on main/master/staging/develop

## Rule 2: NEVER Push Automatically

**Always ask the user before pushing to remote.**

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

## Pre-Commit Checklist

Before every commit:
- [ ] Run `git branch --show-current` to verify current branch
- [ ] If on default branch → create new branch first

**If on a default branch, DO NOT PROCEED until you've created a feature branch.**
