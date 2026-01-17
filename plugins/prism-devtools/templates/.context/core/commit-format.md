# Commit Message Format

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
